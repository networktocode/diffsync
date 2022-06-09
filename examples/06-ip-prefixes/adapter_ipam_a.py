"""IPAM A adapter."""
import ipaddress
from pathlib import Path
import yaml
from models import Prefix  # pylint: disable=no-name-in-module
from diffsync import DiffSync


class IpamAPrefix(Prefix):
    """Implementation of Prefix create/update/delete methods for IPAM A."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a Prefix record in IPAM A."""
        data = diffsync.load_yaml_data()

        data.append(
            {
                "cidr": ids["prefix"],
                "family": ipaddress.ip_address(ids["prefix"].split("/")[0]).version,
                "vrf": attrs["vrf"],
                "vlan": f'VLAN{attrs["vlan_id"]}',
                "customer_id": attrs["tenant"] if attrs["tenant"] else None,
            }
        )

        diffsync.write_yaml_data(data)

        return super().create(diffsync, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update a Prefix record in IPAM A."""
        data = self.diffsync.load_yaml_data()

        for elem in data:
            if elem["cidr"] == self.prefix:
                if "vrf" in attrs:
                    elem["vrf"] = attrs["vrf"]
                if "vlan_id" in attrs:
                    elem["vlan_id"] = f'VLAN{attrs["vlan_id"]}'
                if "tenant" in attrs:
                    elem["customer_id"] = attrs["tenant"]

                break

        self.diffsync.write_yaml_data(data)

        return super().update(attrs)

    def delete(self):
        """Delete a Prefix record in IPAM A."""
        data = self.diffsync.load_yaml_data()

        for index, elem in enumerate(data):
            if elem["cidr"] == self.prefix:
                del data[index]
                break

        self.diffsync.write_yaml_data(data)

        return super().delete()


class IpamA(DiffSync):
    """IPAM A DiffSync adapter implementation."""

    prefix = IpamAPrefix

    top_level = ["prefix"]

    @staticmethod
    def load_yaml_data():
        """Read data from a YAML file."""
        with open(Path.joinpath(Path().resolve(), "data", "ipam_a.yml"), encoding="utf-8") as data_file:
            return yaml.safe_load(data_file)

    @staticmethod
    def write_yaml_data(data):
        """Write data to a YAML file."""
        with open(Path.joinpath(Path().resolve(), "data", "ipam_a.yml"), encoding="utf-8", mode="w") as data_file:
            return yaml.safe_dump(data, data_file)

    def load(self):
        """Load prefixes from IPAM A."""
        for subnet in self.load_yaml_data():
            prefix = self.prefix(
                prefix=subnet["cidr"],
                vrf=subnet["vrf"],
                vlan_id=int(subnet["vlan"].lstrip("VLAN")),
                tenant=subnet["customer_id"],
            )
            self.add(prefix)
