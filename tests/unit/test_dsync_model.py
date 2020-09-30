"""Unit tests for the DSyncModel class."""

import pytest

from dsync.exceptions import ObjectStoreWrongType

def test_generic_dsync_model_methods(generic_dsync_model, make_site):
    """Check the default behavior of various APIs of a DSyncModel."""
    assert str(generic_dsync_model) == ""
    assert repr(generic_dsync_model) == 'None ""'

    assert generic_dsync_model.get_type() == None
    assert generic_dsync_model.get_identifiers() == {}
    assert generic_dsync_model.get_attrs() == {}
    assert generic_dsync_model.get_unique_id() == ""
    assert generic_dsync_model.get_shortname() == ""

    with pytest.raises(ObjectStoreWrongType):
        generic_dsync_model.add_child(make_site())


def test_dsync_model_subclass_methods(make_site, make_device, make_interface):
    """Check that the DSyncModel APIs work correctly for various subclasses."""
    site1 = make_site()
    device1 = make_device()
    device1_eth0 = make_interface()

    assert str(site1) == "site1"
    assert str(device1) == "device1"
    assert str(device1_eth0) == "device1__eth0"

    assert repr(site1) == 'site "site1"'
    assert repr(device1) == 'device "device1"'
    assert repr(device1_eth0) == 'interface "device1__eth0"'

    assert site1.get_type() == "site"
    assert device1.get_type() == "device"
    assert device1_eth0.get_type() == "interface"

    assert site1.get_identifiers() == {"name": "site1"}
    assert device1.get_identifiers() == {"name": "device1"}
    assert device1_eth0.get_identifiers() == {"device_name": "device1", "name": "eth0"}
    # Ordering of identifiers must be consistent
    assert list(device1_eth0.get_identifiers().keys()) == ["device_name", "name"]

    assert site1.get_attrs() == {}  # note that identifiers are not included in get_attrs()
    assert device1.get_attrs() == {"role": "default"}  # site_name field is not in __attributes__, so not in get_attrs
    # TODO: since description is Optional, should it be omitted from get_attrs() if unset??
    assert device1_eth0.get_attrs() == {"interface_type": "ethernet", "description": None}
    # Ordering of attributes must be consistent
    assert list(device1_eth0.get_attrs().keys()) == ["interface_type", "description"]

    assert site1.get_unique_id() == "site1"
    assert device1.get_unique_id() == "device1"
    assert device1_eth0.get_unique_id() == "device1__eth0"

    assert site1.get_shortname() == "site1"
    assert device1.get_shortname() == "device1"
    assert device1_eth0.get_shortname() == "eth0"

    assert site1.devices == []
    site1.add_child(device1)
    assert site1.devices == ["device1"]
    # TODO add_child(device1) a second time should either be a no-op or an exception
    with pytest.raises(ObjectStoreWrongType):
        site1.add_child(device1_eth0)

    assert device1.interfaces == []
    device1.add_child(device1_eth0)
    assert device1.interfaces == ["device1__eth0"]
    # TODO add_child(device1_eth0) a second time should either be a no-op or an exception
    with pytest.raises(ObjectStoreWrongType):
        device1.add_child(site1)
