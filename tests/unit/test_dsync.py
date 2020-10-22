"""Unit tests for the DSync class.

Copyright (c) 2020 Network To Code, LLC <info@networktocode.com>

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

import pytest

from dsync import DSync, DSyncModel, DSyncFlags, DSyncModelFlags
from dsync.exceptions import ObjectAlreadyExists, ObjectNotFound, ObjectCrudException

from .conftest import Site, Device, Interface, TrackedDiff, BackendA


def test_dsync_default_name_type(generic_dsync):
    assert generic_dsync.type == "DSync"
    assert generic_dsync.name == "DSync"


def test_dsync_generic_load_is_noop(generic_dsync):
    generic_dsync.load()
    assert len(generic_dsync._data) == 0  # pylint: disable=protected-access


def test_dsync_dict_with_no_data(generic_dsync):
    assert generic_dsync.dict() == {}


def test_dsync_str_with_no_data(generic_dsync):
    assert generic_dsync.str() == ""


def test_dsync_diff_self_with_no_data_has_no_diffs(generic_dsync):
    assert generic_dsync.diff_from(generic_dsync).has_diffs() is False
    assert generic_dsync.diff_to(generic_dsync).has_diffs() is False


def test_dsync_sync_self_with_no_data_is_noop(generic_dsync):
    generic_dsync.sync_from(generic_dsync)
    generic_dsync.sync_to(generic_dsync)


def test_dsync_get_with_no_data_is_none(generic_dsync):
    assert generic_dsync.get("anything", "myname") is None
    assert generic_dsync.get(DSyncModel, "") is None


def test_dsync_get_all_with_no_data_is_empty_list(generic_dsync):
    assert list(generic_dsync.get_all("anything")) == []
    assert list(generic_dsync.get_all(DSyncModel)) == []


def test_dsync_get_by_uids_with_no_data_is_empty_list(generic_dsync):
    assert generic_dsync.get_by_uids(["any", "another"], "anything") == []
    assert generic_dsync.get_by_uids(["any", "another"], DSyncModel) == []


def test_dsync_add(generic_dsync, generic_dsync_model):
    # A DSync can store arbitrary DSyncModel objects, even if it doesn't know about them at definition time.
    generic_dsync.add(generic_dsync_model)
    with pytest.raises(ObjectAlreadyExists):
        generic_dsync.add(generic_dsync_model)


def test_dsync_get_with_generic_model(generic_dsync, generic_dsync_model):
    generic_dsync.add(generic_dsync_model)
    # The generic_dsync_model has an empty identifier/unique-id
    assert generic_dsync.get(DSyncModel, "") == generic_dsync_model
    assert generic_dsync.get(DSyncModel.get_type(), "") == generic_dsync_model
    # DSync doesn't know how to construct a uid str for a "dsyncmodel"
    assert generic_dsync.get(DSyncModel.get_type(), {}) is None
    # Wrong object-type - no match
    assert generic_dsync.get("", "") is None
    # Wrong unique-id - no match
    assert generic_dsync.get(DSyncModel, "myname") is None


def test_dsync_get_all_with_generic_model(generic_dsync, generic_dsync_model):
    generic_dsync.add(generic_dsync_model)
    assert list(generic_dsync.get_all(DSyncModel)) == [generic_dsync_model]
    assert list(generic_dsync.get_all(DSyncModel.get_type())) == [generic_dsync_model]
    # Wrong object-type - no match
    assert list(generic_dsync.get_all("anything")) == []


def test_dsync_get_by_uids_with_generic_model(generic_dsync, generic_dsync_model):
    generic_dsync.add(generic_dsync_model)
    assert generic_dsync.get_by_uids([""], DSyncModel) == [generic_dsync_model]
    assert generic_dsync.get_by_uids([""], DSyncModel.get_type()) == [generic_dsync_model]
    # Wrong unique-id - no match
    assert generic_dsync.get_by_uids(["myname"], DSyncModel) == []
    # Valid unique-id mixed in with unknown ones - return the successful matches?
    assert generic_dsync.get_by_uids(["aname", "", "anothername"], DSyncModel) == [generic_dsync_model]


def test_dsync_remove_with_generic_model(generic_dsync, generic_dsync_model):
    generic_dsync.add(generic_dsync_model)
    generic_dsync.remove(generic_dsync_model)
    with pytest.raises(ObjectNotFound):
        generic_dsync.remove(generic_dsync_model)

    assert generic_dsync.get(DSyncModel, "") is None
    assert list(generic_dsync.get_all(DSyncModel)) == []
    assert generic_dsync.get_by_uids([""], DSyncModel) == []


def test_dsync_subclass_validation():
    """Test the declaration-time checks on a DSync subclass."""
    # pylint: disable=unused-variable
    with pytest.raises(AttributeError) as excinfo:

        class BadElementName(DSync):
            """Model with a DSyncModel attribute whose name does not match the modelname."""

            dev_class = Device  # should be device = Device

    assert "Device" in str(excinfo.value)
    assert "device" in str(excinfo.value)
    assert "dev_class" in str(excinfo.value)


def test_dsync_dict_with_data(backend_a):
    assert backend_a.dict() == {
        "device": {
            "nyc-spine1": {
                "interfaces": ["nyc-spine1__eth0", "nyc-spine1__eth1"],
                "name": "nyc-spine1",
                "role": "spine",
                "site_name": "nyc",
            },
            "nyc-spine2": {
                "interfaces": ["nyc-spine2__eth0", "nyc-spine2__eth1"],
                "name": "nyc-spine2",
                "role": "spine",
                "site_name": "nyc",
            },
            "rdu-spine1": {
                "interfaces": ["rdu-spine1__eth0", "rdu-spine1__eth1"],
                "name": "rdu-spine1",
                "role": "spine",
                "site_name": "rdu",
            },
            "rdu-spine2": {
                "interfaces": ["rdu-spine2__eth0", "rdu-spine2__eth1"],
                "name": "rdu-spine2",
                "role": "spine",
                "site_name": "rdu",
            },
            "sfo-spine1": {
                "interfaces": ["sfo-spine1__eth0", "sfo-spine1__eth1"],
                "name": "sfo-spine1",
                "role": "spine",
                "site_name": "sfo",
            },
            "sfo-spine2": {
                "interfaces": ["sfo-spine2__eth0", "sfo-spine2__eth1", "sfo-spine2__eth2"],
                "name": "sfo-spine2",
                "role": "spine",
                "site_name": "sfo",
            },
        },
        "interface": {
            "nyc-spine1__eth0": {"description": "Interface 0", "device_name": "nyc-spine1", "name": "eth0"},
            "nyc-spine1__eth1": {"description": "Interface 1", "device_name": "nyc-spine1", "name": "eth1"},
            "nyc-spine2__eth0": {"description": "Interface 0", "device_name": "nyc-spine2", "name": "eth0"},
            "nyc-spine2__eth1": {"description": "Interface 1", "device_name": "nyc-spine2", "name": "eth1"},
            "rdu-spine1__eth0": {"description": "Interface 0", "device_name": "rdu-spine1", "name": "eth0"},
            "rdu-spine1__eth1": {"description": "Interface 1", "device_name": "rdu-spine1", "name": "eth1"},
            "rdu-spine2__eth0": {"description": "Interface 0", "device_name": "rdu-spine2", "name": "eth0"},
            "rdu-spine2__eth1": {"description": "Interface 1", "device_name": "rdu-spine2", "name": "eth1"},
            "sfo-spine1__eth0": {"description": "Interface 0", "device_name": "sfo-spine1", "name": "eth0"},
            "sfo-spine1__eth1": {"description": "Interface 1", "device_name": "sfo-spine1", "name": "eth1"},
            "sfo-spine2__eth0": {"description": "TBD", "device_name": "sfo-spine2", "name": "eth0"},
            "sfo-spine2__eth1": {"description": "ddd", "device_name": "sfo-spine2", "name": "eth1"},
            "sfo-spine2__eth2": {"description": "Interface 2", "device_name": "sfo-spine2", "name": "eth2"},
        },
        "person": {"Glenn Matthews": {"name": "Glenn Matthews"}},
        "site": {
            "nyc": {"devices": ["nyc-spine1", "nyc-spine2"], "name": "nyc"},
            "rdu": {"devices": ["rdu-spine1", "rdu-spine2"], "name": "rdu", "people": ["Glenn Matthews"]},
            "sfo": {"devices": ["sfo-spine1", "sfo-spine2"], "name": "sfo"},
        },
    }


def test_dsync_str_with_data(backend_a):
    assert (
        backend_a.str()
        == """\
site
  site: nyc: {}
    devices
      device: nyc-spine1: {'role': 'spine', 'tag': ''}
        interfaces
          interface: nyc-spine1__eth0: {'interface_type': 'ethernet', 'description': 'Interface 0'}
          interface: nyc-spine1__eth1: {'interface_type': 'ethernet', 'description': 'Interface 1'}
      device: nyc-spine2: {'role': 'spine', 'tag': ''}
        interfaces
          interface: nyc-spine2__eth0: {'interface_type': 'ethernet', 'description': 'Interface 0'}
          interface: nyc-spine2__eth1: {'interface_type': 'ethernet', 'description': 'Interface 1'}
    people: []
  site: sfo: {}
    devices
      device: sfo-spine1: {'role': 'spine', 'tag': ''}
        interfaces
          interface: sfo-spine1__eth0: {'interface_type': 'ethernet', 'description': 'Interface 0'}
          interface: sfo-spine1__eth1: {'interface_type': 'ethernet', 'description': 'Interface 1'}
      device: sfo-spine2: {'role': 'spine', 'tag': ''}
        interfaces
          interface: sfo-spine2__eth0: {'interface_type': 'ethernet', 'description': 'TBD'}
          interface: sfo-spine2__eth1: {'interface_type': 'ethernet', 'description': 'ddd'}
          interface: sfo-spine2__eth2: {'interface_type': 'ethernet', 'description': 'Interface 2'}
    people: []
  site: rdu: {}
    devices
      device: rdu-spine1: {'role': 'spine', 'tag': ''}
        interfaces
          interface: rdu-spine1__eth0: {'interface_type': 'ethernet', 'description': 'Interface 0'}
          interface: rdu-spine1__eth1: {'interface_type': 'ethernet', 'description': 'Interface 1'}
      device: rdu-spine2: {'role': 'spine', 'tag': ''}
        interfaces
          interface: rdu-spine2__eth0: {'interface_type': 'ethernet', 'description': 'Interface 0'}
          interface: rdu-spine2__eth1: {'interface_type': 'ethernet', 'description': 'Interface 1'}
    people
      person: Glenn Matthews: {}"""
    )


def test_dsync_diff_self_with_data_has_no_diffs(backend_a):
    # Self diff should always show no diffs!
    assert backend_a.diff_from(backend_a).has_diffs() is False
    assert backend_a.diff_to(backend_a).has_diffs() is False


def test_dsync_diff_other_with_data_has_diffs(backend_a, backend_b):
    assert backend_a.diff_to(backend_b).has_diffs() is True
    assert backend_a.diff_from(backend_b).has_diffs() is True


def test_dsync_diff_to_and_diff_from_are_symmetric(backend_a, backend_b):
    diff_ab = backend_a.diff_from(backend_b)
    diff_ba = backend_a.diff_to(backend_b)

    def check_diff_symmetry(diff1, diff2):
        """Recursively compare two Diffs to make sure they are equal and opposite to one another."""
        assert len(list(diff1.get_children())) == len(list(diff2.get_children()))
        for elem1, elem2 in zip(sorted(diff1.get_children()), sorted(diff2.get_children())):
            # Same basic properties
            assert elem1.type == elem2.type
            assert elem1.name == elem2.name
            assert elem1.keys == elem2.keys
            assert elem1.has_diffs() == elem2.has_diffs()
            # Opposite diffs, if any
            assert elem1.source_attrs == elem2.dest_attrs
            assert elem1.dest_attrs == elem2.source_attrs
            check_diff_symmetry(elem1.child_diff, elem2.child_diff)

    check_diff_symmetry(diff_ab, diff_ba)


def test_dsync_diff_from_with_custom_diff_class(backend_a, backend_b):
    diff_ba = backend_a.diff_from(backend_b, diff_class=TrackedDiff)
    assert isinstance(diff_ba, TrackedDiff)
    assert diff_ba.is_complete is True


def test_dsync_sync_from(backend_a, backend_b):
    # Perform full sync
    backend_a.sync_from(backend_b)
    # Make sure the sync descended through the diff elements to their children
    assert backend_a.get(Device, "sfo-spine1").role == "leaf"  # was initially "spine"

    # site_nyc and site_sfo should be updated, site_atl should be created, site_rdu should be deleted
    site_nyc_a = backend_a.get(Site, "nyc")
    assert isinstance(site_nyc_a, Site)
    assert site_nyc_a.name == "nyc"
    site_sfo_a = backend_a.get("site", "sfo")
    assert isinstance(site_sfo_a, Site)
    assert site_sfo_a.name == "sfo"
    site_atl_a = backend_a.get("site", "atl")
    assert isinstance(site_atl_a, Site)
    assert site_atl_a.name == "atl"
    assert backend_a.get(Site, "rdu") is None
    assert backend_a.get("nothing", "") is None

    assert list(backend_a.get_all(Site)) == [site_nyc_a, site_sfo_a, site_atl_a]
    assert list(backend_a.get_all("site")) == [site_nyc_a, site_sfo_a, site_atl_a]
    assert list(backend_a.get_all("nothing")) == []

    assert backend_a.get_by_uids(["nyc", "sfo"], Site) == [site_nyc_a, site_sfo_a]
    assert backend_a.get_by_uids(["sfo", "nyc"], "site") == [site_sfo_a, site_nyc_a]
    assert backend_a.get_by_uids(["nyc", "sfo"], Device) == []
    assert backend_a.get_by_uids(["nyc", "sfo"], "device") == []


def test_dsync_subclass_default_name_type(backend_a):
    assert backend_a.name == "BackendA"
    assert backend_a.type == "BackendA"


def test_dsync_subclass_custom_name_type(backend_b):
    assert backend_b.name == "backend-b"
    assert backend_b.type == "Backend_B"


def test_dsync_add_get_remove_with_subclass_and_data(backend_a):
    site_nyc_a = backend_a.get(Site, "nyc")
    site_sfo_a = backend_a.get("site", "sfo")
    site_rdu_a = backend_a.get(Site, "rdu")
    site_atl_a = Site(name="atl")
    backend_a.add(site_atl_a)
    with pytest.raises(ObjectAlreadyExists):
        backend_a.add(site_atl_a)

    assert backend_a.get(Site, "atl") == site_atl_a
    assert list(backend_a.get_all("site")) == [site_nyc_a, site_sfo_a, site_rdu_a, site_atl_a]
    assert backend_a.get_by_uids(["rdu", "sfo", "atl", "nyc"], "site") == [
        site_rdu_a,
        site_sfo_a,
        site_atl_a,
        site_nyc_a,
    ]

    backend_a.remove(site_atl_a)
    with pytest.raises(ObjectNotFound):
        backend_a.remove(site_atl_a)


def test_dsync_sync_from_exceptions_are_not_caught_by_default(error_prone_backend_a, backend_b):
    with pytest.raises(ObjectCrudException):
        error_prone_backend_a.sync_from(backend_b)


def test_dsync_sync_from_with_continue_on_failure_flag(log, error_prone_backend_a, backend_b):
    error_prone_backend_a.sync_from(backend_b, flags=DSyncFlags.CONTINUE_ON_FAILURE)
    # Not all sync operations succeeded on the first try
    remaining_diffs = error_prone_backend_a.diff_from(backend_b)
    remaining_diffs.print_detailed()
    assert remaining_diffs.has_diffs()

    # At least some operations of each type should have succeeded
    assert log.has("Created successfully", status="success")
    assert log.has("Updated successfully", status="success")
    assert log.has("Deleted successfully", status="success")
    # Some ERROR messages should have been logged
    assert [event for event in log.events if event["level"] == "error"] != []
    # Some messages with status="error" should have been logged - these may be the same as the above
    assert [event for event in log.events if event.get("status") == "error"] != []
    log.events = []

    # Retry up to 10 times, we should sync successfully eventually
    for i in range(10):
        print(f"Sync retry #{i}")
        error_prone_backend_a.sync_from(backend_b, flags=DSyncFlags.CONTINUE_ON_FAILURE)
        remaining_diffs = error_prone_backend_a.diff_from(backend_b)
        remaining_diffs.print_detailed()
        if remaining_diffs.has_diffs():
            # If we still have diffs, some ERROR messages should have been logged
            assert [event for event in log.events if event["level"] == "error"] != []
            # Some messages with status="errored" should have been logged - these may be the same as the above
            assert [event for event in log.events if event.get("status") == "error"] != []
            log.events = []
        else:
            # No error messages should have been logged on the last, fully successful attempt
            assert [event for event in log.events if event["level"] == "error"] == []
            # Something must have succeeded for us to be done
            assert [event for event in log.events if event.get("status") == "success"] != []
            break
    else:
        pytest.fail("Sync was still incomplete after 10 retries")


def test_dsync_diff_with_skip_unmatched_src_flag(backend_a, backend_a_with_extra_models, backend_a_minus_some_models):
    assert backend_a.diff_from(backend_a_with_extra_models).has_diffs()
    # SKIP_UNMATCHED_SRC should mean that extra models in the src are not flagged for creation in the dest
    assert not backend_a.diff_from(backend_a_with_extra_models, flags=DSyncFlags.SKIP_UNMATCHED_SRC).has_diffs()
    # SKIP_UNMATCHED_SRC should NOT mean that extra models in the dst are not flagged for deletion in the src
    assert backend_a.diff_from(backend_a_minus_some_models, flags=DSyncFlags.SKIP_UNMATCHED_SRC).has_diffs()


def test_dsync_diff_with_skip_unmatched_dst_flag(backend_a, backend_a_with_extra_models, backend_a_minus_some_models):
    assert backend_a.diff_from(backend_a_minus_some_models).has_diffs()
    # SKIP_UNMATCHED_DST should mean that missing models in the src are not flagged for deletion from the dest
    assert not backend_a.diff_from(backend_a_minus_some_models, flags=DSyncFlags.SKIP_UNMATCHED_DST).has_diffs()
    # SKIP_UNMATCHED_DST should NOT mean that extra models in the src are not flagged for creation in the dest
    assert backend_a.diff_from(backend_a_with_extra_models, flags=DSyncFlags.SKIP_UNMATCHED_DST).has_diffs()


def test_dsync_diff_with_skip_unmatched_both_flag(backend_a, backend_a_with_extra_models, backend_a_minus_some_models):
    # SKIP_UNMATCHED_BOTH should mean that extra models in the src are not flagged for creation in the dest
    assert not backend_a.diff_from(backend_a_with_extra_models, flags=DSyncFlags.SKIP_UNMATCHED_BOTH).has_diffs()
    # SKIP_UNMATCHED_BOTH should mean that missing models in the src are not flagged for deletion from the dest
    assert not backend_a.diff_from(backend_a_minus_some_models, flags=DSyncFlags.SKIP_UNMATCHED_BOTH).has_diffs()


def test_dsync_sync_with_skip_unmatched_src_flag(backend_a, backend_a_with_extra_models):
    backend_a.sync_from(backend_a_with_extra_models, flags=DSyncFlags.SKIP_UNMATCHED_SRC)
    # New objects should not have been created
    assert backend_a.get(backend_a.site, "lax") is None
    assert backend_a.get(backend_a.device, "nyc-spine3") is None
    assert "nyc-spine3" not in backend_a.get(backend_a.site, "nyc").devices


def test_dsync_sync_with_skip_unmatched_dst_flag(backend_a, backend_a_minus_some_models):
    backend_a.sync_from(backend_a_minus_some_models, flags=DSyncFlags.SKIP_UNMATCHED_DST)
    # Objects should not have been deleted
    assert backend_a.get(backend_a.site, "rdu") is not None
    assert backend_a.get(backend_a.device, "sfo-spine2") is not None
    assert "sfo-spine2" in backend_a.get(backend_a.site, "sfo").devices


def test_dsync_diff_with_ignore_flag_on_source_models(backend_a, backend_a_with_extra_models):
    # Directly ignore the extra source site
    backend_a_with_extra_models.get(backend_a_with_extra_models.site, "lax").model_flags |= DSyncModelFlags.IGNORE
    # Ignore any diffs on source site NYC, which should extend to its child nyc-spine3 device
    backend_a_with_extra_models.get(backend_a_with_extra_models.site, "nyc").model_flags |= DSyncModelFlags.IGNORE

    diff = backend_a.diff_from(backend_a_with_extra_models)
    diff.print_detailed()
    assert not diff.has_diffs()


def test_dsync_diff_with_ignore_flag_on_target_models(backend_a, backend_a_minus_some_models):
    # Directly ignore the extra target site
    backend_a.get(backend_a.site, "rdu").model_flags |= DSyncModelFlags.IGNORE
    # Ignore any diffs on target site SFO, which should extend to its child sfo-spine2 device
    backend_a.get(backend_a.site, "sfo").model_flags |= DSyncModelFlags.IGNORE

    diff = backend_a.diff_from(backend_a_minus_some_models)
    diff.print_detailed()
    assert not diff.has_diffs()


def test_dsync_sync_skip_children_on_delete(backend_a):
    class NoDeleteInterface(Interface):
        """Interface that shouldn't be deleted directly."""

        def delete(self):
            raise RuntimeError("Don't delete me, bro!")

    class NoDeleteInterfaceDSync(BackendA):
        """BackendA, but using NoDeleteInterface."""

        interface = NoDeleteInterface

    extra_models = NoDeleteInterfaceDSync()
    extra_models.load()
    extra_device = extra_models.device(name="nyc-spine3", site_name="nyc", role="spine")
    extra_device.model_flags |= DSyncModelFlags.SKIP_CHILDREN_ON_DELETE
    extra_models.get(extra_models.site, "nyc").add_child(extra_device)
    extra_models.add(extra_device)
    extra_interface = extra_models.interface(name="eth0", device_name="nyc-spine3")
    extra_device.add_child(extra_interface)
    extra_models.add(extra_interface)
    assert extra_models.get(extra_models.interface, "nyc-spine3__eth0") is not None

    # NoDeleteInterface.delete() should not be called since we're deleting its parent only
    extra_models.sync_from(backend_a)
    # The extra interface should have been removed from the DSync without calling its delete() method
    assert extra_models.get(extra_models.interface, extra_interface.get_unique_id()) is None
    # The sync should be complete, regardless
    diff = extra_models.diff_from(backend_a)
    diff.print_detailed()
    assert not diff.has_diffs()
