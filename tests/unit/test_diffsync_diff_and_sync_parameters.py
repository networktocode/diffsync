"""Unit tests for Adapter diff/sync parameters: model_types, filters, sync_attrs, exclude_attrs, sync_filter, and concurrent.

Copyright (c) 2020-2021 Network To Code, LLC <info@networktocode.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import Dict, List, Optional

from diffsync import Adapter, DiffSyncModel
from diffsync.enum import DiffSyncFlags

# ---------------------------------------------------------------------------
# Models and adapters used across this test module
# ---------------------------------------------------------------------------


class _Site(DiffSyncModel):
    _modelname = "site"
    _identifiers = ("name",)
    _attributes = ("location",)
    _children = {"device": "devices"}

    name: str
    location: str = ""
    devices: List = []


class _Device(DiffSyncModel):
    _modelname = "device"
    _identifiers = ("name",)
    _attributes = ("role", "tag")

    name: str
    role: str = ""
    tag: str = ""


class _SimpleAdapter(Adapter):
    site = _Site
    device = _Device
    top_level = ["site"]


def _make_adapter_pair():
    """Build a source and destination adapter with overlapping but differing data."""
    src = _SimpleAdapter()
    dst = _SimpleAdapter()

    # Source: site1 (NYC) -> device1 (spine/prod), device2 (leaf/staging)
    #         site2 (SFO) -> device3 (spine/prod)
    site1 = _Site(name="site1", location="NYC")
    src.add(site1)
    d1 = _Device(name="device1", role="spine", tag="prod")
    src.add(d1)
    site1.add_child(d1)
    d2 = _Device(name="device2", role="leaf", tag="staging")
    src.add(d2)
    site1.add_child(d2)

    site2 = _Site(name="site2", location="SFO")
    src.add(site2)
    d3 = _Device(name="device3", role="spine", tag="prod")
    src.add(d3)
    site2.add_child(d3)

    # Dest: site1 (NYC) -> device1 (leaf/dev), device2 (leaf/staging)
    #       site3 (ATL) — not in source
    dst_site1 = _Site(name="site1", location="NYC")
    dst.add(dst_site1)
    dst_d1 = _Device(name="device1", role="leaf", tag="dev")
    dst.add(dst_d1)
    dst_site1.add_child(dst_d1)
    dst_d2 = _Device(name="device2", role="leaf", tag="staging")
    dst.add(dst_d2)
    dst_site1.add_child(dst_d2)

    dst_site3 = _Site(name="site3", location="ATL")
    dst.add(dst_site3)

    return src, dst


# ---------------------------------------------------------------------------
# model_types scoping
# ---------------------------------------------------------------------------


def test_diff_with_model_types_restricts_to_site_only():
    """Passing model_types={'site'} should exclude child device elements from the diff."""
    src, dst = _make_adapter_pair()
    diff = dst.diff_from(src, model_types={"site"})
    types = set()
    for child in diff.get_children():
        types.add(child.type)
    assert "site" in types
    assert "device" not in types


def test_diff_with_model_types_includes_site_and_device():
    """Passing model_types={'site', 'device'} should include both types in the diff."""
    src, dst = _make_adapter_pair()
    diff = dst.diff_from(src, model_types={"site", "device"})
    types = set()
    for child in diff.get_children():
        types.add(child.type)
        for grandchild in child.get_children():
            types.add(grandchild.type)
    assert "site" in types
    assert "device" in types


def test_sync_with_model_types_does_not_touch_excluded_types():
    """Syncing with model_types={'site'} should leave device objects unchanged."""
    src, dst = _make_adapter_pair()
    initial_device_count = dst.count("device")
    dst.sync_from(src, model_types={"site"})
    assert dst.count("device") == initial_device_count


# ---------------------------------------------------------------------------
# sync_attrs / exclude_attrs
# ---------------------------------------------------------------------------


def test_sync_attrs_limits_diff_to_whitelisted_attributes():
    """Only the attributes named in sync_attrs should appear in the diff."""
    src, dst = _make_adapter_pair()
    diff = dst.diff_from(src, sync_attrs={"device": {"role"}})
    for child in diff.get_children():
        for device_el in child.get_children():
            if device_el.type == "device" and device_el.action == "update":
                diffs = device_el.get_attrs_diffs()
                if "+" in diffs:
                    assert "role" in diffs["+"]
                    assert "tag" not in diffs["+"]


def test_exclude_attrs_removes_blacklisted_attributes():
    """Attributes named in exclude_attrs should not appear in the diff."""
    src, dst = _make_adapter_pair()
    diff = dst.diff_from(src, exclude_attrs={"device": {"tag"}})
    for child in diff.get_children():
        for device_el in child.get_children():
            if device_el.type == "device" and device_el.action == "update":
                diffs = device_el.get_attrs_diffs()
                if "+" in diffs:
                    assert "tag" not in diffs["+"]


def test_sync_attrs_and_exclude_attrs_applied_together():
    """sync_attrs whitelist is applied first, then exclude_attrs blacklist."""
    src, dst = _make_adapter_pair()
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
                    assert "tag" in diffs["+"]


# ---------------------------------------------------------------------------
# filters (query predicates)
# ---------------------------------------------------------------------------


def test_filters_include_matching_objects():
    """Objects whose predicate returns True should be included in the diff."""
    src, dst = _make_adapter_pair()
    diff = dst.diff_from(src, filters={"device": lambda d: d.role == "spine"})

    device_names = set()
    for child in diff.get_children():
        for device_el in child.get_children():
            if device_el.type == "device":
                device_names.add(device_el.name)

    assert "device1" in device_names  # spine in source
    assert "device3" in device_names  # spine in source
    assert "device2" not in device_names  # leaf in source, filtered out


def test_filters_exclude_nonmatching_objects():
    """Objects whose predicate returns False should be excluded from the diff."""
    src, dst = _make_adapter_pair()
    diff = dst.diff_from(src, filters={"device": lambda d: d.role == "nonexistent"})

    device_elements = []
    for child in diff.get_children():
        for device_el in child.get_children():
            if device_el.type == "device":
                device_elements.append(device_el)

    assert len(device_elements) == 0


def test_filters_do_not_affect_unfiltered_types():
    """Model types not named in the filters dict should remain in the diff."""
    src, dst = _make_adapter_pair()
    diff = dst.diff_from(src, filters={"device": lambda d: d.role == "spine"})

    site_elements = [child for child in diff.get_children() if child.type == "site"]
    assert len(site_elements) > 0


# ---------------------------------------------------------------------------
# sync_filter callback
# ---------------------------------------------------------------------------


def test_sync_filter_blocks_delete_operations():
    """A sync_filter that rejects deletes should preserve objects that only exist in the destination."""
    src, dst = _make_adapter_pair()
    assert dst.get_or_none("site", "site3") is not None

    dst.sync_from(
        src,
        sync_filter=lambda action, model_type, ids, attrs: action != "delete",
    )

    assert dst.get_or_none("site", "site3") is not None


def test_sync_filter_blocks_create_operations():
    """A sync_filter that rejects creates should prevent objects that only exist in the source."""
    src, dst = _make_adapter_pair()
    assert dst.get_or_none("site", "site2") is None

    dst.sync_from(
        src,
        sync_filter=lambda action, model_type, ids, attrs: action != "create",
    )

    assert dst.get_or_none("site", "site2") is None


def test_sync_filter_allows_update_operations():
    """A sync_filter that only allows updates should apply attribute changes without creating or deleting."""
    src, dst = _make_adapter_pair()

    dst.sync_from(
        src,
        sync_filter=lambda action, model_type, ids, attrs: action == "update",
        flags=DiffSyncFlags.SKIP_UNMATCHED_BOTH,
    )

    device1 = dst.get_or_none("device", "device1")
    assert device1 is not None
    assert device1.role == "spine"


def test_sync_filter_blocks_by_model_type():
    """A sync_filter can selectively block operations on specific model types."""
    src, dst = _make_adapter_pair()

    dst.sync_from(
        src,
        sync_filter=lambda action, model_type, ids, attrs: model_type != "device",
    )

    # site2 should be created (not blocked)
    assert dst.get_or_none("site", "site2") is not None


# ---------------------------------------------------------------------------
# sync_complete operations summary
# ---------------------------------------------------------------------------


class _TrackingAdapter(_SimpleAdapter):
    """Adapter that captures the operations dict passed to sync_complete."""

    captured_operations: Optional[Dict] = None

    def sync_complete(self, source, diff, flags=DiffSyncFlags.NONE, logger=None, operations=None):
        self.captured_operations = operations


def _make_tracking_dst():
    """Build a _TrackingAdapter pre-populated with the same data as the destination in _make_adapter_pair."""
    tracking_dst = _TrackingAdapter()
    dst_site1 = _Site(name="site1", location="NYC")
    tracking_dst.add(dst_site1)
    dst_d1 = _Device(name="device1", role="leaf", tag="dev")
    tracking_dst.add(dst_d1)
    dst_site1.add_child(dst_d1)
    dst_d2 = _Device(name="device2", role="leaf", tag="staging")
    tracking_dst.add(dst_d2)
    dst_site1.add_child(dst_d2)
    return tracking_dst


def test_sync_complete_receives_create_operations():
    """The operations dict passed to sync_complete should include create entries."""
    src, _ = _make_adapter_pair()
    tracking_dst = _make_tracking_dst()
    dst_site3 = _Site(name="site3", location="ATL")
    tracking_dst.add(dst_site3)

    tracking_dst.sync_from(src)

    assert tracking_dst.captured_operations is not None
    ops = tracking_dst.captured_operations
    assert "site" in ops
    created_site_names = [op["ids"]["name"] for op in ops["site"]["create"]]
    assert "site2" in created_site_names


def test_sync_complete_receives_update_operations():
    """The operations dict passed to sync_complete should include update entries."""
    src, _ = _make_adapter_pair()
    tracking_dst = _make_tracking_dst()

    tracking_dst.sync_from(src, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)

    ops = tracking_dst.captured_operations
    assert ops is not None
    assert "device" in ops
    updated_device_names = [op["ids"]["name"] for op in ops["device"]["update"]]
    assert "device1" in updated_device_names


def test_sync_complete_backwards_compat_without_operations_kwarg():
    """Subclasses that override sync_complete without the operations kwarg should still work."""

    class _OldStyleAdapter(_SimpleAdapter):
        sync_complete_called = False

        def sync_complete(self, source, diff, flags=DiffSyncFlags.NONE, logger=None):
            self.sync_complete_called = True

    src, _ = _make_adapter_pair()
    old_dst = _OldStyleAdapter()
    old_dst.add(_Site(name="site1", location="NYC"))

    old_dst.sync_from(src, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)
    assert old_dst.sync_complete_called


# ---------------------------------------------------------------------------
# concurrent sync
# ---------------------------------------------------------------------------


def test_concurrent_sync_matches_serial_sync():
    """Syncing with concurrent=True should produce the same result as a serial sync."""
    src, dst_serial = _make_adapter_pair()
    _, dst_concurrent = _make_adapter_pair()

    dst_serial.sync_from(src)
    dst_concurrent.sync_from(src, concurrent=True, max_workers=2)

    assert dst_serial.count("site") == dst_concurrent.count("site")
    assert dst_serial.count("device") == dst_concurrent.count("device")


def test_sync_defaults_to_serial():
    """Passing concurrent=False (the default) should work identically to the original sync."""
    src, dst = _make_adapter_pair()
    dst.sync_from(src, concurrent=False)
    assert dst.get_or_none("site", "site2") is not None


# ---------------------------------------------------------------------------
# Combinations of multiple parameters
# ---------------------------------------------------------------------------


def test_diff_filter_then_sync_with_sync_filter():
    """A pre-filtered Diff combined with a sync_filter should respect both layers."""
    src, dst = _make_adapter_pair()

    diff = dst.diff_from(src)
    filtered = diff.filter(actions={"create", "update"})

    dst.sync_from(
        src,
        diff=filtered,
        sync_filter=lambda action, model_type, ids, attrs: not (action == "create" and model_type == "site"),
    )

    # site2 blocked by sync_filter, device1 update allowed
    assert dst.get_or_none("site", "site2") is None
    device1 = dst.get_or_none("device", "device1")
    assert device1 is not None
    assert device1.role == "spine"


def test_model_types_combined_with_sync_attrs():
    """model_types and sync_attrs should compose — only scoped types with whitelisted attrs appear."""
    src, dst = _make_adapter_pair()

    diff = dst.diff_from(
        src,
        model_types={"site", "device"},
        sync_attrs={"device": {"role"}},
    )

    for child in diff.get_children():
        for device_el in child.get_children():
            if device_el.type == "device" and device_el.action == "update":
                diffs = device_el.get_attrs_diffs()
                if "+" in diffs:
                    assert "tag" not in diffs["+"]


def test_filters_combined_with_sync_attrs():
    """A query predicate filter and sync_attrs should compose — only matching objects with whitelisted attrs."""
    src, dst = _make_adapter_pair()

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

    for de in device_elements:
        assert de.name != "device2"  # device2 is leaf, should be filtered out
        if de.action == "update":
            diffs = de.get_attrs_diffs()
            if "+" in diffs:
                assert "tag" not in diffs["+"]


# ---------------------------------------------------------------------------
# sync_stages — ordered group execution for concurrent sync
# ---------------------------------------------------------------------------


# Models and adapters for sync_stages tests — uses multiple top-level types
# to exercise staged parallelism.

_creation_order: List = []


class _Region(DiffSyncModel):
    _modelname = "region"
    _identifiers = ("name",)
    _attributes = ("slug",)

    name: str
    slug: str = ""

    @classmethod
    def create(cls, adapter, ids, attrs):
        _creation_order.append(("region", ids["name"]))
        return super().create(adapter=adapter, ids=ids, attrs=attrs)


class _Tenant(DiffSyncModel):
    _modelname = "tenant"
    _identifiers = ("name",)
    _attributes = ("group",)

    name: str
    group: str = ""

    @classmethod
    def create(cls, adapter, ids, attrs):
        _creation_order.append(("tenant", ids["name"]))
        return super().create(adapter=adapter, ids=ids, attrs=attrs)


class _Rack(DiffSyncModel):
    _modelname = "rack"
    _identifiers = ("name",)
    _attributes = ("site_name",)

    name: str
    site_name: str = ""

    @classmethod
    def create(cls, adapter, ids, attrs):
        _creation_order.append(("rack", ids["name"]))
        return super().create(adapter=adapter, ids=ids, attrs=attrs)


class _StagedAdapter(Adapter):
    region = _Region
    tenant = _Tenant
    rack = _Rack
    top_level = ["region", "tenant", "rack"]
    sync_stages = [
        ["region", "tenant"],  # stage 1: independent, can run in parallel
        ["rack"],              # stage 2: depends on regions being created
    ]


class _UnstagedAdapter(Adapter):
    """Same models, no sync_stages — for comparison."""
    region = _Region
    tenant = _Tenant
    rack = _Rack
    top_level = ["region", "tenant", "rack"]


def _make_staged_pair(adapter_cls=_StagedAdapter):
    """Build a source with regions/tenants/racks and an empty destination."""
    src = adapter_cls()
    dst = adapter_cls()

    src.add(_Region(name="region1", slug="r1"))
    src.add(_Region(name="region2", slug="r2"))
    src.add(_Tenant(name="tenant1", group="g1"))
    src.add(_Rack(name="rack1", site_name="region1"))
    src.add(_Rack(name="rack2", site_name="region2"))

    return src, dst


def test_sync_stages_executes_in_order():
    """All stage-1 types (region, tenant) must be created before any stage-2 type (rack)."""
    _creation_order.clear()
    src, dst = _make_staged_pair()
    dst.sync_from(src, concurrent=True, max_workers=4)

    # Find the index of the first rack creation
    rack_indices = [i for i, (t, _) in enumerate(_creation_order) if t == "rack"]
    region_indices = [i for i, (t, _) in enumerate(_creation_order) if t == "region"]
    tenant_indices = [i for i, (t, _) in enumerate(_creation_order) if t == "tenant"]

    assert len(rack_indices) == 2
    assert len(region_indices) == 2
    assert len(tenant_indices) == 1

    # All stage-1 creations (regions + tenants) must come before any stage-2 creation (racks)
    max_stage1_index = max(max(region_indices), max(tenant_indices))
    min_stage2_index = min(rack_indices)
    assert max_stage1_index < min_stage2_index, (
        f"Stage 1 items must all complete before stage 2 begins. "
        f"Order was: {_creation_order}"
    )


def test_sync_stages_parallelizes_within_stage():
    """Two independent top-level types in the same stage should both be processed."""
    _creation_order.clear()
    src, dst = _make_staged_pair()
    dst.sync_from(src, concurrent=True, max_workers=4)

    types_created = {t for t, _ in _creation_order}
    assert "region" in types_created
    assert "tenant" in types_created
    assert "rack" in types_created


def test_sync_stages_none_preserves_current_behavior():
    """sync_stages=None with concurrent=True should behave like the original unstaged concurrent sync."""
    _creation_order.clear()
    src, dst = _make_staged_pair(_UnstagedAdapter)
    dst.sync_from(src, concurrent=True, max_workers=2)

    assert dst.get_or_none("region", "region1") is not None
    assert dst.get_or_none("tenant", "tenant1") is not None
    assert dst.get_or_none("rack", "rack1") is not None


def test_sync_stages_ignored_when_serial():
    """sync_stages should have no effect on serial sync — top_level order is used."""
    _creation_order.clear()
    src, dst = _make_staged_pair()
    dst.sync_from(src, concurrent=False)

    assert dst.get_or_none("region", "region1") is not None
    assert dst.get_or_none("rack", "rack1") is not None


def test_sync_stages_validation_rejects_unknown_type():
    """A type in sync_stages that is not in top_level should raise AttributeError."""
    import pytest

    with pytest.raises(AttributeError, match="sync_stages.*not in top_level"):
        class _BadAdapter(Adapter):
            region = _Region
            top_level = ["region"]
            sync_stages = [["region", "nonexistent"]]


def test_sync_stages_validation_rejects_duplicates():
    """A type appearing in multiple stages should raise AttributeError."""
    import pytest

    with pytest.raises(AttributeError, match="sync_stages.*duplicate"):
        class _BadAdapter(Adapter):
            region = _Region
            tenant = _Tenant
            top_level = ["region", "tenant"]
            sync_stages = [["region", "tenant"], ["region"]]


def test_sync_stages_unstaged_types_still_sync():
    """A type in top_level but not in any stage should still be synced (serially, after all stages)."""

    class _PartialStagesAdapter(Adapter):
        region = _Region
        tenant = _Tenant
        rack = _Rack
        top_level = ["region", "tenant", "rack"]
        sync_stages = [["region"]]  # tenant and rack not staged

    _creation_order.clear()
    src, dst = _make_staged_pair(_PartialStagesAdapter)
    dst.sync_from(src, concurrent=True, max_workers=2)

    # All types should still be synced
    assert dst.get_or_none("region", "region1") is not None
    assert dst.get_or_none("tenant", "tenant1") is not None
    assert dst.get_or_none("rack", "rack1") is not None
