"""IPAM A adapter."""
import os
import ipaddress
import yaml
from models import Prefix  # pylint: disable=no-name-in-module
from diffsync import Adapter

dirname = os.path.dirname(os.path.realpath(__file__))


class IpamAPrefix(Prefix):
    """Implementation of Prefix create/update/delete methods for IPAM A."""

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Create a Prefix record in IPAM A."""
        adapter.data.append(
            {
                "cidr": ids["prefix"],
                "family": ipaddress.ip_address(ids["prefix"].split("/")[0]).version,
                "vrf": attrs["vrf"],
                "vlan": f'VLAN{attrs["vlan_id"]}',
                "customer_id": attrs["tenant"] if attrs["tenant"] else None,
            }
        )

        return super().create(adapter, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update a Prefix record in IPAM A."""
        for elem in self.adapter.data:
            if elem["cidr"] == self.prefix:
                if "vrf" in attrs:
                    elem["vrf"] = attrs["vrf"]
                if "vlan_id" in attrs:
                    elem["vlan_id"] = f'VLAN{attrs["vlan_id"]}'
                if "tenant" in attrs:
                    elem["customer_id"] = attrs["tenant"]
                break

        return super().update(attrs)

    def delete(self):
        """Delete a Prefix record in IPAM A."""
        for index, elem in enumerate(self.adapter.data):
            if elem["cidr"] == self.prefix:
                del self.adapter.data[index]
                break

        return super().delete()


class IpamA(Adapter):
    """IPAM A DiffSync adapter implementation."""

    prefix = IpamAPrefix

    top_level = ["prefix"]

    def __init__(self, *args, **kwargs):
        """Initialize the IPAM A Adapter."""
        super().__init__(*args, **kwargs)

        with open(os.path.join(dirname, "data", "ipam_a.yml"), encoding="utf-8") as data_file:
            self.data = yaml.safe_load(data_file)

    def load(self):
        """Load prefixes from IPAM A."""
        for subnet in self.data:
            prefix = self.prefix(
                prefix=subnet["cidr"],
                vrf=subnet["vrf"],
                vlan_id=int(subnet["vlan"].lstrip("VLAN")),
                tenant=subnet["customer_id"],
            )
            self.add(prefix)

    def sync_complete(self, source, *args, **kwargs):
        """Clean up function for DiffSync sync."""
        with open(os.path.join(dirname, "data", "ipam_a.yml"), encoding="utf-8", mode="w") as data_file:
            yaml.safe_dump(self.data, data_file)

        return super().sync_complete(source, *args, **kwargs)
