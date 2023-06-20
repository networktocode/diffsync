"""DiffSyncModel subclasses for Nautobot-PeeringDB data sync."""
from typing import Optional, Union, List, Annotated
from uuid import UUID

from diffsync import DiffSyncModel, DiffSyncFieldType


class RegionModel(DiffSyncModel):
    """Shared data model representing a Region."""

    # Metadata about this model
    _modelname = "region"

    # Data type declarations for all identifiers and attributes
    name: Annotated[str, DiffSyncFieldType.IDENTIFIER]
    slug: Annotated[str, DiffSyncFieldType.ATTRIBUTE]
    description: Annotated[Optional[str], DiffSyncFieldType.ATTRIBUTE]
    parent_name: Annotated[Optional[str], DiffSyncFieldType.ATTRIBUTE]
    sites: Annotated[List, DiffSyncFieldType.CHILDREN, "sites"] = []

    # Not annotated, hence not included in diff calculations
    pk: Optional[UUID]


class SiteModel(DiffSyncModel):
    """Shared data model representing a Site in either of the local or remote Nautobot instances."""

    # Metadata about this model
    _modelname = "site"

    # To keep this example simple, we don't include **all** attributes of a Site here. But you could!
    name: Annotated[str, DiffSyncFieldType.IDENTIFIER]
    slug: Annotated[str, DiffSyncFieldType.ATTRIBUTE]
    status_slug: Annotated[str, DiffSyncFieldType.ATTRIBUTE]
    region_name: Annotated[Optional[str], DiffSyncFieldType.ATTRIBUTE]
    description: Annotated[Optional[str], DiffSyncFieldType.ATTRIBUTE]
    latitude: Annotated[Optional[float], DiffSyncFieldType.ATTRIBUTE]
    longitude: Annotated[Optional[float], DiffSyncFieldType.ATTRIBUTE]

    # Not in _attributes or _identifiers, hence not included in diff calculations
    pk: Optional[Union[UUID, int]]
