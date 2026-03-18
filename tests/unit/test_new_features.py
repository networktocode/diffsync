"""Tests for new features: bulk sync, filtering, concurrent execution.

Tests for Features 1-9 as described in the implementation plan.
"""

from typing import ClassVar, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

from diffsync import Adapter, DiffSyncModel
from diffsync.diff import Diff, DiffElement
from diffsync.enum import DiffSyncFlags


# ---------------------------------------------------------------------------
# Test models and adapters
# ---------------------------------------------------------------------------

class Region(DiffSyncModel):
    _modelname = "region"
    _identifiers = ("name",)
    _children = {"site": "sites"}

    name: str
    sites: List = []


class Site(DiffSyncModel):
    _modelname = "site"
    _identifiers = ("name",)
    _attributes = ("location",)
    _children = {"device": "devices"}

    name: str
    location: str = ""
    devices: List = []


class Device(DiffSyncModel):
    _modelname = "device"
    _identifiers = ("name",)
    _attributes = ("role", "tag")

    name: str
    role: str = ""
    tag: str = ""


class BulkDevice(DiffSyncModel):
    """Device model with custom bulk CRUD methods for testing."""

    _modelname = "device"
    _identifiers = ("name",)
    _attributes = ("role", "tag")

    name: str
    role: str = ""
    tag: str = ""

    _bulk_create_calls: ClassVar[List] = []
    _bulk_update_calls: ClassVar[List] = []
    _bulk_delete_calls: ClassVar[List] = []

    @classmethod
    def create_bulk(cls, adapter, objects):
        cls._bulk_create_calls.append(objects)
        return [cls.create(adapter=adapter, ids=o["ids"], attrs=o["attrs"]) for o in objects]

    @classmethod
    def update_bulk(cls, adapter, objects):
        cls._bulk_update_calls.append(objects)
        return [model.update(attrs=attrs) for model, attrs in objects]

    @classmethod
    def delete_bulk(cls, adapter, objects):
        cls._bulk_delete_calls.append(objects)
        return [model.delete() for model in objects]


class SimpleAdapter(Adapter):
    site = Site
    device = Device
    top_level = ["site"]


class RegionAdapter(Adapter):
    region = Region
    site = Site
    device = Device
    top_level = ["region"]


def make_adapter_pair():
    """Create a source and destination adapter with some data for testing."""
    src = SimpleAdapter()
    dst = SimpleAdapter()

    # Source: site1 with device1 (spine) and device2 (leaf)
    # Source: site2 with device3 (spine)
    site1 = Site(name="site1", location="NYC")
    src.add(site1)
    d1 = Device(name="device1", role="spine", tag="prod")
    src.add(d1)
    site1.add_child(d1)
    d2 = Device(name="device2", role="leaf", tag="staging")
    src.add(d2)
    site1.add_child(d2)

    site2 = Site(name="site2", location="SFO")
    src.add(site2)
    d3 = Device(name="device3", role="spine", tag="prod")
    src.add(d3)
    site2.add_child(d3)

    # Dest: site1 with device1 (different role) and device2 (same)
    # Dest: site3 (extra site not in src)
    dst_site1 = Site(name="site1", location="NYC")
    dst.add(dst_site1)
    dst_d1 = Device(name="device1", role="leaf", tag="dev")
    dst.add(dst_d1)
    dst_site1.add_child(dst_d1)
    dst_d2 = Device(name="device2", role="leaf", tag="staging")
    dst.add(dst_d2)
    dst_site1.add_child(dst_d2)

    dst_site3 = Site(name="site3", location="ATL")
    dst.add(dst_site3)

    return src, dst


# ===========================================================================
# Feature 8: Diff.filter() and Diff.exclude()
# ===========================================================================

class TestDiffFilter:

    def test_filter_by_action_create(self, diff_with_children):
        """Filter for only create actions."""
        filtered = diff_with_children.filter(actions={"create"})
        # person "Jimbo" has source_attrs only → create
        # The device with child update should appear as neutral container
        actions = []
        for child in filtered.get_children():
            if child.action:
                actions.append(child.action)
        assert "create" in actions
        assert "delete" not in actions

    def test_filter_by_action_delete(self, diff_with_children):
        """Filter for only delete actions."""
        filtered = diff_with_children.filter(actions={"delete"})
        actions = []
        for child in filtered.get_children():
            if child.action:
                actions.append(child.action)
        assert "delete" in actions
        assert "create" not in actions

    def test_filter_by_model_types(self, diff_with_children):
        """Filter for only person model type."""
        filtered = diff_with_children.filter(model_types={"person"})
        types = [child.type for child in filtered.get_children()]
        assert "person" in types
        assert "device" not in types
        assert "address" not in types

    def test_filter_combined(self, diff_with_children):
        """Filter by both action and model type."""
        filtered = diff_with_children.filter(actions={"create"}, model_types={"person"})
        elements = list(filtered.get_children())
        assert len(elements) == 1
        assert elements[0].type == "person"
        assert elements[0].action == "create"

    def test_filter_preserves_original(self, diff_with_children):
        """Verify that filtering does not mutate the original Diff."""
        original_len = len(diff_with_children)
        _ = diff_with_children.filter(actions={"create"})
        assert len(diff_with_children) == original_len

    def test_exclude_by_action(self, diff_with_children):
        """Exclude delete actions."""
        excluded = diff_with_children.exclude(actions={"delete"})
        for child in excluded.get_children():
            assert child.action != "delete"

    def test_exclude_by_model_types(self, diff_with_children):
        """Exclude person model types."""
        excluded = diff_with_children.exclude(model_types={"person"})
        types = [child.type for child in excluded.get_children()]
        assert "person" not in types

    def test_filter_no_criteria_returns_copy(self, diff_with_children):
        """Filtering with no criteria returns a full copy."""
        filtered = diff_with_children.filter()
        assert len(filtered) == len(diff_with_children)

    def test_exclude_no_criteria_returns_copy(self, diff_with_children):
        """Excluding with no criteria returns a full copy."""
        excluded = diff_with_children.exclude()
        assert len(excluded) == len(diff_with_children)

    def test_filter_models_processed_preserved(self, diff_with_children):
        """Verify models_processed is copied to filtered diff."""
        filtered = diff_with_children.filter(actions={"create"})
        assert filtered.models_processed == diff_with_children.models_processed


# ===========================================================================
# Feature 6: Model-type Scoping
# ===========================================================================

class TestModelTypeScoping:

    def test_diff_with_model_types_restricts_to_site(self):
        """Diff restricted to site model type should not include device changes."""
        src, dst = make_adapter_pair()
        diff = dst.diff_from(src, model_types={"site"})
        types = set()
        for child in diff.get_children():
            types.add(child.type)
        assert "site" in types
        assert "device" not in types

    def test_diff_with_model_types_site_and_device(self):
        """Diff restricted to both site and device should include both."""
        src, dst = make_adapter_pair()
        diff = dst.diff_from(src, model_types={"site", "device"})
        types = set()
        for child in diff.get_children():
            types.add(child.type)
            for grandchild in child.get_children():
                types.add(grandchild.type)
        assert "site" in types
        assert "device" in types

    def test_sync_with_model_types_only_syncs_specified(self):
        """Sync restricted to site model type should not create/delete devices."""
        src, dst = make_adapter_pair()
        initial_device_count = dst.count("device")
        dst.sync_from(src, model_types={"site"})
        # Device count should be unchanged since devices were excluded
        assert dst.count("device") == initial_device_count


# ===========================================================================
# Feature 7: Attribute-scoped Syncing
# ===========================================================================

class TestAttributeScopedSyncing:

    def test_sync_attrs_whitelist(self):
        """Only attributes in sync_attrs should appear in the diff."""
        src, dst = make_adapter_pair()
        diff = dst.diff_from(src, sync_attrs={"device": {"role"}})
        # device1 has role diff (spine vs leaf) and tag diff (prod vs dev)
        # With sync_attrs={"device": {"role"}}, only role should appear
        for child in diff.get_children():
            for device_el in child.get_children():
                if device_el.type == "device" and device_el.action == "update":
                    diffs = device_el.get_attrs_diffs()
                    if "+" in diffs:
                        assert "role" in diffs["+"]
                        assert "tag" not in diffs["+"]

    def test_exclude_attrs_blacklist(self):
        """Attributes in exclude_attrs should not appear in the diff."""
        src, dst = make_adapter_pair()
        diff = dst.diff_from(src, exclude_attrs={"device": {"tag"}})
        for child in diff.get_children():
            for device_el in child.get_children():
                if device_el.type == "device" and device_el.action == "update":
                    diffs = device_el.get_attrs_diffs()
                    if "+" in diffs:
                        assert "tag" not in diffs["+"]

    def test_sync_attrs_and_exclude_attrs_combined(self):
        """sync_attrs applied first, then exclude_attrs."""
        src, dst = make_adapter_pair()
        # Include both, then exclude role — net result: empty attrs for devices
        diff = dst.diff_from(
            src,
            sync_attrs={"device": {"role", "tag"}},
            exclude_attrs={"device": {"role"}},
        )
        for child in diff.get_children():
            for device_el in child.get_children():
                if device_el.type == "device" and device_el.name == "device1":
                    diffs = device_el.get_attrs_diffs()
                    if "+" in diffs:
                        assert "role" not in diffs["+"]
                        # tag should remain (prod vs dev)
                        assert "tag" in diffs["+"]


# ===========================================================================
# Feature 5: Attribute-based Query Predicates
# ===========================================================================

class TestQueryPredicates:

    def test_filter_predicate_includes_matching(self):
        """Objects matching the predicate should be included in the diff."""
        src, dst = make_adapter_pair()
        # Only include devices with role == "spine" in source
        diff = dst.diff_from(src, filters={"device": lambda d: d.role == "spine"})

        device_names = set()
        for child in diff.get_children():
            for device_el in child.get_children():
                if device_el.type == "device":
                    device_names.add(device_el.name)

        assert "device1" in device_names  # spine in source
        assert "device3" in device_names  # spine in source
        assert "device2" not in device_names  # leaf in source

    def test_filter_predicate_excludes_nonmatching(self):
        """Objects not matching the predicate should be excluded."""
        src, dst = make_adapter_pair()
        diff = dst.diff_from(src, filters={"device": lambda d: d.role == "nonexistent"})

        device_elements = []
        for child in diff.get_children():
            for device_el in child.get_children():
                if device_el.type == "device":
                    device_elements.append(device_el)

        assert len(device_elements) == 0

    def test_filter_predicate_unfiltered_types_unaffected(self):
        """Model types not in filters dict should be unaffected."""
        src, dst = make_adapter_pair()
        diff = dst.diff_from(src, filters={"device": lambda d: d.role == "spine"})

        site_elements = [child for child in diff.get_children() if child.type == "site"]
        assert len(site_elements) > 0  # Sites should still be present


# ===========================================================================
# Feature 9: Callback-based Sync Interceptor
# ===========================================================================

class TestSyncFilter:

    def test_sync_filter_blocks_deletes(self):
        """A sync_filter that returns False for deletes should prevent deletions."""
        src, dst = make_adapter_pair()
        # dst has site3 which doesn't exist in src — would normally be deleted
        assert dst.get_or_none("site", "site3") is not None

        dst.sync_from(
            src,
            sync_filter=lambda action, model_type, ids, attrs: action != "delete",
        )

        # site3 should still exist because deletes were blocked
        assert dst.get_or_none("site", "site3") is not None

    def test_sync_filter_blocks_creates(self):
        """A sync_filter that returns False for creates should prevent creations."""
        src, dst = make_adapter_pair()
        # src has site2 which doesn't exist in dst — would normally be created
        assert dst.get_or_none("site", "site2") is None

        dst.sync_from(
            src,
            sync_filter=lambda action, model_type, ids, attrs: action != "create",
        )

        # site2 should still not exist because creates were blocked
        assert dst.get_or_none("site", "site2") is None

    def test_sync_filter_allows_updates(self):
        """A sync_filter that allows updates should let them through."""
        src, dst = make_adapter_pair()

        dst.sync_from(
            src,
            sync_filter=lambda action, model_type, ids, attrs: action == "update",
            flags=DiffSyncFlags.SKIP_UNMATCHED_BOTH,
        )

        # device1 had role="leaf" in dst, role="spine" in src — should be updated
        device1 = dst.get_or_none("device", "device1")
        assert device1 is not None
        assert device1.role == "spine"

    def test_sync_filter_by_model_type(self):
        """A sync_filter that blocks specific model types."""
        src, dst = make_adapter_pair()

        dst.sync_from(
            src,
            sync_filter=lambda action, model_type, ids, attrs: model_type != "device",
        )

        # Sites should be synced, but device operations should be blocked
        assert dst.get_or_none("site", "site2") is not None  # created


# ===========================================================================
# Feature 4: Structured sync_complete Operations Summary
# ===========================================================================

class TrackingAdapter(SimpleAdapter):
    """Adapter that captures the operations dict from sync_complete."""

    captured_operations: Optional[Dict] = None

    def sync_complete(self, source, diff, flags=DiffSyncFlags.NONE, logger=None, operations=None):
        self.captured_operations = operations


class TestSyncCompleteOperations:

    def test_operations_summary_contains_creates(self):
        """sync_complete should receive operations dict with create entries."""
        src, dst = make_adapter_pair()
        tracking_dst = TrackingAdapter()
        # Populate tracking_dst same as dst
        dst_site1 = Site(name="site1", location="NYC")
        tracking_dst.add(dst_site1)
        dst_d1 = Device(name="device1", role="leaf", tag="dev")
        tracking_dst.add(dst_d1)
        dst_site1.add_child(dst_d1)
        dst_d2 = Device(name="device2", role="leaf", tag="staging")
        tracking_dst.add(dst_d2)
        dst_site1.add_child(dst_d2)
        dst_site3 = Site(name="site3", location="ATL")
        tracking_dst.add(dst_site3)

        tracking_dst.sync_from(src)

        assert tracking_dst.captured_operations is not None
        ops = tracking_dst.captured_operations

        # site2 should be in creates
        assert "site" in ops
        site_creates = ops["site"]["create"]
        created_site_names = [op["ids"]["name"] for op in site_creates]
        assert "site2" in created_site_names

    def test_operations_summary_contains_updates(self):
        """sync_complete should receive operations dict with update entries."""
        src, dst = make_adapter_pair()
        tracking_dst = TrackingAdapter()
        dst_site1 = Site(name="site1", location="NYC")
        tracking_dst.add(dst_site1)
        dst_d1 = Device(name="device1", role="leaf", tag="dev")
        tracking_dst.add(dst_d1)
        dst_site1.add_child(dst_d1)
        dst_d2 = Device(name="device2", role="leaf", tag="staging")
        tracking_dst.add(dst_d2)
        dst_site1.add_child(dst_d2)

        tracking_dst.sync_from(src, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)

        ops = tracking_dst.captured_operations
        assert ops is not None
        assert "device" in ops
        device_updates = ops["device"]["update"]
        updated_device_names = [op["ids"]["name"] for op in device_updates]
        assert "device1" in updated_device_names

    def test_backwards_compat_sync_complete_without_operations(self):
        """Existing subclasses without operations param should still work."""

        class OldStyleAdapter(SimpleAdapter):
            sync_complete_called = False

            def sync_complete(self, source, diff, flags=DiffSyncFlags.NONE, logger=None):
                self.sync_complete_called = True

        src, dst = make_adapter_pair()
        old_dst = OldStyleAdapter()
        old_dst.add(Site(name="site1", location="NYC"))

        # This should not raise TypeError
        old_dst.sync_from(src, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)
        assert old_dst.sync_complete_called


# ===========================================================================
# Feature 1: Bulk CRUD Methods
# ===========================================================================

class TestBulkCRUD:

    def test_create_bulk_default_loops(self):
        """Default create_bulk should produce same results as individual creates."""
        adapter = SimpleAdapter()
        results = Device.create_bulk(
            adapter=adapter,
            objects=[
                {"ids": {"name": "d1"}, "attrs": {"role": "spine", "tag": "a"}},
                {"ids": {"name": "d2"}, "attrs": {"role": "leaf", "tag": "b"}},
            ],
        )
        assert len(results) == 2
        assert results[0].name == "d1"
        assert results[1].name == "d2"

    def test_update_bulk_default_loops(self):
        """Default update_bulk should update each model."""
        adapter = SimpleAdapter()
        d1 = Device(name="d1", role="spine", tag="a")
        d2 = Device(name="d2", role="leaf", tag="b")
        results = Device.update_bulk(
            adapter=adapter,
            objects=[(d1, {"role": "updated1"}), (d2, {"role": "updated2"})],
        )
        assert results[0].role == "updated1"
        assert results[1].role == "updated2"

    def test_delete_bulk_default_loops(self):
        """Default delete_bulk should delete each model."""
        adapter = SimpleAdapter()
        d1 = Device(name="d1", role="spine", tag="a")
        d2 = Device(name="d2", role="leaf", tag="b")
        results = Device.delete_bulk(adapter=adapter, objects=[d1, d2])
        assert len(results) == 2

    def test_store_add_bulk(self):
        """Store add_bulk should add multiple objects."""
        adapter = SimpleAdapter()
        d1 = Device(name="d1", role="spine", tag="a")
        d2 = Device(name="d2", role="leaf", tag="b")
        adapter.store.add_bulk(objs=[d1, d2])
        assert adapter.count("device") == 2

    def test_store_remove_bulk(self):
        """Store remove_bulk should remove multiple objects."""
        adapter = SimpleAdapter()
        d1 = Device(name="d1", role="spine", tag="a")
        d2 = Device(name="d2", role="leaf", tag="b")
        adapter.store.add_bulk(objs=[d1, d2])
        adapter.store.remove_bulk(objs=[d1, d2])
        assert adapter.count("device") == 0


# ===========================================================================
# Feature 3: Concurrent Sync
# ===========================================================================

class TestConcurrentSync:

    def test_concurrent_sync_produces_correct_results(self):
        """Concurrent sync should produce same results as serial sync."""
        src, dst_serial = make_adapter_pair()
        _, dst_concurrent = make_adapter_pair()

        dst_serial.sync_from(src)
        dst_concurrent.sync_from(src, concurrent=True, max_workers=2)

        # Both should have the same final state
        assert dst_serial.count("site") == dst_concurrent.count("site")
        assert dst_serial.count("device") == dst_concurrent.count("device")

    def test_concurrent_false_is_default(self):
        """By default, sync should not use concurrent mode."""
        src, dst = make_adapter_pair()
        # Should work fine without concurrent
        dst.sync_from(src, concurrent=False)
        assert dst.get_or_none("site", "site2") is not None


# ===========================================================================
# Integration tests combining multiple features
# ===========================================================================

class TestIntegration:

    def test_filter_then_sync_with_sync_filter(self):
        """Combine diff-level filtering with sync_filter."""
        src, dst = make_adapter_pair()

        # Get the full diff, filter to only creates, then sync with sync_filter blocking site creates
        diff = dst.diff_from(src)
        filtered = diff.filter(actions={"create", "update"})

        dst.sync_from(
            src,
            diff=filtered,
            sync_filter=lambda action, model_type, ids, attrs: not (action == "create" and model_type == "site"),
        )

        # site2 should NOT be created (blocked by sync_filter)
        assert dst.get_or_none("site", "site2") is None
        # device1 update should have gone through
        device1 = dst.get_or_none("device", "device1")
        assert device1 is not None
        assert device1.role == "spine"

    def test_model_types_with_attribute_filter(self):
        """Combine model_types scoping with attribute filtering."""
        src, dst = make_adapter_pair()

        diff = dst.diff_from(
            src,
            model_types={"site", "device"},
            sync_attrs={"device": {"role"}},
        )

        # Devices should only show role diffs, not tag diffs
        for child in diff.get_children():
            for device_el in child.get_children():
                if device_el.type == "device" and device_el.action == "update":
                    diffs = device_el.get_attrs_diffs()
                    if "+" in diffs:
                        assert "tag" not in diffs["+"]

    def test_query_predicate_with_sync_attrs(self):
        """Combine query predicate filter with attribute scoping."""
        src, dst = make_adapter_pair()

        diff = dst.diff_from(
            src,
            filters={"device": lambda d: d.role == "spine"},
            sync_attrs={"device": {"role"}},
        )

        device_elements = []
        for child in diff.get_children():
            for device_el in child.get_children():
                if device_el.type == "device":
                    device_elements.append(device_el)

        # Only spine devices should appear, and only role attr
        for de in device_elements:
            assert de.name != "device2"  # device2 is leaf
            if de.action == "update":
                diffs = de.get_attrs_diffs()
                if "+" in diffs:
                    assert "tag" not in diffs["+"]
