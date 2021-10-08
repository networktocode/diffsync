import json

from slugify import slugify

from diffsync import DiffSync
from models import Region, Country

COUNTRIES_FILE = "countries.json"


class LocalAdapter(DiffSync):
    """DiffSync Adapter to Load the list of regions and countries from a local JSON file."""

    region = Region
    country = Country

    # Since all countries are associated with a region, we don't need to list country here
    # When doing a diff or a sync between 2 adapters,
    #  diffsync will recursively check all models defined at the top level and their children.
    top_level = ["region"]

    # Human readable name of the Adapter,
    # mainly used when doing a diff to indicate where each data is coming from
    type = "Local"

    def load(self, filename=COUNTRIES_FILE):
        """Load all regions and countries from a local JSON file."""

        data_file = open(filename, "r")
        countries = json.loads(data_file.read())

        # Load all regions first
        # A Region object will be create for each region and it will be store inside the object with self.add
        # To create a Region we are using "self.region" instead of "Region" directly to allow someone to extend this adapter without redefining everything.
        region_names = set([country.get("region") for country in countries])
        for region in region_names:
            self.add(self.region(slug=slugify(region), name=region))

        # Load all countries
        # A Country object will be create for each country, it will be store inside the object with self.add
        # and it will be linked to its parent with parent.add_child(item)
        for country in countries:

            # Retrive the parent region object from the internal cache.
            region = self.get(obj=self.region, identifier=slugify(country.get("region")))

            name = country.get("country")

            # The population is store in thousands in the local file so we need to convert it
            population = int(float(country.get("pop2021")) * 1000)

            item = self.country(slug=slugify(name), name=name, population=population, region=region.slug)
            self.add(item)

            region.add_child(item)

        data_file.close()
