"""Unit tests for the DSync class."""

import logging

import pytest

from dsync import DSync, DSyncModel, DSyncFlags
from dsync.exceptions import ObjectAlreadyExists, ObjectNotFound, ObjectCrudException

from .conftest import Site, Device, Interface, TrackedDiff, BackendA


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

    assert generic_dsync.get("anything", "myname") is None
    assert generic_dsync.get(DSyncModel, "") is None

    assert list(generic_dsync.get_all("anything")) == []
    assert list(generic_dsync.get_all(DSyncModel)) == []

    assert generic_dsync.get_by_uids(["any", "another"], "anything") == []
    assert generic_dsync.get_by_uids(["any", "another"], DSyncModel) == []

    # A DSync can store arbitrary DSyncModel objects, even if it doesn't know about them at definition time.
    generic_dsync.add(generic_dsync_model)
    with pytest.raises(ObjectAlreadyExists):
        generic_dsync.add(generic_dsync_model)

    # The generic_dsync_model has an empty identifier/unique-id
    assert generic_dsync.get(DSyncModel, "") == generic_dsync_model
    # DSync doesn't know what a "dsyncmodel" is
    assert generic_dsync.get(DSyncModel.get_type(), "") is None
    # Wrong object-type - no match
    assert generic_dsync.get("", "") is None
    # Wrong unique-id - no match
    assert generic_dsync.get(DSyncModel, "myname") is None

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

    assert generic_dsync.get(DSyncModel, "") is None
    assert list(generic_dsync.get_all(DSyncModel)) == []
    assert generic_dsync.get_by_uids([""], DSyncModel) == []

    diff_elements = generic_dsync._diff_objects(  # pylint: disable=protected-access
        [generic_dsync_model], [generic_dsync_model], generic_dsync,
    )
    assert len(diff_elements) == 1
    assert not diff_elements[0].has_diffs()
    assert diff_elements[0].source_name == "DSync"
    assert diff_elements[0].dest_name == "DSync"


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


def test_dsync_subclass_methods_diff_sync(backend_a, backend_b):
    """Test DSync diff/sync APIs on an actual concrete subclass."""
    diff_elements = backend_a._diff_objects(  # pylint: disable=protected-access
        source=backend_b.get_all("site"), dest=backend_a.get_all("site"), source_root=backend_b
    )
    assert len(diff_elements) == 4  # atl, nyc, sfo, rdu
    for diff_element in diff_elements:
        diff_element.print_detailed()
        assert diff_element.has_diffs()
    # We don't inspect the contents of the diff elements in detail here - see test_diff_element.py for that

    # Self diff should always show no diffs!
    assert backend_a.diff_from(backend_a).has_diffs() is False
    assert backend_a.diff_to(backend_a).has_diffs() is False

    diff_ab = backend_a.diff_to(backend_b)
    assert diff_ab.has_diffs() is True
    diff_ba = backend_a.diff_from(backend_b)
    assert diff_ba.has_diffs() is True

    check_diff_symmetry(diff_ab, diff_ba)

    # Perform sync of one subtree of diffs
    backend_a._sync_from_diff_element(diff_elements[0])  # pylint: disable=protected-access
    # Make sure the sync descended through the diff element all the way to the leafs
    assert backend_a.get(Interface, "nyc-spine1__eth0").description == "Interface 0/0"  # was initially Interface 0
    # Recheck diffs
    diff_elements = backend_a._diff_objects(  # pylint: disable=protected-access
        source=backend_a.get_all("site"), dest=backend_b.get_all("site"), source_root=backend_b
    )
    for diff_element in diff_elements:
        diff_element.print_detailed()
    assert len(diff_elements) == 4  # atl, nyc, sfo, rdu
    assert not diff_elements[0].has_diffs()  # sync completed, no diffs
    assert diff_elements[1].has_diffs()
    assert diff_elements[2].has_diffs()
    assert diff_elements[3].has_diffs()

    # Perform full sync
    backend_a.sync_from(backend_b)
    # Make sure the sync descended through the diff elements to their children
    assert backend_a.get(Device, "sfo-spine1").role == "leaf"  # was initially "spine"
    # Recheck diffs, using a custom Diff subclass this time.
    diff_ba = backend_a.diff_from(backend_b, diff_class=TrackedDiff)
    assert isinstance(diff_ba, TrackedDiff)
    assert diff_ba.is_complete is True
    diff_ba.print_detailed()
    assert diff_ba.has_diffs() is False

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


def test_dsync_subclass_methods_name_type(backend_a, backend_b):
    """Test DSync name and type an actual concrete subclass.

    backend_a is using the default name and type
    backend_b is using a user defined name and type
    """
    assert backend_a.name == "BackendA"
    assert backend_a.type == "BackendA"

    assert backend_b.name == "backend-b"
    assert backend_b.type == "Backend_B"


def test_dsync_subclass_methods_crud(backend_a):
    """Test DSync CRUD APIs against a concrete subclass."""
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


def test_dsync_subclass_methods_sync_exceptions(caplog, error_prone_backend_a, backend_b):
    """Test handling of exceptions during a sync."""
    caplog.set_level(logging.INFO)
    with pytest.raises(ObjectCrudException):
        error_prone_backend_a.sync_from(backend_b)

    error_prone_backend_a.sync_from(backend_b, flags=DSyncFlags.CONTINUE_ON_FAILURE)
    # Not all sync operations succeeded on the first try
    remaining_diffs = error_prone_backend_a.diff_from(backend_b)
    remaining_diffs.print_detailed()
    assert remaining_diffs.has_diffs()

    # Some ERROR messages should have been logged
    assert [record.message for record in caplog.records if record.levelname == "ERROR"] != []
    caplog.clear()

    # Retry up to 10 times, we should sync successfully eventually
    for i in range(10):
        print(f"Sync retry #{i}")
        error_prone_backend_a.sync_from(backend_b, flags=DSyncFlags.CONTINUE_ON_FAILURE)
        remaining_diffs = error_prone_backend_a.diff_from(backend_b)
        remaining_diffs.print_detailed()
        if remaining_diffs.has_diffs():
            # If we still have diffs, some ERROR messages should have been logged
            assert [record.message for record in caplog.records if record.levelname == "ERROR"] != []
            caplog.clear()
        else:
            # No error messages should have been logged on the last, fully successful attempt
            assert [record.message for record in caplog.records if record.levelname == "ERROR"] == []
            break
    else:
        pytest.fail("Sync was still incomplete after 10 retries")


def test_dsync_subclass_methods_diff_sync_skip_flags():
    """Test diff and sync behavior when using the SKIP_UNMATCHED_* flags."""
    baseline = BackendA()
    baseline.load()

    extra_models = BackendA()
    extra_models.load()
    extra_site = extra_models.site(name="lax")
    extra_models.add(extra_site)
    extra_device = extra_models.device(name="nyc-spine3", site_name="nyc", role="spine")
    extra_models.get(extra_models.site, "nyc").add_child(extra_device)
    extra_models.add(extra_device)

    missing_models = BackendA()
    missing_models.load()
    missing_models.remove(missing_models.get(missing_models.site, "rdu"))
    missing_device = missing_models.get(missing_models.device, "sfo-spine2")
    missing_models.get(missing_models.site, "sfo").remove_child(missing_device)
    missing_models.remove(missing_device)

    assert baseline.diff_from(extra_models).has_diffs()
    assert baseline.diff_to(missing_models).has_diffs()

    # SKIP_UNMATCHED_SRC should mean that extra models in the src are not flagged for creation in the dest
    assert not baseline.diff_from(extra_models, flags=DSyncFlags.SKIP_UNMATCHED_SRC).has_diffs()
    # SKIP_UNMATCHED_DST should mean that missing models in the src are not flagged for deletion from the dest
    assert not baseline.diff_from(missing_models, flags=DSyncFlags.SKIP_UNMATCHED_DST).has_diffs()
    # SKIP_UNMATCHED_BOTH means, well, both
    assert not extra_models.diff_from(missing_models, flags=DSyncFlags.SKIP_UNMATCHED_BOTH).has_diffs()
    assert not extra_models.diff_to(missing_models, flags=DSyncFlags.SKIP_UNMATCHED_BOTH).has_diffs()

    baseline.sync_from(extra_models, flags=DSyncFlags.SKIP_UNMATCHED_SRC)
    # New objects should not have been created
    assert baseline.get(baseline.site, "lax") is None
    assert baseline.get(baseline.device, "nyc-spine3") is None
    assert "nyc-spine3" not in baseline.get(baseline.site, "nyc").devices

    baseline.sync_from(missing_models, flags=DSyncFlags.SKIP_UNMATCHED_DST)
    # Objects should not have been deleted
    assert baseline.get(baseline.site, "rdu") is not None
    assert baseline.get(baseline.device, "sfo-spine2") is not None
    assert "sfo-spine2" in baseline.get(baseline.site, "sfo").devices
