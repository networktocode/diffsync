"""Main DiffSync models for example3."""
from typing import List, Optional, Annotated
from diffsync import DiffSyncModel, DiffSyncFieldType


class Region(DiffSyncModel):
    """Example model of a geographic region."""

    _modelname = "region"

    slug: Annotated[str, DiffSyncFieldType.IDENTIFIER]
    name: Annotated[str, DiffSyncFieldType.ATTRIBUTE]

    # By annotating country as a child to Region
    # DiffSync will be able to recursively compare all regions including all their children
    countries: Annotated[List[str], DiffSyncFieldType.CHILDREN, "country"] = []


class Country(DiffSyncModel):
    """Example model of a Country.

    A country must be part of a region and has an attribute to capture its population.
    """

    _modelname = "country"

    slug: Annotated[str, DiffSyncFieldType.IDENTIFIER]
    name: Annotated[str, DiffSyncFieldType.ATTRIBUTE]
    region: Annotated[str, DiffSyncFieldType.ATTRIBUTE]
    population: Annotated[Optional[int], DiffSyncFieldType.ATTRIBUTE]
