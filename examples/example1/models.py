"""Example models."""
from typing import List, Optional
from dsync import DSyncModel


class Site(DSyncModel):
    """Example model of a geographic Site."""

    _modelname = "site"
    _identifiers = ("name",)
    _shortname = ()
    _attributes = ()
    _children = {"device": "devices"}

    name: str
    devices: List = list()


class Device(DSyncModel):
    """Example model of a network Device."""

    _modelname = "device"
    _identifiers = ("name",)
    _attributes = ()
    _children = {"interface": "interfaces"}

    name: str
    site_name: str
    role: str
    interfaces: List = list()


class Interface(DSyncModel):
    """Example model of a network Interface."""

    _modelname = "interface"
    _identifiers = ("device_name", "name")
    _shortname = ("name",)
    _attributes = ("description",)

    name: str
    device_name: str

    description: Optional[str]
