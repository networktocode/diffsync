import os
import pynautobot

from diffsync import DiffSync
from models import Region, Country

NAUTOBOT_URL = os.getenv("NAUTOBOT_URL", "https://demo.nautobot.com")
NAUTOBOT_TOKEN = os.getenv("NAUTOBOT_TOKEN", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")


class NautobotRegion(Region):
    """Extend the Region object to store Nautobot specific information.

    Region are represented in Nautobot as a dcim.region object without parent.
    """

    remote_id: str
    """Store the nautobot uuid in the object to allow update and delete of existing object."""


class NautobotCountry(Country):
    """Extend the Country to manage Country in Nautobot. CREATE/UPDATE/DELETE.
    
    Country are represented in Nautobot as a dcim.region object as well but a country must have a parent.
    Subregion information will be store in the description of the object in Nautobot
    """

    remote_id: str
    """Store the nautobot uuid in the object to allow update and delete of existing object."""

    @classmethod
    def create(cls, diffsync: "DiffSync", ids: dict, attrs: dict):
        """Create a country object in Nautobot.

        Args:
            diffsync: The master data store for other DiffSyncModel instances that we might need to reference
            ids: Dictionary of unique-identifiers needed to create the new object
            attrs: Dictionary of additional attributes to set on the new object

        Returns:
            NautobotCountry: DiffSync object newly created
        """

        # Retrieve the parent region in internal cache to access its UUID
        #  because the UUID is required to associate the object to its parent region in Nautobot
        region = diffsync.get(diffsync.region, attrs.get("region"))

        # Create the new country in Nautobot and attach it to its parent
        try:
            country = diffsync.nautobot.dcim.regions.create(
                slug=ids.get("slug"),
                name=attrs.get("name"),
                description=attrs.get("subregion", None),
                parent=region.remote_id,
            )
            print(f"Created country : {ids} | {attrs} | {country.id}")

        except pynautobot.core.query.RequestError as exc:
            print(f"Unable to create country {ids} | {attrs} | {exc}")
            return None

        # Add the newly created remote_id and create the internal object for this resource.
        attrs["remote_id"] = country.id
        item = super().create(ids=ids, diffsync=diffsync, attrs=attrs)
        return item

    def update(self, attrs: dict):
        """Update a country object in Nautobot.

        Args:
            attrs: Dictionary of attributes to update on the object

        Returns:
            DiffSyncModel: this instance, if all data was successfully updated.
            None: if data updates failed in such a way that child objects of this model should not be modified.

        Raises:
            ObjectNotUpdated: if an error occurred.
        """

        # Retrive the pynautobot object from Nautobot since we only have the UUID internally
        remote = self.diffsync.nautobot.dcim.regions.get(self.remote_id)

        # Convert the internal attrs to Nautobot format
        nautobot_attrs = {}
        if "subregion" in attrs:
            nautobot_attrs["description"] = attrs.get("subregion")
        if "name" in attrs:
            nautobot_attrs["name"] = attrs.get("name")

        if nautobot_attrs:
            remote.update(data=nautobot_attrs)
            print(f"Updated Country {self.slug} | {attrs}")

        return super().update(attrs)

    def delete(self):
        """Delete a country object in Nautobot.

        Returns:
            NautobotCountry: DiffSync object
        """
        # Retrieve the pynautobot object and delete the object in Nautobot
        remote = self.diffsync.nautobot.dcim.regions.get(self.remote_id)
        remote.delete()

        super().delete()
        return self


class NautobotAdapter(DiffSync):
    """Example of a DiffSync adapter implementation."""

    # We are using NautobotCountry and NautobotRegion instead of Region and Country
    # because we are using these classes to manage the logic to integrate with Nautobot
    # NautobotRegion is just a small extension to store the UUID and do not support any CRUD operation toward Nautobot
    # NautobotCountry support the creation, update or deletion of a country in Nautobot
    region = NautobotRegion
    country = NautobotCountry

    # Since all countries are associated with a region, we don't need to list country here
    # When doing a diff or a sync between 2 adapters,
    #  diffsync will recursively check all models defined at the top level and their children.
    top_level = ["region"]

    # Human readable name of the Adapter,
    # mainly used when doing a diff to indicate where each data is coming from
    type = "Nautobot"

    def load(self):
        """Load all data from Nautobot into the internal cache after transformation."""

        # Initialize pynautobot to interact with Nautobot and store it within the adapter
        # to reuse it later
        self.nautobot = pynautobot.api(url=NAUTOBOT_URL, token=NAUTOBOT_TOKEN,)

        # Pull all regions from Nautobot, which includes all regions and all countries
        regions = self.nautobot.dcim.regions.all()

        # Extract Region first (top level object without parent)
        for region in regions:
            if region.parent:
                continue

            # We are excluding the networktocode because it's not present in the local file
            if region.slug == "networktocode":
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
                subregion=country.description,
                remote_id=country.id,
            )
            self.add(item)
            parent.add_child(item)
