"""Main DiffSync models for example3."""
from typing import List, Optional
from diffsync import DiffSyncModel


class Region(DiffSyncModel):
    """Example model of a geographic region."""

    _modelname = "region"
    _identifiers = ("slug",)
    _attributes = ("name",)

    # By listing country as a child to Region
    # DiffSync will be able to recursively compare all regions including all their children
    _children = {"country": "countries"}

    slug: str
    name: str
    countries: List[str] = []


class Country(DiffSyncModel):
    """Example model of a Country.

    A country must be part of a region and has an attribute to capture its population.
    """

    _modelname = "country"
    _identifiers = ("slug",)
    _attributes = ("name", "region", "population")

    slug: str
    name: str
    region: str
    population: Optional[int]
