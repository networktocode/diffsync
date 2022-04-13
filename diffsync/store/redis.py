"""RedisStore module."""
import copy
import uuid
from pickle import loads, dumps  # nosec
from typing import List, Mapping, Text, Type, Union, TYPE_CHECKING

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from diffsync.exceptions import ObjectNotFound, ObjectStoreException, ObjectAlreadyExists
from diffsync.store import BaseStore

if TYPE_CHECKING:
    from diffsync import DiffSyncModel

REDIS_DIFFSYNC_ROOT_LABEL = "diffsync"


class RedisStore(BaseStore):
    """RedisStore class."""

    def __init__(self, *args, store_id=None, host="localhost", port=6379, url=None, db=0, **kwargs):
        """Init method for RedisStore."""
        super().__init__(*args, **kwargs)

        try:
            if url:
                self._store = Redis.from_url(url, db=db)
            else:
                self._store = Redis(host=host, port=port, db=db)

            if not self._store.ping():
                raise RedisConnectionError
        except RedisConnectionError:
            raise ObjectStoreException("Redis store is unavailable.") from RedisConnectionError

        self._store_id = store_id if store_id else str(uuid.uuid4())[:8]

        self._store_label = f"{REDIS_DIFFSYNC_ROOT_LABEL}:{self._store_id}"

    def __str__(self):
        """Render store name."""
        return f"{self.name}({self._store_id})"

    def get_all_model_names(self):
        """Get all the model names stored.

        Return:
            List[str]: List of all the model names.
        """
        # TODO: optimize it
        all_model_names = []
        for item in self._store.scan_iter(f"{self._store_label}:*"):
            model_name = item.split(b":")[2].decode()
            if model_name not in all_model_names:
                all_model_names.append(model_name)

        return all_model_names

    def _get_key_for_object(self, modelname, uid):
        return f"{self._store_label}:{modelname}:{uid}"

    def get(self, obj: Union[Text, "DiffSyncModel", Type["DiffSyncModel"]], identifier: Union[Text, Mapping]):
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

        try:
            obj_result = loads(self._store.get(self._get_key_for_object(modelname, uid)))  # nosec
            obj_result.diffsync = self.diffsync
        except TypeError:
            raise ObjectNotFound(f"{modelname} {uid} not present in Cache")  # pylint: disable=raise-missing-from

        return obj_result

    def get_all(self, obj: Union[Text, "DiffSyncModel", Type["DiffSyncModel"]]) -> List["DiffSyncModel"]:
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

        results = []
        for key in self._store.scan_iter(f"{self._store_label}:{modelname}:*"):
            try:
                obj_result = loads(self._store.get(key))  # nosec
                obj_result.diffsync = self.diffsync
                results.append(obj_result)
            except TypeError:
                raise ObjectNotFound(f"{key} not present in Cache")  # pylint: disable=raise-missing-from

        return results

    def get_by_uids(
        self, uids: List[Text], obj: Union[Text, "DiffSyncModel", Type["DiffSyncModel"]]
    ) -> List["DiffSyncModel"]:
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

            try:
                obj_result = loads(self._store.get(self._get_key_for_object(modelname, uid)))  # nosec
                obj_result.diffsync = self.diffsync
                results.append(obj_result)
            except TypeError:
                raise ObjectNotFound(f"{modelname} {uid} not present in Cache")  # pylint: disable=raise-missing-from

        return results

    def add(self, obj: "DiffSyncModel"):
        """Add a DiffSyncModel object to the store.

        Args:
            obj (DiffSyncModel): Object to store

        Raises:
            ObjectAlreadyExists: if a different object with the same uid is already present.
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        # Get existing Object
        object_key = self._get_key_for_object(modelname, uid)

        existing_obj_binary = self._store.get(object_key)
        if existing_obj_binary:
            existing_obj = loads(existing_obj_binary)
            existing_obj_dict = existing_obj.dict()

            if existing_obj_dict != obj.dict():
                raise ObjectAlreadyExists(f"Object {uid} already present", obj)

            # Return so we don't have to change anything on the existing object and underlying data
            return

        # Remove the diffsync object before sending to Redis
        obj_copy = copy.copy(obj)
        obj_copy.diffsync = None

        self._store.set(object_key, dumps(obj_copy))

    def update(self, obj: "DiffSyncModel"):
        """Update a DiffSyncModel object to the store.

        Args:
            obj (DiffSyncModel): Object to update
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        object_key = self._get_key_for_object(modelname, uid)
        obj_copy = copy.copy(obj)
        obj_copy.diffsync = None

        self._store.set(object_key, dumps(obj_copy))

    def remove(self, obj: "DiffSyncModel", remove_children: bool = False):
        """Remove a DiffSyncModel object from the store.

        Args:
            obj (DiffSyncModel): object to remove
            remove_children (bool): If True, also recursively remove any children of this object

        Raises:
            ObjectNotFound: if the object is not present
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        object_key = self._get_key_for_object(modelname, uid)

        if not self._store.exists(object_key):
            raise ObjectNotFound(f"{modelname} {uid} not present in Cache")

        if obj.diffsync:
            obj.diffsync = None

        self._store.delete(object_key)

        if remove_children:
            for child_type, child_fieldname in obj.get_children_mapping().items():
                for child_id in getattr(obj, child_fieldname):
                    try:
                        child_obj = self.get(child_type, child_id)
                        self.remove(child_obj, remove_children=remove_children)
                    except ObjectNotFound:
                        pass
                        # Since this is "cleanup" code, log an error and continue, instead of letting the exception raise
                        # self._log.error(f"Unable to remove child {child_id} of {modelname} {uid} - not found!")

    def count(self, modelname=None):
        """Returns the number of elements of an specific model name."""
        search_pattern = f"{self._store_label}:*"
        if modelname:
            search_pattern = f"{self._store_label}:{modelname.lower()}:*"

        return sum([1 for _ in self._store.scan_iter(search_pattern)])
