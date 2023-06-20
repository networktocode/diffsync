"""DiffSync models."""
from typing import Optional, Annotated
from diffsync import DiffSyncModel, DiffSyncFieldType


class Prefix(DiffSyncModel):
    """Example model of a Prefix."""

    _modelname = "prefix"

    prefix: Annotated[str, DiffSyncFieldType.IDENTIFIER]
    vrf: Annotated[Optional[str], DiffSyncFieldType.ATTRIBUTE]
    vlan_id: Annotated[Optional[int], DiffSyncFieldType.ATTRIBUTE]
    tenant: Annotated[Optional[str], DiffSyncFieldType.ATTRIBUTE]
