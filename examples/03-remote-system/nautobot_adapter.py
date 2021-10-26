"""DiffSync Adapter for Nautobot to manage regions."""
import os
import pynautobot  # pylint: disable=import-error

from nautobot_models import NautobotCountry, NautobotRegion

from diffsync import DiffSync

# pylint: disable=attribute-defined-outside-init

NAUTOBOT_URL = os.getenv("NAUTOBOT_URL", "https://demo.nautobot.com")
NAUTOBOT_TOKEN = os.getenv("NAUTOBOT_TOKEN", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

CUSTOM_FIELDS = [
    {
        "name": "country_population",
        "display": "Population (nbr people)",
        "content_types": ["dcim.region"],
        "type": "integer",
        "description": "Number of inhabitant per country",
    }
]


class NautobotAdapter(DiffSync):
    """Example of a DiffSync adapter implementation using pynautobot to communicate with a remote Nautobot system."""

    # We are using NautobotCountry and NautobotRegion instead of Region and Country
    # because we are using these classes to manage the logic to integrate with Nautobot
    # NautobotRegion is just a small extension to store the UUID and does not support any CRUD operation toward Nautobot
    # NautobotCountry supports the creation, update or deletion of a country in Nautobot
    region = NautobotRegion
    country = NautobotCountry

    # When doing a diff or a sync between 2 adapters,
    #  diffsync will recursively check all models defined at the top level and their children.
    # Since countries are defined as children of a region, we don't need to list country here
    top_level = ["region"]

    # Human readable name of the Adapter,
    # mainly used when doing a diff to indicate where each data is coming from
    type = "Nautobot"

    def load(self):
        """Load all data from Nautobot into the internal cache after transformation."""
        # Initialize pynautobot to interact with Nautobot and store it within the adapter
        # to reuse it later
        self.nautobot = pynautobot.api(url=NAUTOBOT_URL, token=NAUTOBOT_TOKEN)

        # Pull all regions from Nautobot, which includes all regions and all countries
        regions = self.nautobot.dcim.regions.all()

        # Extract Region first (top level object without parent)
        for region in regions:
            if region.parent:
                continue

            item = self.region(slug=region.slug, name=region.name, remote_id=region.id)
            self.add(item)

        # Extract All countries (second level, country must have a parent)
        for country in regions:
            if not country.parent:
                continue

            parent = self.get(self.region, country.parent.slug)

            item = self.country(
                slug=country.slug,
                name=country.name,
                region=parent.slug,
                population=country.custom_fields.get("country_population", None),
                remote_id=country.id,
            )
            self.add(item)
            parent.add_child(item)

    def sync_from(self, *args, **kwargs):  # pylint: disable=signature-differs
        """Sync the data with Nautobot but first ensure that all the required Custom fields are present in Nautobot."""
        # Check if all required custom fields exist, create them if they don't
        for custom_field in CUSTOM_FIELDS:
            nb_cfs = self.nautobot.extras.custom_fields.filter(name=custom_field.get("name"))
            if not nb_cfs:
                self.nautobot.extras.custom_fields.create(**custom_field)

        super().sync_from(*args, **kwargs)
