"""Example models.

Copyright (c) 2021 Network To Code, LLC <info@networktocode.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from typing import List, Optional
from diffsync import DiffSyncModel


class Site(DiffSyncModel):
    """Example model of a geographic Site."""

    _modelname = "site"
    _identifiers = ("name",)
    _shortname = ()
    _attributes = ()

    name: str


class Device(DiffSyncModel):
    """Example model of a network Device."""

    _modelname = "device"
    _identifiers = ("name",)
    _attributes = ()
    _children = {"interface": "interfaces", "site": "sites"}

    name: str
    site_name: Optional[str]  # note that this attribute is NOT included in _attributes
    role: Optional[str]  # note that this attribute is NOT included in _attributes
    interfaces: List = list()
    sites: List = list()


class Interface(DiffSyncModel):
    """Example model of a network Interface."""

    _modelname = "interface"
    _identifiers = ("device_name", "name")
    _shortname = ("name",)
    _attributes = ("description",)

    name: str
    device_name: str

    description: Optional[str]
