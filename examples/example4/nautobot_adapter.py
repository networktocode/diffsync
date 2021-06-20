import os
from typing import Callable, ClassVar, Dict, List, Mapping, MutableMapping, Optional, Text, Tuple, Type, Union

import pynautobot

from diffsync import DiffSync, DiffSyncModel
from models import Region, Country

NAUTOBOT_URL = os.getenv("NAUTOBOT_URL", "https://demo.nautobot.com")
NAUTOBOT_TOKEN = os.getenv("NAUTOBOT_TOKEN", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")


class NautobotRegion(Region):
    """Extend the Region object to store Nautobot specific information.

    Region are represented in Nautobot as a dcim.region object without parent.
    """

    remote_id: str
    """Store the nautobot uuid in the object to allow update and delete of existing object."""

    @classmethod
    def convert_from(cls, diffsync, obj):
        """Convert a Nautobot dcim.region object to a Region Object."""
        countries = diffsync.nautobot.dcim.regions.filter(parent_id=obj.id)
        return cls(
            slug=obj.slug,
            diffsync=diffsync,
            name=obj.name,
            remote_id=obj.id,
            countries=[country.slug for country in countries],
        )

    # -----------------------------------------------------
    # Redefine the default methods to access the objects from the store to implement a storeless adapter
    # -----------------------------------------------------
    @classmethod
    def get_all(cls, diffsync):
        """Get all Region objects."""
        regions = diffsync.nautobot.dcim.regions.all()
        results = []
        for region in regions:
            if region.parent:
                continue

            if region.slug == "networktocode":
                continue

            results.append(cls.convert_from(diffsync, region))

        return results

    @classmethod
    def get_by_uids(cls, diffsync, uids):
        """Get a list of region identified by their unique identifiers."""
        regions = diffsync.nautobot.dcim.regions.filter(slug=uids)
        results = []
        for region in regions:
            results.append(cls.convert_from(diffsync, region))
        return results

    @classmethod
    def get(cls, diffsync, identifier):
        """Get one region identified by its unique identifier."""
        if isinstance(identifier, str):
            region = diffsync.nautobot.dcim.regions.get(slug=identifier)
        elif isinstance(identifier, dict):
            region = diffsync.nautobot.dcim.regions.get(**identifier)
        else:
            raise TypeError
        return cls.convert_from(diffsync, region)


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

    @classmethod
    def convert_from(cls, diffsync, obj):
        """Convert a Nautobot Region object into a Country object."""
        return cls(
            diffsync=diffsync,
            slug=obj.slug,
            name=obj.name,
            region=obj.parent.slug,
            subregion=obj.description,
            remote_id=obj.id,
        )

    # -----------------------------------------------------
    # Redefine the default methods to access the objects from the store to implement a storeless adapter
    # -----------------------------------------------------
    @classmethod
    def get_all(cls, diffsync):
        """Get all Country objects from Nautobot"""
        regions = diffsync.nautobot.dcim.regions.all()
        results = []
        for region in regions:
            if not region.parent:
                continue
            results.append(cls.convert_from(diffsync, region))

        return results

    @classmethod
    def get_by_uids(cls, diffsync, uids):
        """Get a list of Country identified by their unique identifiers."""
        regions = diffsync.nautobot.dcim.regions.filter(slug=uids)
        results = []
        for region in regions:
            results.append(cls.convert_from(diffsync, region))

        return results

    @classmethod
    def get(cls, diffsync, identifier):
        """Return an instance of Country based on its unique identifier."""
        if isinstance(identifier, str):
            region = diffsync.nautobot.dcim.regions.get(slug=identifier)
        elif isinstance(identifier, dict):
            region = diffsync.nautobot.dcim.regions.get(**identifier)
        else:
            raise TypeError

        return cls.convert_from(diffsync, region)


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
        """Nothing to load here since this adapter is not leveraging the internal datastore."""

        # Initialize pynautobot to interact with Nautobot and store it within the adapter
        # to reuse it later
        self.nautobot = pynautobot.api(url=NAUTOBOT_URL, token=NAUTOBOT_TOKEN,)

        return

    # -----------------------------------------------------
    # Redefine the default methods to access the objects from the store to implement a storeless adapter
    #  get / get_all / get_by_uids, add and remove are the main methods to interact with the datastore.
    # For get / get_all / get_by_uids the adapter is acting as passthrough and it's calling the same method on the model itself
    # -----------------------------------------------------
    def get(
        self, obj: Union[Text, DiffSyncModel, Type[DiffSyncModel]], identifier: Union[Text, Mapping]
    ) -> DiffSyncModel:
        """Get one object from the data store based on its unique id.

        This method is acting as passthrough and it's calling the same method on the model itself.

        Args:
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the object to retrieve
            identifier: Unique ID of the object to retrieve, or dict of unique identifier keys/values

        Raises:
            ValueError: if obj is a str and identifier is a dict (can't convert dict into a uid str without a model class)
            ObjectNotFound: if the requested object is not present
        """
        if isinstance(obj, str):
            obj = getattr(self, obj)

        return obj.get(diffsync=self, identifier=identifier)

    def get_all(self, obj: Union[Text, DiffSyncModel, Type[DiffSyncModel]]) -> List[DiffSyncModel]:
        """Get all objects of a given type.

        This method is acting as passthrough and it's calling the same method on the model itself.

        Args:
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve
        Returns:
            List[DiffSyncModel]: List of Object
        """
        if isinstance(obj, str):
            obj = getattr(self, obj)

        return obj.get_all(diffsync=self)

    def get_by_uids(
        self, uids: List[Text], obj: Union[Text, DiffSyncModel, Type[DiffSyncModel]]
    ) -> List[DiffSyncModel]:
        """Get multiple objects from the store by their unique IDs/Keys and type.

        This method is acting as passthrough and it's calling the same method on the model itself.

        Args:
            uids: List of unique id / key identifying object in the database.
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve
        
        Raises:
            ObjectNotFound: if any of the requested UIDs are not found in the store
        """
        if isinstance(obj, str):
            obj = getattr(self, obj)

        return obj.get_by_uids(diffsync=self, uids=uids)

    def add(self, obj: DiffSyncModel):
        """Add a DiffSyncModel object to the store.

        Args:
            obj (DiffSyncModel): Object to store

        Raises:
            ObjectAlreadyExists: if an object with the same uid is already present
        """
        pass

    def remove(self, obj: DiffSyncModel):
        """Remove a DiffSyncModel object from the store.

        Args:
            obj (DiffSyncModel): object to remove
            remove_children (bool): If True, also recursively remove any children of this object

        Raises:
            ObjectNotFound: if the object is not present
        """
        pass
