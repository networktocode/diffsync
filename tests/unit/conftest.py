"""Used to setup fixtures to be used through tests"""
from typing import List, Optional

import pytest

from dsync import DSync, DSyncModel


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
    _attributes = ("role",)
    _children = {"interface": "interfaces"}

    name: str
    site_name: str  # note this is not included in _attributes
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


class BackendA(DSync):
    """An example subclass of DSync."""

    site = Site
    device = Device
    interface = Interface

    top_level = ["site"]

    DATA = {
        "nyc": {
            "nyc-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
            "nyc-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
        },
        "sfo": {
            "sfo-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
            "sfo-spine2": {"role": "spine", "interfaces": {"eth0": "TBD", "eth1": "ddd"}},
        },
    }

    def load(self):
        """Initialize the BackendA Object by loading some site, device and interfaces from DATA_A."""

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


@pytest.fixture
def backend_a():
    """Provide an instance of BackendA subclass of DSync."""
    dsync = BackendA()
    dsync.load()
    return dsync


class BackendB(BackendA):
    """Another DSync subclass with different data from BackendA."""

    DATA = {
        "nyc": {
            "nyc-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0/0", "eth1": "Interface 1"}},
            "nyc-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
        },
        "sfo": {
            "sfo-spine1": {"role": "leaf", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
            "sfo-spine2": {"role": "spine", "interfaces": {"eth0": "TBD", "eth1": "ddd"}},
        },
    }


@pytest.fixture
def backend_b():
    """Provide an instance of BackendB subclass of DSync."""
    dsync = BackendB()
    dsync.load()
    return dsync
