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
from typing import List, Optional, Annotated
from diffsync import DiffSyncModel, DiffSyncFieldType


class Site(DiffSyncModel):
    """Example model of a geographic Site."""

    _modelname = "site"
    _shortname = ()

    name: Annotated[str, DiffSyncFieldType.IDENTIFIER]


class Device(DiffSyncModel):
    """Example model of a network Device."""

    _modelname = "device"

    name: Annotated[str, DiffSyncFieldType.IDENTIFIER]
    site_name: Optional[str]  # note that this attribute is NOT annotated
    role: Optional[str]  # note that this attribute is NOT annotated
    interfaces: Annotated[List[str], DiffSyncFieldType.CHILDREN, "interface"] = []
    sites: Annotated[List[str], DiffSyncFieldType.CHILDREN, "site"] = []


class Interface(DiffSyncModel):
    """Example model of a network Interface."""

    _modelname = "interface"
    _shortname = ("name",)

    name: Annotated[str, DiffSyncFieldType.IDENTIFIER]
    device_name: Annotated[str, DiffSyncFieldType.IDENTIFIER]

    description: Annotated[Optional[str], DiffSyncFieldType.ATTRIBUTE]
