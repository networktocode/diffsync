"""IPAM B adapter."""
import os
import yaml
from models import Prefix  # pylint: disable=no-name-in-module
from diffsync import DiffSync

dirname = os.path.dirname(os.path.realpath(__file__))


class IpamBPrefix(Prefix):
    """Implementation of Prefix create/update/delete methods for IPAM B."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a Prefix record in IPAM B."""
        data = diffsync.load_yaml_data()

        data.append(
            {
                "network": ids["prefix"].split("/")[0],
                "prefix_length": int(ids["prefix"].split("/")[1]),
                "vrf": attrs["vrf"],
                "vlan_id": attrs["vlan_id"],
                "tenant": attrs["tenant"] if attrs["tenant"] else None,
            }
        )

        diffsync.write_yaml_data(data)

        return super().create(diffsync, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update a Prefix record in IPAM B."""
        data = self.diffsync.load_yaml_data()

        network = self.prefix.split("/")[0]
        prefix_length = int(self.prefix.split("/")[1])

        for elem in data:
            if elem["network"] == network and elem["prefix_length"] == prefix_length:
                if "vrf" in attrs:
                    elem["vrf"] = attrs["vrf"]
                if "vlan_id" in attrs:
                    elem["vlan_id"] = attrs["vlan_id"]
                if "tenant" in attrs:
                    elem["tenant"] = attrs["tenant"]

                break

        self.diffsync.write_yaml_data(data)

        return super().update(attrs)

    def delete(self):
        """Update a Prefix record in IPAM B."""
        data = self.diffsync.load_yaml_data()

        network = self.prefix.split("/")[0]
        prefix_length = int(self.prefix.split("/")[1])

        for index, elem in enumerate(data):
            if elem["network"] == network and elem["prefix_length"] == prefix_length:
                del data[index]
                break

        self.diffsync.write_yaml_data(data)

        return super().delete()


class IpamB(DiffSync):
    """IPAM A DiffSync adapter implementation."""

    prefix = IpamBPrefix

    top_level = ["prefix"]

    @staticmethod
    def load_yaml_data():
        """Read data from a YAML file."""
        with open(os.path.join(dirname, "data", "ipam_b.yml"), encoding="utf-8") as data_file:
            return yaml.safe_load(data_file)

    @staticmethod
    def write_yaml_data(data):
        """Write data to a YAML file."""
        with open(os.path.join(dirname, "data", "ipam_b.yml"), encoding="utf-8", mode="w") as data_file:
            return yaml.safe_dump(data, data_file)

    def load(self):
        """Initialize the Ipam B Object by loading from DATA."""
        for prefix_data in self.load_yaml_data():
            prefix = self.prefix(
                prefix=f"{prefix_data['network']}/{prefix_data['prefix_length']}",
                vrf=prefix_data["vrf"],
                vlan_id=prefix_data["vlan_id"],
                tenant=prefix_data["tenant"],
            )
            self.add(prefix)
