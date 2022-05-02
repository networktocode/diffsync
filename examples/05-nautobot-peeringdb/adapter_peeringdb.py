"""Diffsync adapter class for PeeringDB."""
# pylint: disable=import-error,no-name-in-module
import requests
from slugify import slugify
import pycountry
from models import RegionModel, SiteModel
from diffsync import DiffSync
from diffsync.exceptions import ObjectNotFound


PEERINGDB_URL = "https://peeringdb.com/"


class PeeringDB(DiffSync):
    """DiffSync adapter using requests to communicate with PeeringDB."""

    # Model classes used by this adapter class
    region = RegionModel
    site = SiteModel

    # Top-level class labels, i.e. those classes that are handled directly rather than as children of other models
    top_level = ["region"]

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
                region = self.get(self.region, fac["city"])
            except ObjectNotFound:
                # Use pycountry to translate the country code (like "DE") to a country name (like "Germany")
                parent_name = pycountry.countries.get(alpha_2=fac["country"]).name
                # Add the country as a parent region if not already added
                try:
                    self.get(self.region, parent_name)
                except ObjectNotFound:
                    parent_region = self.region(
                        name=parent_name,
                        slug=slugify(parent_name),
                    )
                    self.add(parent_region)

                region = self.region(
                    name=fac["city"],
                    slug=slugify(fac["city"]),
                    parent_name=parent_name,
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
            region.add_child(site)
            self.update(region)  # pylint: disable=no-member
