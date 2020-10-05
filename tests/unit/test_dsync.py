"""Unit tests for the DSync class."""

import pytest

from dsync import DSync, DSyncModel
from dsync.exceptions import ObjectAlreadyExists, ObjectNotFound, ObjectNotCreated, ObjectNotUpdated, ObjectNotDeleted

from .conftest import Site, Device, Interface


def test_generic_dsync_methods(generic_dsync, generic_dsync_model):
    """Test the standard DSync APIs on a generic DSync instance and DSyncModel instance."""
    generic_dsync.load()  # no-op
    assert len(generic_dsync._data) == 0  # pylint: disable=protected-access

    diff = generic_dsync.diff_from(generic_dsync)
    assert diff.has_diffs() is False
    diff = generic_dsync.diff_to(generic_dsync)
    assert diff.has_diffs() is False

    generic_dsync.sync_from(generic_dsync)  # no-op
    generic_dsync.sync_to(generic_dsync)  # no-op

    assert generic_dsync.get("anything", ["myname"]) is None
    assert generic_dsync.get(DSyncModel, []) is None

    assert list(generic_dsync.get_all("anything")) == []
    assert list(generic_dsync.get_all(DSyncModel)) == []

    assert generic_dsync.get_by_uids(["any", "another"], "anything") == []
    assert generic_dsync.get_by_uids(["any", "another"], DSyncModel) == []

    # A DSync can store arbitrary DSyncModel objects, even if it doesn't know about them at definition time.
    generic_dsync.add(generic_dsync_model)
    with pytest.raises(ObjectAlreadyExists):
        generic_dsync.add(generic_dsync_model)

    # The generic_dsync_model has an empty identifier/unique-id
    assert generic_dsync.get(DSyncModel, []) == generic_dsync_model
    assert generic_dsync.get(DSyncModel.get_type(), []) == generic_dsync_model
    # Wrong object-type - no match
    assert generic_dsync.get("", []) is None
    # Wrong unique-id - no match
    assert generic_dsync.get(DSyncModel, ["myname"]) is None

    assert list(generic_dsync.get_all(DSyncModel)) == [generic_dsync_model]
    assert list(generic_dsync.get_all(DSyncModel.get_type())) == [generic_dsync_model]
    # Wrong object-type - no match
    assert list(generic_dsync.get_all("anything")) == []

    assert generic_dsync.get_by_uids([""], DSyncModel) == [generic_dsync_model]
    assert generic_dsync.get_by_uids([""], DSyncModel.get_type()) == [generic_dsync_model]
    # Wrong unique-id - no match
    assert generic_dsync.get_by_uids(["myname"], DSyncModel) == []
    # Valid unique-id mixed in with unknown ones - return the successful matches?
    assert generic_dsync.get_by_uids(["aname", "", "anothername"], DSyncModel) == [generic_dsync_model]

    generic_dsync.remove(generic_dsync_model)
    with pytest.raises(ObjectNotFound):
        generic_dsync.remove(generic_dsync_model)

    assert generic_dsync.get(DSyncModel, []) is None
    assert list(generic_dsync.get_all(DSyncModel)) == []
    assert generic_dsync.get_by_uids([""], DSyncModel) == []

    # Default (empty) DSync class doesn't know how to create any objects
    with pytest.raises(ObjectNotCreated):
        generic_dsync.create_object("dsyncmodel", {}, {})
    with pytest.raises(ObjectNotUpdated):
        generic_dsync.update_object("dsyncmodel", {}, {})
    with pytest.raises(ObjectNotDeleted):
        generic_dsync.delete_object("dsyncmodel", {}, {})

    diff_elements = generic_dsync._diff_objects(  # pylint: disable=protected-access
        [generic_dsync_model], [generic_dsync_model], generic_dsync,
    )
    assert len(diff_elements) == 1
    assert not diff_elements[0].has_diffs()
    # No-op as diff_element.has_diffs() is False
    generic_dsync._sync_from_diff_element(diff_elements[0])  # pylint: disable=protected-access


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


def test_dsync_subclass_methods_diff_sync(backend_a, backend_b):
    """Test DSync diff/sync APIs on an actual concrete subclass."""
    diff_elements = backend_a._diff_objects(  # pylint: disable=protected-access
        source=backend_a.get_all("site"), dest=backend_b.get_all("site"), source_root=backend_b
    )
    assert len(diff_elements) == 2  # nyc, sfo
    assert diff_elements[0].has_diffs()
    assert diff_elements[1].has_diffs()
    # We don't inspect the contents of the diff elements in detail here - see test_diff_element.py for that

    diff_aa = backend_a.diff_from(backend_a)
    assert diff_aa.has_diffs() is False
    diff_aa = backend_a.diff_to(backend_a)
    assert diff_aa.has_diffs() is False
    diff_ab = backend_a.diff_to(backend_b)
    assert diff_ab.has_diffs() is True
    diff_ba = backend_a.diff_from(backend_b)
    assert diff_ba.has_diffs() is True

    def check_diff_symmetry(diff1, diff2):
        """Recursively compare two Diffs to make sure they are equal and opposite to one another."""
        assert len(list(diff1.get_children())) == len(list(diff2.get_children()))
        for elem1, elem2 in zip(diff1.get_children(), diff2.get_children()):
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

    # Perform sync of one subtree of diffs
    assert backend_a._sync_from_diff_element(diff_elements[0]) is True  # pylint: disable=protected-access
    # Make sure the sync descended through the diff element all the way to the leafs
    assert backend_a.get(Interface, ["nyc-spine1", "eth0"]).description == "Interface 0/0"  # was initially Interface 0
    # Recheck diffs
    diff_elements = backend_a._diff_objects(  # pylint: disable=protected-access
        source=backend_a.get_all("site"), dest=backend_b.get_all("site"), source_root=backend_b
    )
    assert len(diff_elements) == 2  # nyc, sfo
    assert not diff_elements[0].has_diffs()  # sync completed, no diffs
    assert diff_elements[1].has_diffs()

    # Perform full sync
    backend_a.sync_from(backend_b)
    # Make sure the sync descended through the diff elements to their children
    assert backend_a.get(Device, ["sfo-spine1"]).role == "leaf"  # was initially "spine"
    # Recheck diffs
    assert backend_a.diff_from(backend_b).has_diffs() is False

    site_nyc_a = backend_a.get(Site, ["nyc"])
    assert isinstance(site_nyc_a, Site)
    assert site_nyc_a.name == "nyc"
    site_sfo_a = backend_a.get("site", ["sfo"])
    assert isinstance(site_sfo_a, Site)
    assert site_sfo_a.name == "sfo"
    assert backend_a.get("site", ["atl"]) is None
    assert backend_a.get("nothing", [""]) is None

    assert list(backend_a.get_all(Site)) == [site_nyc_a, site_sfo_a]
    assert list(backend_a.get_all("site")) == [site_nyc_a, site_sfo_a]
    assert list(backend_a.get_all("nothing")) == []

    # TODO: get_by_uids() currently orders its response based on the insertion order into the store,
    #       not by the order of the provided keys. Probably a bug?
    assert backend_a.get_by_uids(["nyc", "sfo"], Site) == [site_nyc_a, site_sfo_a]
    assert backend_a.get_by_uids(["sfo", "nyc"], "site") == [site_nyc_a, site_sfo_a]  # TODO: [site_sfo_a, site_nyc_a]
    assert backend_a.get_by_uids(["nyc", "sfo"], Device) == []
    assert backend_a.get_by_uids(["nyc", "sfo"], "device") == []


def test_dsync_subclass_methods_crud(backend_a):
    """Test DSync CRUD APIs against a concrete subclass."""
    site_nyc_a = backend_a.get(Site, ["nyc"])
    site_sfo_a = backend_a.get("site", ["sfo"])
    site_atl_a = Site(name="atl")
    backend_a.add(site_atl_a)
    with pytest.raises(ObjectAlreadyExists):
        backend_a.add(site_atl_a)

    assert backend_a.get(Site, ["atl"]) == site_atl_a
    assert list(backend_a.get_all("site")) == [site_nyc_a, site_sfo_a, site_atl_a]
    # TODO: again, order of keys is not respected by get_by_uids()
    assert backend_a.get_by_uids(["sfo", "atl", "nyc"], "site") == [site_nyc_a, site_sfo_a, site_atl_a]

    backend_a.remove(site_atl_a)
    with pytest.raises(ObjectNotFound):
        backend_a.remove(site_atl_a)

    # Test low-level default_* CRUD APIs
    backend_a.default_create("interface", {"device_name": "nyc-spine1", "name": "eth2"}, {"description": "Interface 2"})
    new_interface = backend_a.get("interface", ["nyc-spine1", "eth2"])
    assert new_interface.description == "Interface 2"

    backend_a.default_update("interface", {"device_name": "nyc-spine1", "name": "eth2"}, {"description": "Intf 2"})
    new_interface_2 = backend_a.get("interface", ["nyc-spine1", "eth2"])
    assert new_interface.description == "Intf 2"
    assert new_interface_2 is new_interface

    backend_a.default_delete("interface", {"device_name": "nyc-spine1", "name": "eth2"}, {})
    assert backend_a.get("interface", ["nyc-spine1", "eth2"]) is None

    # Test higher-level *_object CRUD APIs
    backend_a.create_object("device", {"name": "new_device"}, {"role": "new_role", "site_name": "nyc"})
    new_device = backend_a.get("device", ["new_device"])
    assert new_device.role == "new_role"
    assert new_device.site_name == "nyc"

    backend_a.update_object("device", {"name": "new_device"}, {"role": "another_role"})
    new_device_2 = backend_a.get(Device, ["new_device"])
    assert new_device_2 is new_device
    assert new_device.role == "another_role"

    backend_a.delete_object("device", {"name": "new_device"})
    new_device_3 = backend_a.get("device", ["new_device"])
    assert new_device_3 is None
