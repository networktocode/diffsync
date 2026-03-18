"""Unit tests for the DiffSyncModel bulk CRUD methods and store bulk operations.

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

from diffsync import Adapter, DiffSyncModel


class _Device(DiffSyncModel):
    _modelname = "device"
    _identifiers = ("name",)
    _attributes = ("role", "tag")

    name: str
    role: str = ""
    tag: str = ""


class _Site(DiffSyncModel):
    _modelname = "site"
    _identifiers = ("name",)
    _children = {"device": "devices"}

    name: str
    devices: List = []


class _SimpleAdapter(Adapter):
    site = _Site
    device = _Device
    top_level = ["site"]


def test_create_bulk_produces_same_results_as_individual_creates():
    """The default create_bulk implementation should create all requested objects."""
    adapter = _SimpleAdapter()
    results = _Device.create_bulk(
        adapter=adapter,
        objects=[
            {"ids": {"name": "d1"}, "attrs": {"role": "spine", "tag": "a"}},
            {"ids": {"name": "d2"}, "attrs": {"role": "leaf", "tag": "b"}},
        ],
    )
    assert len(results) == 2
    assert results[0].name == "d1"
    assert results[1].name == "d2"


def test_update_bulk_updates_all_models():
    """The default update_bulk implementation should update each model's attributes."""
    adapter = _SimpleAdapter()
    d1 = _Device(name="d1", role="spine", tag="a")
    d2 = _Device(name="d2", role="leaf", tag="b")
    results = _Device.update_bulk(
        adapter=adapter,
        objects=[(d1, {"role": "updated1"}), (d2, {"role": "updated2"})],
    )
    assert results[0].role == "updated1"
    assert results[1].role == "updated2"


def test_delete_bulk_deletes_all_models():
    """The default delete_bulk implementation should delete each model."""
    adapter = _SimpleAdapter()
    d1 = _Device(name="d1", role="spine", tag="a")
    d2 = _Device(name="d2", role="leaf", tag="b")
    results = _Device.delete_bulk(adapter=adapter, objects=[d1, d2])
    assert len(results) == 2


def test_store_add_bulk_adds_multiple_objects():
    """LocalStore.add_bulk should add all provided objects to the store."""
    adapter = _SimpleAdapter()
    d1 = _Device(name="d1", role="spine", tag="a")
    d2 = _Device(name="d2", role="leaf", tag="b")
    adapter.store.add_bulk(objs=[d1, d2])
    assert adapter.count("device") == 2


def test_store_remove_bulk_removes_multiple_objects():
    """LocalStore.remove_bulk should remove all provided objects from the store."""
    adapter = _SimpleAdapter()
    d1 = _Device(name="d1", role="spine", tag="a")
    d2 = _Device(name="d2", role="leaf", tag="b")
    adapter.store.add_bulk(objs=[d1, d2])
    adapter.store.remove_bulk(objs=[d1, d2])
    assert adapter.count("device") == 0
