"""IPAM B adapter."""

import os

import yaml
from models import Prefix  # pylint: disable=no-name-in-module

from diffsync import Adapter

dirname = os.path.dirname(os.path.realpath(__file__))


class IpamBPrefix(Prefix):
    """Implementation of Prefix create/update/delete methods for IPAM B."""

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Create a Prefix record in IPAM B."""
        adapter.data.append(
            {
                "network": ids["prefix"].split("/")[0],
                "prefix_length": int(ids["prefix"].split("/")[1]),
                "vrf": attrs["vrf"],
                "vlan_id": attrs["vlan_id"],
                "tenant": attrs["tenant"] if attrs["tenant"] else None,
            }
        )

        return super().create(adapter, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update a Prefix record in IPAM B."""
        network = self.prefix.split("/")[0]
        prefix_length = int(self.prefix.split("/")[1])

        for elem in self.adapter.data:
            if elem["network"] == network and elem["prefix_length"] == prefix_length:
                if "vrf" in attrs:
                    elem["vrf"] = attrs["vrf"]
                if "vlan_id" in attrs:
                    elem["vlan_id"] = attrs["vlan_id"]
                if "tenant" in attrs:
                    elem["tenant"] = attrs["tenant"]
                break

        return super().update(attrs)

    def delete(self):
        """Update a Prefix record in IPAM B."""
        network = self.prefix.split("/")[0]
        prefix_length = int(self.prefix.split("/")[1])

        for index, elem in enumerate(self.adapter.data):
            if elem["network"] == network and elem["prefix_length"] == prefix_length:
                del self.adapter.data[index]
                break

        return super().delete()


class IpamB(Adapter):
    """IPAM A DiffSync adapter implementation."""

    prefix = IpamBPrefix

    top_level = ["prefix"]

    def __init__(self, *args, **kwargs):
        """Initialize the IPAM B Adapter."""
        super().__init__(*args, **kwargs)

        with open(os.path.join(dirname, "data", "ipam_b.yml"), encoding="utf-8") as data_file:
            self.data = yaml.safe_load(data_file)

    def load(self):
        """Initialize the Ipam B Object by loading from DATA."""
        for prefix_data in self.data:
            prefix = self.prefix(
                prefix=f"{prefix_data['network']}/{prefix_data['prefix_length']}",
                vrf=prefix_data["vrf"],
                vlan_id=prefix_data["vlan_id"],
                tenant=prefix_data["tenant"],
            )
            self.add(prefix)

    def sync_complete(self, source, *args, **kwargs):
        """Clean up function for DiffSync sync."""
        with open(os.path.join(dirname, "data", "ipam_b.yml"), encoding="utf-8", mode="w") as data_file:
            yaml.safe_dump(self.data, data_file)

        return super().sync_complete(source, *args, **kwargs)
