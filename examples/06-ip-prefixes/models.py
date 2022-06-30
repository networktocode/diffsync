"""DiffSync models."""
from typing import Optional
from diffsync import DiffSyncModel


class Prefix(DiffSyncModel):
    """Example model of a Prefix."""

    _modelname = "prefix"
    _identifiers = ("prefix",)
    _attributes = ("vrf", "vlan_id", "tenant")

    prefix: str
    vrf: Optional[str]
    vlan_id: Optional[int]
    tenant: Optional[str]
