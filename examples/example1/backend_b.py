from dsync import DSync
from models import *

DATA = {
    "nyc": {
        "nyc-spine1": {"role": "spine", "interfaces": {"eth0": "Interface 0/0", "eth1": "Interface 1",}},
        "nyc-spine2": {"role": "spine", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1",}},
    },
    "sfo": {
        "sfo-spine1": {"role": "leaf", "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1",}},
        "sfo-spine2": {"role": "spine", "interfaces": {"eth0": "TBD", "eth1": "ddd",}},
    },
}


class BackendB(DSync):

    site = Site
    device = Device
    interface = Interface

    top_level = ['site']

    nb = None

    def init(self):
        """
        Initialize the BackendB Object by loading some site, device and interfaces 
        from DATA 
        """

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
