"""Example of a DiffSync adapter implementation using new helper methods.

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

from models import Site, Device, Interface  # pylint: disable=no-name-in-module
from diffsync import Adapter

BACKEND_DATA_A = [
    {
        "name": "nyc-spine1",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"},
        "site": "nyc",
    },
    {
        "name": "nyc-spine2",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"},
        "site": "nyc",
    },
    {
        "name": "sfo-spine1",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"},
        "site": "sfo",
    },
    {
        "name": "sfo-spine2",
        "role": "spine",
        "interfaces": {"eth0": "TBD", "eth1": "ddd", "eth2": "Interface 2"},
        "site": "sfo",
    },
]
BACKEND_DATA_B = [
    {
        "name": "atl-spine1",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"},
        "site": "atl",
    },
    {
        "name": "atl-spine2",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"},
        "site": "atl",
    },
    {
        "name": "nyc-spine1",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0/0", "eth1": "Interface 1"},
        "site": "nyc",
    },
    {
        "name": "nyc-spine2",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"},
        "site": "nyc",
    },
    {"name": "sfo-spine1", "role": "leaf", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}, "site": "sfo"},
    {"name": "sfo-spine2", "role": "spine", "interfaces": {"eth0": "TBD", "eth1": "ddd"}, "site": "sfo"},
]


class BackendA(Adapter):
    """Example of a DiffSync adapter implementation."""

    site = Site
    device = Device
    interface = Interface

    top_level = ["device"]

    type = "Backend A"

    def load(self):
        """Initialize the BackendA Object by loading some site, device and interfaces from DATA."""
        for device_data in BACKEND_DATA_A:
            device, instantiated = self.get_or_instantiate(
                self.device, {"name": device_data["name"]}, {"role": device_data["role"]}
            )

            site, instantiated = self.get_or_instantiate(self.site, {"name": device_data["site"]})
            if instantiated:
                device.add_child(site)

            for intf_name, desc in device_data["interfaces"].items():
                intf, instantiated = self.update_or_instantiate(
                    self.interface, {"name": intf_name, "device_name": device_data["name"]}, {"description": desc}
                )
                if instantiated:
                    device.add_child(intf)


class BackendB(Adapter):
    """Example of a DiffSync adapter implementation."""

    site = Site
    device = Device
    interface = Interface

    top_level = ["device"]

    type = "Backend B"

    def load(self):
        """Initialize the BackendB Object by loading some site, device and interfaces from DATA."""
        for device_data in BACKEND_DATA_B:
            device, instantiated = self.get_or_instantiate(
                self.device, {"name": device_data["name"]}, {"role": device_data["role"]}
            )

            site, instantiated = self.get_or_instantiate(self.site, {"name": device_data["site"]})
            if instantiated:
                device.add_child(site)

            for intf_name, desc in device_data["interfaces"].items():
                intf, instantiated = self.get_or_instantiate(
                    self.interface, {"name": intf_name, "device_name": device_data["name"]}, {"description": desc}
                )
                if instantiated:
                    device.add_child(intf)
