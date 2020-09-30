"""Used to setup fixtures to be used through tests"""
from typing import List, Optional

import pytest

from dsync import DSyncModel


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

    __modelname__ = "site"
    __identifier__ = ["name"]
    __children__ = {"device": "devices"}

    name: str
    devices: List = list()


@pytest.fixture
def make_site():
    """Factory for Site instances."""

    def site(name="site1", devices=[]):
        """Provide an instance of a Site model."""
        return Site(name=name, devices=devices)

    return site


class Device(DSyncModel):
    """Concrete DSyncModel subclass representing a device."""

    __modelname__ = "device"
    __identifier__ = ["name"]
    __attributes__ = ["role"]
    __children__ = {"interface": "interfaces"}

    name: str
    site_name: str  # note this is not included in __attributes__
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

    __modelname__ = "interface"
    __identifier__ = ["device_name", "name"]
    __shortname__ = ["name"]
    __attributes__ = ["interface_type", "description"]

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
