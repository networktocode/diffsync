"""Extension of the Base model for the Nautobot DiffSync Adapter to manage the CRUD operations."""
import pynautobot  # pylint: disable=import-error

from models import Region, Country  # pylint: disable=no-name-in-module

from diffsync import DiffSync


# pylint: disable=no-member,too-few-public-methods


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
    def create(cls, diffsync: DiffSync, ids: dict, attrs: dict):
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
                custom_fields=dict(population=attrs.get("population")),
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
        if "population" in attrs:
            remote.custom_fields["country_population"] = attrs.get("population")
        if "name" in attrs:
            remote.name = attrs.get("name")

        remote.save()
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
