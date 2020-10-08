"""Unit tests for the DSyncModel class."""

from typing import List

import pytest

from dsync import DSyncModel
from dsync.exceptions import ObjectStoreWrongType, ObjectAlreadyExists, ObjectNotFound

from .conftest import Device, Interface


def test_generic_dsync_model_methods(generic_dsync_model, make_site):
    """Check the default behavior of various APIs of a DSyncModel."""
    assert str(generic_dsync_model) == ""
    assert repr(generic_dsync_model) == 'dsyncmodel ""'

    assert generic_dsync_model.get_type() == "dsyncmodel"
    assert generic_dsync_model.get_identifiers() == {}
    assert generic_dsync_model.get_attrs() == {}
    assert generic_dsync_model.get_unique_id() == ""
    assert generic_dsync_model.get_shortname() == ""

    with pytest.raises(ObjectStoreWrongType):
        generic_dsync_model.add_child(make_site())


def test_dsync_model_subclass_getters(make_site, make_device, make_interface):
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
    assert device1.get_attrs() == {"role": "default"}  # site_name field is not in _attributes, so not in get_attrs
    assert device1_eth0.get_attrs() == {"interface_type": "ethernet", "description": None}
    # Ordering of attributes must be consistent
    assert list(device1_eth0.get_attrs().keys()) == ["interface_type", "description"]

    assert site1.get_unique_id() == "site1"
    assert device1.get_unique_id() == "device1"
    assert device1_eth0.get_unique_id() == "device1__eth0"

    assert site1.get_shortname() == "site1"
    assert device1.get_shortname() == "device1"
    assert device1_eth0.get_shortname() == "eth0"


def test_dsync_model_subclass_add_remove(make_site, make_device, make_interface):
    """Check that the DSyncModel add_child/remove_child APIs work correctly for various subclasses."""
    site1 = make_site()
    device1 = make_device()
    device1_eth0 = make_interface()

    assert site1.devices == []
    site1.add_child(device1)
    assert site1.devices == ["device1"]
    with pytest.raises(ObjectStoreWrongType):
        site1.add_child(device1_eth0)
    with pytest.raises(ObjectAlreadyExists):
        site1.add_child(device1)

    site1.remove_child(device1)
    assert site1.devices == []
    with pytest.raises(ObjectStoreWrongType):
        site1.remove_child(device1_eth0)
    with pytest.raises(ObjectNotFound):
        site1.remove_child(device1)

    assert device1.interfaces == []
    device1.add_child(device1_eth0)
    assert device1.interfaces == ["device1__eth0"]
    with pytest.raises(ObjectStoreWrongType):
        device1.add_child(site1)
    with pytest.raises(ObjectAlreadyExists):
        device1.add_child(device1_eth0)

    device1.remove_child(device1_eth0)
    assert device1.interfaces == []
    with pytest.raises(ObjectStoreWrongType):
        device1.remove_child(site1)
    with pytest.raises(ObjectNotFound):
        device1.remove_child(device1_eth0)


def test_dsync_model_subclass_crud(generic_dsync):
    """Test basic CRUD operations on generic DSyncModel subclasses."""
    device1 = Device.create(generic_dsync, {"name": "device1"}, {"role": "spine"})
    assert isinstance(device1, Device)
    assert device1.dsync == generic_dsync
    assert device1.name == "device1"
    assert device1.role == "spine"

    device1_eth0 = Interface.create(
        generic_dsync, {"name": "eth0", "device_name": "device1"}, {"description": "some description"},
    )
    assert isinstance(device1_eth0, Interface)
    assert device1_eth0.dsync == generic_dsync
    assert device1_eth0.name == "eth0"
    assert device1_eth0.device_name == "device1"
    assert device1_eth0.description == "some description"

    device1 = device1.update({"site_name": "site1", "role": "leaf"})
    assert isinstance(device1, Device)
    assert device1.name == "device1"
    assert device1.site_name == "site1"
    assert device1.role == "leaf"

    device1_eth0 = device1_eth0.update({"description": ""})
    assert isinstance(device1_eth0, Interface)
    assert device1_eth0.name == "eth0"
    assert device1_eth0.device_name == "device1"
    assert device1_eth0.description == ""

    # TODO: negative tests - try to update identifiers with update(), for example

    device1 = device1.delete()
    assert isinstance(device1, Device)

    device1_eth0.delete()
    assert isinstance(device1_eth0, Interface)


def test_dsync_model_subclass_validation():
    """Verify that invalid subclasses of DSyncModel are detected at declaration time."""
    # Pylint would complain because we're not actually using any of the classes declared below
    # pylint: disable=unused-variable

    with pytest.raises(AttributeError) as excinfo:

        class BadIdentifier(DSyncModel):
            """Model with an _identifiers referencing a nonexistent field."""

            _identifiers = ("name",)

    assert "_identifiers" in str(excinfo.value)
    assert "name" in str(excinfo.value)

    with pytest.raises(AttributeError) as excinfo:

        class BadShortname(DSyncModel):
            """Model with a _shortname referencing a nonexistent field."""

            _identifiers = ("name",)
            _shortname = ("short_name",)

            name: str

    assert "_shortname" in str(excinfo.value)
    assert "short_name" in str(excinfo.value)

    with pytest.raises(AttributeError) as excinfo:

        class BadAttributes(DSyncModel):
            """Model with _attributes referencing a nonexistent field."""

            _identifiers = ("name",)
            _shortname = ("short_name",)
            _attributes = ("my_attr",)

            name: str
            # Note that short_name doesn't have a type annotation - making sure this works too
            short_name = "short_name"

    assert "_attributes" in str(excinfo.value)
    assert "my_attr" in str(excinfo.value)

    with pytest.raises(AttributeError) as excinfo:

        class BadChildren(DSyncModel):
            """Model with _children referencing a nonexistent field."""

            _identifiers = ("name",)
            _shortname = ("short_name",)
            _attributes = ("my_attr",)
            _children = {"device": "devices"}

            name: str
            short_name = "short_name"
            my_attr: int = 0

    assert "_children" in str(excinfo.value)
    assert "devices" in str(excinfo.value)

    with pytest.raises(AttributeError) as excinfo:

        class IdAttrOverlap(DSyncModel):
            """Model including a field in both _identifiers and _attributes."""

            _identifiers = ("name",)
            _attributes = ("name",)

            name: str

    assert "both _identifiers and _attributes" in str(excinfo.value)
    assert "name" in str(excinfo.value)

    with pytest.raises(AttributeError) as excinfo:

        class IdChildOverlap(DSyncModel):
            """Model including a field in both _identifiers and _children."""

            _identifiers = ("names",)
            _children = {"name": "names"}

            names: str

    assert "both _identifiers and _children" in str(excinfo.value)
    assert "names" in str(excinfo.value)

    with pytest.raises(AttributeError) as excinfo:

        class AttrChildOverlap(DSyncModel):
            """Model including a field in both _attributes and _children."""

            _attributes = ("devices",)
            _children = {"device": "devices"}

            devices: List

    assert "both _attributes and _children" in str(excinfo.value)
    assert "devices" in str(excinfo.value)


def test_dsync_model_subclass_inheritance():
    """Verify that the class validation works properly even with a hierarchy of subclasses."""
    # Pylint would complain because we're not actually using any of the classes declared below
    # pylint: disable=unused-variable
    class Alpha(DSyncModel):
        """A model class representing a single Greek letter."""

        _modelname = "alpha"
        _identifiers = ("name",)
        _shortname = ("name",)
        _attributes = ("letter",)
        _children = {"number": "numbers"}

        name: str
        letter: str
        numbers: List = list()

    class Beta(Alpha):
        """A model class representing a single Greek letter in both English and Spanish."""

        _modelname = "beta"
        _identifiers = ("name", "nombre")  # reference parent field, as well as a new field of our own
        _attributes = ("letter", "letra")  # reference parent field, as well as a new field of our own

        nombre: str
        letra: str

    beta = Beta(name="Beta", letter="β", nombre="Beta", letra="β")
    assert beta.get_unique_id() == "Beta__Beta"
    assert beta.get_attrs() == {"letter": "β", "letra": "β"}
