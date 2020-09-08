"""Models """
from typing import Set, Dict, List, Optional
from dsync import DSyncModel


class Site(DSyncModel):
    """
    """

    __modelname__ = "site"
    __identifier__ = ["name"]
    __shortname__ = []
    __attributes__ = []
    __children__ = {"device": "devices"}

    name: str
    devices: List = list()


class Device(DSyncModel):
    """
    """

    __modelname__ = "device"
    __identifier__ = ["name"]
    __attributes__ = []
    __children__ = {"interface": "interfaces"}

    name: str
    site_name: str
    role: str
    interfaces: List = list()


class Interface(DSyncModel):
    """
    """

    __modelname__ = "interface"
    __identifier__ = ["device_name", "name"]
    __shortname__ = ["name"]
    __attributes__ = ["description"]

    name: str
    device_name: str

    description: Optional[str]
