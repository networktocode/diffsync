"""Used to setup fixtures to be used through tests"""
from typing import ClassVar, List, Optional, Tuple

import pytest

from dsync import DSync, DSyncModel
from dsync.diff import Diff


@pytest.fixture()
def give_me_success():
    """
    Provides True to make tests pass

    Returns:
        (bool): Returns True
    """
    return True


@pytest.fixture
def generic_dsync_model():
    """Provide a generic DSyncModel instance."""
    return DSyncModel()


class Site(DSyncModel):
    """Concrete DSyncModel subclass representing a site or location that contains devices."""

    _modelname = "site"
    _identifiers = ("name",)
    _children = {"device": "devices"}

    name: str
    devices: List = list()


@pytest.fixture
def make_site():
    """Factory for Site instances."""

    def site(name="site1", devices=None):
        """Provide an instance of a Site model."""
        if not devices:
            devices = []
        return Site(name=name, devices=devices)

    return site


class Device(DSyncModel):
    """Concrete DSyncModel subclass representing a device."""

    _modelname = "device"
    _identifiers = ("name",)
    _attributes: ClassVar[Tuple[str, ...]] = ("role",)
    _children = {"interface": "interfaces"}

    name: str
    site_name: Optional[str]  # note this is not included in _attributes
    role: str
    interfaces: List = list()


@pytest.fixture
def make_device():
    """Factory for Device instances."""

    def device(name="device1", site_name="site1", role="default", **kwargs):
        """Provide an instance of a Device model."""
        return Device(name=name, site_name=site_name, role=role, **kwargs)

    return device


class Interface(DSyncModel):
    """Concrete DSyncModel subclass representing an interface."""

    _modelname = "interface"
    _identifiers = ("device_name", "name")
    _shortname = ("name",)
    _attributes = ("interface_type", "description")

    device_name: str
    name: str

    interface_type: str = "ethernet"
    description: Optional[str]


@pytest.fixture
def make_interface():
    """Factory for Interface instances."""

    def interface(device_name="device1", name="eth0", **kwargs):
        """Provide an instance of an Interface model."""
        return Interface(device_name=device_name, name=name, **kwargs)

    return interface


@pytest.fixture
def generic_dsync():
    """Provide a generic DSync instance."""
    return DSync()


class GenericBackend(DSync):
    """An example semi-abstract subclass of DSync."""

    site = Site  # to be overridden by subclasses
    device = Device
    interface = Interface

    top_level = ["site"]

    DATA: dict = {}

    def load(self):
        """Initialize the Backend object by loading some site, device and interfaces from DATA."""
        for site_name, site_data in self.DATA.items():
            site = self.site(name=site_name)
            self.add(site)

            for device_name, device_data in site_data.items():
                device = self.device(name=device_name, role=device_data["role"], site_name=site_name)
                self.add(device)
                site.add_child(device)

                for intf_name, desc in device_data["interfaces"].items():
                    intf = self.interface(name=intf_name, device_name=device_name, description=desc)
                    self.add(intf)
                    device.add_child(intf)


class SiteA(Site):
    """Extend Site with a `people` list."""

    _children = {"device": "devices", "person": "people"}

    people: List = list()


class DeviceA(Device):
    """Extend Device with additional data fields."""

    _attributes = ("role", "tag")

    tag: str = ""


class PersonA(DSyncModel):
    """Concrete DSyncModel subclass representing a person; only used by BackendA."""

    _modelname = "person"
    _identifiers = ("name",)

    name: str


class BackendA(GenericBackend):
    """An example concrete subclass of DSync."""

    site = SiteA
    device = DeviceA
    person = PersonA

    DATA = {
        "nyc": {
            "nyc-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
            "nyc-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
        },
        "sfo": {
            "sfo-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
            "sfo-spine2": {"role": "spine", "interfaces": {"eth0": "TBD", "eth1": "ddd", "eth2": "Interface 2"}},
        },
        "rdu": {
            "rdu-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
            "rdu-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
        },
    }

    def load(self):
        """Extend the base load() implementation with subclass-specific logic."""
        super().load()
        person = self.person(name="Glenn Matthews")
        self.add(person)
        self.get("site", "rdu").add_child(person)


@pytest.fixture
def backend_a():
    """Provide an instance of BackendA subclass of DSync."""
    dsync = BackendA()
    dsync.load()
    return dsync


class SiteB(Site):
    """Extend Site with a `places` list."""

    _children = {"device": "devices", "place": "places"}

    places: List = list()


class DeviceB(Device):
    """Extend Device with a `vlans` list."""

    _attributes = ("role", "vlans")

    vlans: List = list()


class PlaceB(DSyncModel):
    """Concrete DSyncModel subclass representing a place; only used by BackendB."""

    _modelname = "place"
    _identifiers = ("name",)

    name: str


class BackendB(GenericBackend):
    """Another DSync concrete subclass with different data from BackendA."""

    site = SiteB
    device = DeviceB
    place = PlaceB

    DATA = {
        "nyc": {
            "nyc-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0/0", "eth1": "Interface 1"}},
            "nyc-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
        },
        "sfo": {
            "sfo-spine1": {"role": "leaf", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
            "sfo-spine2": {"role": "spine", "interfaces": {"eth0": "TBD", "eth1": "ddd", "eth3": "Interface 3"}},
        },
        "atl": {
            "atl-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
            "atl-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
        },
    }

    def load(self):
        """Extend the base load() implementation with subclass-specific logic."""
        super().load()
        place = self.place(name="Statue of Liberty")
        self.add(place)
        self.get("site", "nyc").add_child(place)


@pytest.fixture
def backend_b():
    """Provide an instance of BackendB subclass of DSync."""
    dsync = BackendB()
    dsync.load()
    return dsync


class TrackedDiff(Diff):
    """Subclass of Diff that knows when it's completed."""

    is_complete: bool = False

    def complete(self):
        """Function called when the Diff has been fully constructed and populated with data."""
        self.is_complete = True
