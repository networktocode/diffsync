"""Unit tests for the DSync class."""

import pytest

from dsync import DSyncModel
from dsync.exceptions import ObjectAlreadyExists, ObjectNotFound

from .conftest import Site, Device


def test_generic_dsync_methods(generic_dsync, generic_dsync_model):
    generic_dsync.load()  # no-op
    assert len(generic_dsync.__datas__) == 0
    generic_dsync.sync_from(generic_dsync)  # no-op
    generic_dsync.sync_to(generic_dsync)  # no-op

    diff = generic_dsync.diff_from(generic_dsync)
    assert diff.has_diffs() is False
    diff = generic_dsync.diff_to(generic_dsync)
    assert diff.has_diffs() is False

    # TODO: sync_from_diff_element, diff_objects, [create|update|delete]_object, default_[create|update|delete]

    assert generic_dsync.get("anything", ["myname"]) is None
    assert generic_dsync.get(DSyncModel, []) is None

    assert list(generic_dsync.get_all("anything")) == []
    assert list(generic_dsync.get_all(DSyncModel)) == []

    assert generic_dsync.get_by_uids(["any", "another"], "anything") == []
    assert generic_dsync.get_by_uids(["any", "another"], DSyncModel) == []

    generic_dsync.add(generic_dsync_model)
    with pytest.raises(ObjectAlreadyExists):
        generic_dsync.add(generic_dsync_model)

    assert generic_dsync.get(DSyncModel, []) == generic_dsync_model
    # TODO - this errors because DSyncModel.get_type() returns None, rather than a str
    # assert generic_dsync.get(DSyncModel.get_type(), []) == generic_dsync_model
    assert generic_dsync.get("", []) is None
    assert generic_dsync.get(DSyncModel, ["myname"]) is None

    assert list(generic_dsync.get_all(DSyncModel)) == [generic_dsync_model]
    # TODO - this errors because DSyncModel.get_type() returns None, rather than a str
    # assert list(generic_dsync.get_all(DSyncModel.get_type())) == [generic_dsync_model]
    assert list(generic_dsync.get_all("anything")) == []

    assert generic_dsync.get_by_uids([""], DSyncModel) == [generic_dsync_model]
    # TODO - this errors because DSyncModel.get_type() returns None, rather than a str
    # assert generic_dsync.get_by_uids([""], DSyncModel.get_type()) == [generic_dsync_model]
    assert generic_dsync.get_by_uids(["myname"], DSyncModel) == []
    assert generic_dsync.get_by_uids(["aname", "", "anothername"], DSyncModel) == [generic_dsync_model]

    generic_dsync.remove(generic_dsync_model)
    with pytest.raises(ObjectNotFound):
        generic_dsync.remove(generic_dsync_model)

    assert generic_dsync.get(DSyncModel, []) is None
    assert list(generic_dsync.get_all(DSyncModel)) == []
    assert generic_dsync.get_by_uids([""], DSyncModel) == []


def test_dsync_subclass_methods(backend_a, backend_b):
    """Test DSync APIs on an actual concrete subclass."""

    diff_aa = backend_a.diff_from(backend_a)
    assert diff_aa.has_diffs() is False
    diff_aa = backend_a.diff_to(backend_a)
    assert diff_aa.has_diffs() is False
    diff_ab = backend_a.diff_to(backend_b)
    assert diff_ab.has_diffs() is True
    diff_ba = backend_a.diff_from(backend_b)
    assert diff_ba.has_diffs() is True
    # TODO: check contents of diff_ab and diff_ba?

    # TODO: sync_[from|to](_diff_element)?, diff_objects, [create|update|delete]_object, default_[create|update|delete]

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
