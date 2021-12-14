"""DiffSyncModel subclasses for Nautobot-PeeringDB data sync."""
from typing import Optional, Union
from uuid import UUID

from diffsync import DiffSyncModel


class RegionModel(DiffSyncModel):
    """Shared data model representing a Region."""

    # Metadata about this model
    _modelname = "region"
    _identifiers = ("name",)
    _attributes = (
        "slug",
        "description",
        "parent_name",
    )

    # Data type declarations for all identifiers and attributes
    name: str
    slug: str
    description: Optional[str]
    parent_name: Optional[str]  # may be None

    # Not in _attributes or _identifiers, hence not included in diff calculations
    pk: Optional[UUID]


class SiteModel(DiffSyncModel):
    """Shared data model representing a Site in either of the local or remote Nautobot instances."""

    # Metadata about this model
    _modelname = "site"
    _identifiers = ("name",)
    # To keep this example simple, we don't include **all** attributes of a Site here. But you could!
    _attributes = (
        "slug",
        "status_slug",
        "region_name",
        "description",
        "latitude",
        "longitude",
    )

    # Data type declarations for all identifiers and attributes
    name: str
    slug: str
    status_slug: str
    region_name: Optional[str]  # may be None
    description: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]

    # Not in _attributes or _identifiers, hence not included in diff calculations
    pk: Optional[Union[UUID, int]]
