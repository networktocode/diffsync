"""Example of a DiffSync adapter implementation.

Copyright (c) 2020 Network To Code, LLC <info@networktocode.com>

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

# pylint: disable=wrong-import-order
from diffsync import Adapter
from models import Site, Device, Interface  # pylint: disable=no-name-in-module

DATA = {
    "nyc": {
        "nyc-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 1/1", "eth1": "Interface 1"}},
        "nyc-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
    },
    "sfo": {
        "sfo-spine1": {"role": "leaf", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"}},
        "sfo-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0/0", "eth1": "Interface 0/1"}},
    },
}


class BackendC(Adapter):
    """Example of a DiffSync adapter implementation."""

    site = Site
    device = Device
    interface = Interface

    top_level = ["site"]

    nb = None

    def load(self):
        """Initialize the BackendC Object by loading some site, device and interfaces from DATA."""
        for site_name, site_data in DATA.items():
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
