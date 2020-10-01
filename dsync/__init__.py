"""
(c) 2020 Network To Code

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import logging
from collections import defaultdict
from typing import List, Mapping

from pydantic import BaseModel

from .diff import Diff, DiffElement
from .utils import intersection
from .exceptions import ObjectCrudException, ObjectAlreadyExists, ObjectStoreWrongType, ObjectNotFound

logger = logging.getLogger(__name__)


class DSyncModel(BaseModel):
    """Base class for all DSync object models.

    Note that APIs of this class are implemented as `get_*()` functions rather than as properties;
    this is intentional as specific model classes may want to use these names (`type`, `keys`, `attrs`, etc.)
    as model attributes and we want to avoid any ambiguity or collisions.

    This class has several dunder-named class variables that subclasses need to set for desired behavior; see below.
    """

    __modelname__: str = None
    """Name of this model, used by DSync to store and look up instances of this model or its equivalents.

    Lowercase by convention; typically corresponds to the class name, but that is not enforced.
    """

    __identifier__: tuple = []
    """List of model fields which together uniquely identify an instance of this model."""

    __shortname__: tuple = []
    """Optional: list of model fields that together form a shorter identifier of an instance, not necessarily unique."""

    __attributes__: tuple = []
    """Optional: list of additional model fields (beyond those in `__identifier__`) that are relevant to this model.

    Only the fields in `__attributes__` (as well as any `__children__` fields, see below) will be considered
    for the purposes of Diff calculation.
    A model may define additional fields (not included in `__attributes__`) for its internal use;
    a common example would be a locally significant database primary key or id value.
    """

    __children__: Mapping[str, str] = {}
    """Optional: dict of `{__modelname__: field_name}` entries describing how to store "child" models in this model.

    When calculating a Diff or performing a sync, DSync will automatically recurse into these child models.
    """

    def __repr__(self):
        return f'{self.get_type()} "{self.get_unique_id()}"'

    def __str__(self):
        return self.get_unique_id()

    @classmethod
    def get_type(cls):
        """Return the type AKA modelname of the object or the class

        Returns:
            str: modelname of the class, used in to store all objects
        """
        return cls.__modelname__

    def get_identifiers(self):
        """Get a dict of all identifiers (primary keys) and their values for this object.

        Returns:
            dict: dictionary containing all primary keys for this device, as defined in __identifier__
        """
        return self.dict(include=set(self.__identifier__))

    def get_attrs(self):
        """Get all the non-primary-key attributes or parameters for this object.

        Similar to Pydantic's `BaseModel.dict()` method, with the following key differences:
        1. Does not include the fields in `__identifier__`
        2. Only includes fields explicitly listed in `__attributes__`
        3. Does not include any additional fields not listed in `__attributes__`

        Returns:
            dict: Dictionary of attributes for this object
        """
        return self.dict(include=set(self.__attributes__))

    def get_unique_id(self):
        """Get the unique ID of an object.

        By default the unique ID is built based on all the primary keys defined in `__identifier__`.

        Returns:
            str: Unique ID for this object
        """
        return "__".join([str(getattr(self, key)) for key in self.__identifier__])

    def get_shortname(self):
        """Get the (not guaranteed-unique) shortname of an object, if any.

        By default the shortname is built based on all the keys defined in `__shortname__`.
        If `__shortname__` is not specified, then this function is equivalent to `get_unique_id()`.

        Returns:
            str: Shortname of this object
        """
        if self.__shortname__:
            return "__".join([str(getattr(self, key)) for key in self.__shortname__])
        else:
            return self.get_unique_id()

    def add_child(self, child):
        """Add a child to an object.

        The child will be automatically saved/indexed by its unique id
        The name of the target attribute is defined in `__children__` per object type

        Args:
            child (DSyncModel): Valid  DSyncModel object

        Raises:
            ObjectStoreWrongType: if the type is not part of `__children__`
            AttributeError: if the model doesn't have a field matching the entry in `__children__`
        """
        child_type = child.get_type()

        if child_type not in self.__children__:
            raise ObjectStoreWrongType(
                f"Unable to store {child_type} as a child; valid types are {sorted(self.__children__.keys())}"
            )

        attr_name = self.__children__[child_type]

        # TODO: this should be checked at class declaration time, not at run time!
        if not hasattr(self, attr_name):
            raise AttributeError(
                f"Invalid attribute name ({attr_name}) for child of type {child_type} for {self.get_type()}"
            )

        childs = getattr(self, attr_name)
        childs.append(child.get_unique_id())


class DSync:
    """Class for storing a group of DSyncModel instances and diffing or synchronizing to another DSync instance."""

    # Add mapping to objects here:
    # modelname1 = MyModelClass1
    # modelname2 = MyModelClass2

    top_level = []
    """List of top-level modelnames to begin from when diffing or synchronizing."""

    def __init__(self):
        """Generic initialization function.

        Subclasses should be careful to call super().__init__() if they override this method.
        """
        self.__datas__ = defaultdict(dict)
        """Defaultdict storing model instances.

        `self.__datas__[modelname][unique_id] == model_instance`
        """

    def load(self):
        """Load all desired data from whatever backend data source into this instance."""
        # No-op in this generic class

    def sync_from(self, source: "DSync"):
        """Synchronize data from the given source DSync object into the current DSync object.

        Args:
            source (DSync): object to sync data from into this one
        """
        diff = self.diff_from(source)

        for child in diff.get_childs():
            self.sync_from_diff_element(child)

    def sync_to(self, target: "DSync"):
        """Synchronize data from the current DSync object into the given target DSync object.

        Args:
            target (DSync): object to sync data into from this one.
        """
        target.sync_from(self)

    def sync_from_diff_element(self, element: DiffElement) -> bool:
        """Synchronize a given object or element defined in a DiffElement into this DSync.

        Args:
            element (DiffElement):

        Returns:
            bool: Return False if there is nothing to sync
        """
        if not element.has_diffs():
            return False

        if element.source_attrs is None:
            self.delete_object(object_type=element.type, keys=element.keys, params=element.dest_attrs)
        elif element.dest_attrs is None:
            self.create_object(object_type=element.type, keys=element.keys, params=element.source_attrs)
        elif element.source_attrs != element.dest_attrs:
            self.update_object(object_type=element.type, keys=element.keys, params=element.source_attrs)

        for child in element.get_childs():
            self.sync_from_diff_element(child)

        return True

    def diff_from(self, source: "DSync") -> Diff:
        """Generate a Diff describing the difference from the other DSync to this one.

        Args:
            source (DSync): Object to diff against.

        Returns:
            Diff
        """
        diff = Diff()

        for obj in intersection(self.top_level, source.top_level):

            diff_elements = self.diff_objects(
                source=list(source.get_all(obj)), dest=list(self.get_all(obj)), source_root=source,
            )

            for element in diff_elements:
                diff.add(obj, element)

        return diff

    def diff_to(self, target: "DSync") -> Diff:
        """Generate a Diff describing the difference from this DSync to another one.

        Args:
            target (DSync): Object to diff against.

        Returns:
            Diff
        """
        return target.diff_from(self)

    def diff_objects(self, source, dest, source_root):
        """Generate a list of DiffElement between the given lists of objects.

        Args:
          source (list): List of source DSyncModel instances
          dest (list): List of target DSyncModel instances
          source_root: TODO

        Returns:
          list(DiffElement)
        """
        if type(source) != type(dest):
            # TODO, should probably be an exception?
            logger.warning(f"Attribute {source} are of different types")
            return False

        diffs = []

        if isinstance(source, list):

            # Convert both list into a Dict and using the str representation as Key
            dict_src = {item.get_unique_id(): item for item in source}
            dict_dst = {item.get_unique_id(): item for item in dest}

            # Identify the shared keys between SRC and DST DSync
            # The keys missing in DST Dsync
            # The keys missing in SRT DSync
            same_keys = intersection(dict_src.keys(), dict_dst.keys())
            missing_dst = list(set(dict_src.keys()) - set(same_keys))
            missing_src = list(set(dict_dst.keys()) - set(same_keys))

            for key in missing_dst:
                de = DiffElement(
                    obj_type=dict_src[key].get_type(),
                    name=dict_src[key].get_shortname(),
                    keys=dict_src[key].get_identifiers(),
                )
                de.add_attrs(source=dict_src[key].get_attrs(), dest=None)
                diffs.append(de)
                # TODO Continue the tree here

            for key in missing_src:
                de = DiffElement(
                    obj_type=dict_dst[key].get_type(),
                    name=dict_dst[key].get_shortname(),
                    keys=dict_dst[key].get_identifiers(),
                )
                de.add_attrs(source=None, dest=dict_dst[key].get_attrs())
                diffs.append(de)
                # TODO Continue the tree here

            for key in same_keys:

                de = DiffElement(
                    obj_type=dict_dst[key].get_type(),
                    name=dict_dst[key].get_shortname(),
                    keys=dict_dst[key].get_identifiers(),
                )

                de.add_attrs(
                    source=dict_src[key].get_attrs(), dest=dict_dst[key].get_attrs(),
                )

                # logger.debug(
                #     f"{dict_src[i].get_type()} {dict_dst[i]} | {i}"
                # )

                # if dict_src[i].get_attrs() != dict_dst[i].get_attrs():
                #     attrs = dict_src[i].get_attrs()
                #     for k, v in attrs.items():
                #         diff.add_item(k, v, getattr(dict_dst[i], k))

                # logger.debug(
                #     f"{dict_src[i].get_type()} {dict_dst[i]} | following the path for {dict_src[i].childs}"
                # )

                for child_type, child_attr in dict_src[key].__children__.items():

                    # TODO: the below is very much not self-documenting - let's add some comments :-)
                    childs = self.diff_objects(
                        source=source_root.get_by_uids(getattr(dict_src[key], child_attr), child_type),
                        dest=self.get_by_uids(getattr(dict_dst[key], child_attr), child_type),
                        source_root=source_root,
                    )

                    for c in childs:
                        de.add_child(c)

                diffs.append(de)

        else:
            # In the future we might support dict, set, tuple, etc...
            # TODO, should probably be an exception?
            logger.warning(f"Type {type(source)} is not supported for now")

        return diffs

    def create_object(self, object_type, keys, params):
        """TODO: move to a `create` method on DSyncModel class."""
        self._crud_change(action="create", keys=keys, object_type=object_type, params=params)

    def update_object(self, object_type, keys, params):
        """TODO: move to a `update` method on DSyncModel class."""
        self._crud_change(
            action="update", object_type=object_type, keys=keys, params=params,
        )

    def delete_object(self, object_type, keys, params):
        """TODO: move to a `delete` method on DSyncModel class."""
        self._crud_change(action="delete", object_type=object_type, keys=keys, params=params)

    def _crud_change(self, action, object_type, keys, params):
        """Dispatcher function to Create, Update or Delete an object.

        Based on the type of the action and the type of the object,
        we'll first try to execute a function named after the object type and the action
            "{action}_{object_type}"   update_interface or delete_device ...
        if such function is not available, the default function will be executed instead
            default_create, default_update or default_delete

        The goal is to all each DSync class to insert its own logic per object type when we manipulate these objects

        TODO: move to DSyncModel class?

        Args:
            action (str): type of action, must be create, update or delete
            object_type (str): Attribute name on this class describing the desired DSyncModel subclass.
            keys (dict): Dictionary containing the primary attributes of an object and their value
            params (dict): Dictionary containing the attributes of an object and their value

        Raises:
            Exception: Object type do not exist in this class

        Returns:
            DSyncModel: object created/updated/deleted
        """

        if not hasattr(self, object_type):
            raise Exception("Unable to find this object type")

        # Check if a specific crud function is available
        #   update_interface or create_device etc ...
        # If not apply the default one

        try:
            if hasattr(self, f"{action}_{object_type}"):
                item = getattr(self, f"{action}_{object_type}")(keys=keys, params=params)
                logger.debug(f"{action}d {object_type} - {params}")
            else:
                item = getattr(self, f"default_{action}")(object_type=object_type, keys=keys, params=params)
                logger.debug(f"{action}d {object_type} = {keys} - {params} (default)")
            return item
        except ObjectCrudException:
            return False

    # ----------------------------------------------------------------------------
    def default_create(self, object_type, keys, params):
        """Default function to create a new object in the local storage.

        This function will be called if a more specific function of type create_<object_type> is not defined

        Args:
            object_type (str): Attribute name on this class identifying the DSyncModel subclass of the object
            keys (dict): Dictionary containing the primary attributes of an object and their value
            params (dict): Dictionary containing the attributes of an object and their value

        Returns:
            DSyncModel: Return the newly created object
        """
        obj = getattr(self, object_type)
        item = obj(**keys, **params)
        self.add(item)
        return item

    def default_update(self, object_type, keys, params):
        """Update an object locally based on its primary keys and attributes.

        This function will be called if a more specific function of type update_<object_type> is not defined

        Args:
            object_type (str): Attribute name on this class identifying the DSyncModel subclass of the object
            keys (dict): Dictionary containing the primary attributes of an object and their value
            params (dict): Dictionary containing the attributes of an object and their value

        Returns:
            DSyncModel: Return the object after update
        """
        obj = getattr(self, object_type)

        # TODO: uid = "__".join(keys.values()) to avoid instantiating the model unnecessarily?
        uid = obj(**keys).get_unique_id()
        item = self.get(obj=obj, keys=[uid])

        for attr, value in params.items():
            setattr(item, attr, value)

        return item

    def default_delete(self, object_type, keys, params):
        """Delete an object locally based on its primary keys and attributes.

        This function will be called if a more specific function of type delete_<object_type> is not defined

        Args:
            object_type (str): Attribute name on this class identifying the DSyncModel subclass of the object
            keys (dict): Dictionnary containings the primary attributes of an object and their value
            params (dict): Dictionnary containings the attributes of an object and their value

        Returns:
            DSyncModel: Return the object that has been deleted
        """
        obj = getattr(self, object_type)
        # TODO: uid = "__".join(keys.values()) to avoid instantiating the model unnecessarily?
        item = obj(**keys, **params)
        self.remove(item)
        return item

    # ------------------------------------------------------------------------------
    # Object Storage Management
    # ------------------------------------------------------------------------------

    def get(self, obj, keys):
        """Get one object from the data store based on its unique id or a list of its unique attributes.

        Args:
            obj (DSyncModel, str): DSyncModel class or object or string that define the type of the objects to retrieve
            keys (list[str]): List of attributes.

        Returns:
            DSyncModel, None
        """
        if isinstance(obj, str):
            modelname = obj
        else:
            modelname = obj.get_type()

        # TODO: default_update() calls get(obj, [uid]) making the below rather redundant...
        uid = "__".join(keys)

        if uid in self.__datas__[modelname]:
            return self.__datas__[modelname][uid]

        return None

    def get_all(self, obj):
        """Get all objects of a given type.

        Args:
            obj (DSyncModel, str): DSyncModel class or object or string that define the type of the objects to retrieve

        Returns:
            ValuesList[DSyncModel]: List of Object
        """
        if isinstance(obj, str):
            modelname = obj
        else:
            modelname = obj.get_type()

        return self.__datas__[modelname].values()

    def get_by_uids(self, uids: List[str], obj):
        """Get multiple objects from the store by their unique IDs/Keys and type.

        Args:
            uids (list[str]): List of unique id / key identifying object in the database.
            obj (DSyncModel, str): DSyncModel class or object or string that define the type of the objects to retrieve

        Returns:
            list[DSyncModel]: List of DSyncModel objects
        """
        if isinstance(obj, str):
            modelname = obj
        else:
            modelname = obj.get_type()

        # TODO: this returns the results ordered by their storage order in self.__datas__[modelname],
        #       and NOT by the order given in uids. Seems like a bug?
        #
        # TODO: should this raise an exception if any or all of the uids are not found?
        return [value for uid, value in self.__datas__[modelname].items() if uid in uids]

    def add(self, obj: DSyncModel):
        """Add a DSyncModel object to the store.

        Args:
            obj (DSyncModel): Object to store

        Raises:
            ObjectAlreadyExists: if an object with the same uid is already present
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        if uid in self.__datas__[modelname]:
            raise ObjectAlreadyExists(f"Object {uid} already present")

        self.__datas__[modelname][uid] = obj

    def remove(self, obj: DSyncModel):
        """Remove a DSyncModel object from the store.

        Args:
            obj (DSyncModel): object to delete

        Raises:
            ObjectNotFound: if the object is not present
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        if uid not in self.__datas__[modelname]:
            raise ObjectNotFound(f"Object {uid} not present")

        del self.__datas__[modelname][uid]
