"""Diffsync adapter class for PeeringDB."""
import requests
from slugify import slugify
import pycountry

from diffsync import DiffSync
from diffsync.exceptions import ObjectNotFound

from .models import RegionModel, SiteModel

PEERINGDB_URL = "https://peeringdb.com/"


class PeeringDB(DiffSync):
    """DiffSync adapter using pysnow to communicate with PeeringDB."""

    # Model classes used by this adapter class
    region = RegionModel
    site = SiteModel

    # Top-level class labels, i.e. those classes that are handled directly rather than as children of other models
    top_level = ("region", "site")

    def __init__(self, *args, ix_id, **kwargs):
        """Initialize the PeeringDB adapter."""
        super().__init__(*args, **kwargs)
        self.ix_id = ix_id

    def load(self):
        """Load data via from PeeringDB."""
        ix_data = requests.get(f"{PEERINGDB_URL}/api/ix/{self.ix_id}").json()

        for fac in ix_data["data"][0]["fac_set"]:
            # PeeringDB has no Region entity, so we must avoid duplicates
            try:
                self.get(self.region, fac["city"])
            except ObjectNotFound:
                region = self.region(
                    name=fac["city"],
                    slug=slugify(fac["city"]),
                    parent_name=pycountry.countries.get(alpha_2=fac["country"]).name,
                )
                self.add(region)

            site = self.site(
                name=fac["name"],
                slug=slugify(fac["name"]),
                status_slug="active",
                region_name=fac["city"],
                description=fac["notes"],
                longitude=fac["longitude"],
                latitude=fac["latitude"],
                pk=fac["id"],
            )
            self.add(site)
