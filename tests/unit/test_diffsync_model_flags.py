"""Unit tests for the DiffSyncModel flags.

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

from typing import List

import pytest

from diffsync import Adapter, DiffSyncModel
from diffsync.enum import DiffSyncModelFlags
from diffsync.exceptions import ObjectNotFound


def test_diffsync_diff_with_skip_unmatched_src_flag_on_models(backend_a, backend_a_with_extra_models):
    # Validate that there are 2 extras objects out of the box
    diff = backend_a.diff_from(backend_a_with_extra_models)
    assert diff.summary() == {"create": 2, "update": 0, "delete": 0, "no-change": 23, "skip": 0}

    # Check that only 1 object is affected by the flag
    backend_a_with_extra_models.get(
        backend_a_with_extra_models.site, "lax"
    ).model_flags |= DiffSyncModelFlags.SKIP_UNMATCHED_SRC
    diff = backend_a.diff_from(backend_a_with_extra_models)
    assert diff.summary() == {"create": 1, "update": 0, "delete": 0, "no-change": 23, "skip": 1}

    backend_a_with_extra_models.get(
        backend_a_with_extra_models.device, "nyc-spine3"
    ).model_flags |= DiffSyncModelFlags.SKIP_UNMATCHED_SRC
    diff = backend_a.diff_from(backend_a_with_extra_models)
    assert diff.summary() == {"create": 0, "update": 0, "delete": 0, "no-change": 23, "skip": 2}


def test_diffsync_sync_with_skip_unmatched_src_flag_on_models(backend_a, backend_a_with_extra_models):
    backend_a_with_extra_models.get(
        backend_a_with_extra_models.site, "lax"
    ).model_flags |= DiffSyncModelFlags.SKIP_UNMATCHED_SRC
    backend_a_with_extra_models.get(
        backend_a_with_extra_models.device, "nyc-spine3"
    ).model_flags |= DiffSyncModelFlags.SKIP_UNMATCHED_SRC

    backend_a.sync_from(backend_a_with_extra_models)

    # New objects should not have been created
    with pytest.raises(ObjectNotFound):
        backend_a.get(backend_a.site, "lax")
    with pytest.raises(ObjectNotFound):
        backend_a.get(backend_a.device, "nyc-spine3")
    assert "nyc-spine3" not in backend_a.get(backend_a.site, "nyc").devices

    diff = backend_a.diff_from(backend_a_with_extra_models)
    assert diff.summary() == {"create": 0, "update": 0, "delete": 0, "no-change": 23, "skip": 2}


def test_diffsync_diff_with_skip_unmatched_dst_flag_on_models(backend_a, backend_a_minus_some_models):
    # Validate that there are 3 extras objects out of the box
    diff = backend_a.diff_from(backend_a_minus_some_models)
    assert diff.summary() == {"create": 0, "update": 0, "delete": 12, "no-change": 11, "skip": 0}

    # Check that only the device "rdu-spine1" and its 2 interfaces are affected by the flag
    backend_a.get(backend_a.device, "rdu-spine1").model_flags |= DiffSyncModelFlags.SKIP_UNMATCHED_DST
    diff = backend_a.diff_from(backend_a_minus_some_models)
    assert diff.summary() == {"create": 0, "update": 0, "delete": 9, "no-change": 11, "skip": 1}

    # Check that only one additional device "sfo-spine2" and its 3 interfaces are affected by the flag
    backend_a.get(backend_a.device, "sfo-spine2").model_flags |= DiffSyncModelFlags.SKIP_UNMATCHED_DST
    diff = backend_a.diff_from(backend_a_minus_some_models)
    assert diff.summary() == {"create": 0, "update": 0, "delete": 5, "no-change": 11, "skip": 2}


def test_diffsync_sync_with_skip_unmatched_dst_flag_on_models(backend_a, backend_a_minus_some_models):
    backend_a.get(backend_a.site, "rdu").model_flags |= DiffSyncModelFlags.SKIP_UNMATCHED_DST
    backend_a.get(backend_a.device, "sfo-spine2").model_flags |= DiffSyncModelFlags.SKIP_UNMATCHED_DST
    backend_a.sync_from(backend_a_minus_some_models)

    # Objects should not have been deleted
    # rdu-spine1 hasn't been deleted because its parent hasn't been deleted
    assert backend_a.get(backend_a.site, "rdu") is not None
    assert backend_a.get(backend_a.device, "rdu-spine1") is not None
    assert backend_a.get(backend_a.device, "sfo-spine2") is not None
    assert backend_a.get(backend_a.interface, "sfo-spine2__eth0") is not None
    assert "sfo-spine2" in backend_a.get(backend_a.site, "sfo").devices


def test_diffsync_diff_with_ignore_flag_on_source_models(backend_a, backend_a_with_extra_models):
    # Directly ignore the extra source site
    backend_a_with_extra_models.get(backend_a_with_extra_models.site, "lax").model_flags |= DiffSyncModelFlags.IGNORE
    # Ignore any diffs on source site NYC, which should extend to its child nyc-spine3 device
    backend_a_with_extra_models.get(backend_a_with_extra_models.site, "nyc").model_flags |= DiffSyncModelFlags.IGNORE

    diff = backend_a.diff_from(backend_a_with_extra_models)
    print(diff.str())  # for debugging of any failure
    assert not diff.has_diffs()


def test_diffsync_diff_with_ignore_flag_on_target_models(backend_a, backend_a_minus_some_models):
    # Directly ignore the extra target site
    backend_a.get(backend_a.site, "rdu").model_flags |= DiffSyncModelFlags.IGNORE
    # Ignore any diffs on target site SFO, which should extend to its child sfo-spine2 device
    backend_a.get(backend_a.site, "sfo").model_flags |= DiffSyncModelFlags.IGNORE

    diff = backend_a.diff_from(backend_a_minus_some_models)
    print(diff.str())  # for debugging of any failure
    assert not diff.has_diffs()


def test_diffsync_diff_with_natural_deletion_order():
    # This list will contain the order in which the delete methods were called
    call_order = []

    class TestModelChild(DiffSyncModel):  # pylint: disable=missing-class-docstring
        _modelname = "child"
        _identifiers = ("name",)

        name: str

        def delete(self):
            call_order.append(self.name)
            return super().delete()

    class TestModelParent(DiffSyncModel):  # pylint: disable=missing-class-docstring
        _modelname = "parent"
        _identifiers = ("name",)
        _children = {"child": "children"}

        name: str
        children: List[TestModelChild] = []

        def delete(self):
            call_order.append(self.name)
            return super().delete()

    class TestBackend(Adapter):  # pylint: disable=missing-class-docstring
        top_level = ["parent"]

        parent = TestModelParent
        child = TestModelChild

        def load(self):
            parent = self.parent(name="Test-Parent")
            parent.model_flags |= DiffSyncModelFlags.NATURAL_DELETION_ORDER
            self.add(parent)
            child = self.child(name="Test-Child")
            parent.add_child(child)
            self.add(child)

    source = TestBackend()
    source.load()
    destination = TestBackend()
    destination.load()
    source.remove(source.get("parent", {"name": "Test-Parent"}), remove_children=True)
    source.sync_to(destination)
    assert call_order == ["Test-Child", "Test-Parent"]


def test_natural_deletion_order_with_noop_parent():
    """Test whether children are recursed through when natural deletion order is set and the parent has no changes."""
    call_order = []

    class ChildModel(DiffSyncModel):
        """Test child model that reports when its update method is called."""

        _modelname = "child"
        _identifiers = ("name",)
        _attributes = ("attribute",)

        name: str
        attribute: str

        def update(self, attrs):
            call_order.append("Update on child")
            return super().update(attrs)

    class ParentModel(DiffSyncModel):
        """Test parent model."""

        _modelname = "parent"
        _identifiers = ("name",)
        _attributes = ("attribute",)
        _children = {"child": "children"}

        name: str
        attribute: str
        children: List[ChildModel] = []

    class TestAdapter(Adapter):
        """Test adapter."""

        top_level = ["parent"]

        parent = ParentModel
        child = ChildModel

        def load(self, is_source=False) -> None:
            """Test load method. Generate a difference with the is_source parameter."""
            parent = self.parent(name="Test Parent", attribute="This doesn't change")
            parent.model_flags |= DiffSyncModelFlags.NATURAL_DELETION_ORDER
            self.add(parent)
            if is_source:
                child = self.child(name="Test Child", attribute="Attribute from source")
                child.model_flags |= DiffSyncModelFlags.NATURAL_DELETION_ORDER
                parent.add_child(child)
                self.add(child)
            else:
                child = self.child(name="Test Child", attribute="Attribute from destination")
                child.model_flags |= DiffSyncModelFlags.NATURAL_DELETION_ORDER
                parent.add_child(child)
                self.add(child)

    source_adapter = TestAdapter()
    source_adapter.load(is_source=True)
    destination_adapter = TestAdapter()
    destination_adapter.load()

    source_adapter.sync_to(destination_adapter)

    assert "Update on child" in call_order
