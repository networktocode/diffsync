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

import pytest

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

    assert "device1" in device_names   # spine in source
    assert "device3" in device_names   # spine in source
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
