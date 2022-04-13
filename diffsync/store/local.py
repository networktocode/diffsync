"""LocalStore module."""

from collections import defaultdict
from typing import List, Mapping, Text, Type, Union, TYPE_CHECKING, Dict

from diffsync.exceptions import ObjectNotFound, ObjectAlreadyExists
from diffsync.store import BaseStore


if TYPE_CHECKING:
    from diffsync import DiffSyncModel


class LocalStore(BaseStore):
    """LocalStore class."""

    def __init__(self, *args, **kwargs) -> None:
        """Init method for LocalStore."""
        super().__init__(*args, **kwargs)

        self._data: Dict = defaultdict(dict)

    def get_all_model_names(self):
        """Get all the model names stored.

        Return:
            List[str]: List of all the model names.
        """
        return self._data.keys()

    def get(self, obj: Union[Text, "DiffSyncModel", Type["DiffSyncModel"]], identifier: Union[Text, Mapping]):  #
        """Get one object from the data store based on its unique id.

        Args:
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the object to retrieve
            identifier: Unique ID of the object to retrieve, or dict of unique identifier keys/values

        Raises:
            ValueError: if obj is a str and identifier is a dict (can't convert dict into a uid str without a model class)
            ObjectNotFound: if the requested object is not present
        """
        if isinstance(obj, str):
            modelname = obj
            if not hasattr(self, obj):
                object_class = None
            else:
                object_class = getattr(self, obj)
        else:
            object_class = obj
            modelname = obj.get_type()

        if isinstance(identifier, str):
            uid = identifier
        elif object_class:
            uid = object_class.create_unique_id(**identifier)
        else:
            raise ValueError(
                f"Invalid args: ({obj}, {identifier}): "
                f"either {obj} should be a class/instance or {identifier} should be a str"
            )

        if uid not in self._data[modelname]:
            raise ObjectNotFound(f"{modelname} {uid} not present in {str(self)}")
        return self._data[modelname][uid]

    def get_all(self, obj: Union[Text, "DiffSyncModel", Type["DiffSyncModel"]]) -> List["DiffSyncModel"]:  #
        """Get all objects of a given type.

        Args:
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve

        Returns:
            List[DiffSyncModel]: List of Object
        """
        if isinstance(obj, str):
            modelname = obj
        else:
            modelname = obj.get_type()

        return list(self._data[modelname].values())

    def get_by_uids(
        self, uids: List[Text], obj: Union[Text, "DiffSyncModel", Type["DiffSyncModel"]]  #
    ) -> List["DiffSyncModel"]:  #
        """Get multiple objects from the store by their unique IDs/Keys and type.

        Args:
            uids: List of unique id / key identifying object in the database.
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve

        Raises:
            ObjectNotFound: if any of the requested UIDs are not found in the store
        """
        if isinstance(obj, str):
            modelname = obj
        else:
            modelname = obj.get_type()

        results = []
        for uid in uids:
            if uid not in self._data[modelname]:
                raise ObjectNotFound(f"{modelname} {uid} not present in {str(self)}")
            results.append(self._data[modelname][uid])
        return results

    def add(self, obj: "DiffSyncModel"):  #
        """Add a DiffSyncModel object to the store.

        Args:
            obj (DiffSyncModel): Object to store

        Raises:
            ObjectAlreadyExists: if a different object with the same uid is already present.
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        existing_obj = self._data[modelname].get(uid)
        if existing_obj:
            if existing_obj is not obj:
                raise ObjectAlreadyExists(f"Object {uid} already present", obj)
            # Return so we don't have to change anything on the existing object and underlying data
            return

        if not obj.diffsync:
            obj.diffsync = self.diffsync

        self._data[modelname][uid] = obj

    def update(self, obj: "DiffSyncModel"):  #
        """Update a DiffSyncModel object to the store.

        Args:
            obj (DiffSyncModel): Object to update
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        existing_obj = self._data[modelname].get(uid)
        if existing_obj is obj:
            return

        self._data[modelname][uid] = obj

    def remove(self, obj: "DiffSyncModel", remove_children: bool = False):  #
        """Remove a DiffSyncModel object from the store.

        Args:
            obj (DiffSyncModel): object to remove
            remove_children (bool): If True, also recursively remove any children of this object

        Raises:
            ObjectNotFound: if the object is not present
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        if uid not in self._data[modelname]:
            raise ObjectNotFound(f"{modelname} {uid} not present in {str(self)}")

        if obj.diffsync:
            obj.diffsync = None

        del self._data[modelname][uid]

        if remove_children:
            for child_type, child_fieldname in obj.get_children_mapping().items():
                for child_id in getattr(obj, child_fieldname):
                    try:
                        child_obj = self.get(child_type, child_id)
                        self.remove(child_obj, remove_children=remove_children)
                    except ObjectNotFound:
                        # Since this is "cleanup" code, log an error and continue, instead of letting the exception raise
                        self._log.error(f"Unable to remove child {child_id} of {modelname} {uid} - not found!")

    def count(self, modelname=None):
        """Returns the number of elements of an specific model name."""
        if not modelname:
            return sum(len(entries) for entries in self._data.values())

        return len(self._data[modelname])
