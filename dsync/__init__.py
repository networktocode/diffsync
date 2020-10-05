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
from inspect import isclass
import logging
from collections import defaultdict
from collections.abc import Iterable as ABCIterable, Mapping as ABCMapping
from typing import List, Mapping, Iterable

from pydantic import BaseModel

from .diff import Diff, DiffElement
from .utils import intersection
from .exceptions import (
    ObjectNotCreated,
    ObjectNotUpdated,
    ObjectNotDeleted,
    ObjectCrudException,
    ObjectAlreadyExists,
    ObjectStoreWrongType,
    ObjectNotFound,
)

logger = logging.getLogger(__name__)


class DSyncModel(BaseModel):
    """Base class for all DSync object models.

    Note that APIs of this class are implemented as `get_*()` functions rather than as properties;
    this is intentional as specific model classes may want to use these names (`type`, `keys`, `attrs`, etc.)
    as model attributes and we want to avoid any ambiguity or collisions.

    This class has several underscore-prefixed class variables that subclasses should set as desired; see below.

    NOTE: The groupings _identifiers, _attributes, and _children are mutually exclusive; any given field name can
          be included in **at most** one of these three tuples.
    """

    _modelname: str = "dsyncmodel"
    """Name of this model, used by DSync to store and look up instances of this model or its equivalents.

    Lowercase by convention; typically corresponds to the class name, but that is not enforced.
    """

    _identifiers: tuple = ()
    """List of model fields which together uniquely identify an instance of this model."""

    _shortname: tuple = ()
    """Optional: list of model fields that together form a shorter identifier of an instance, not necessarily unique."""

    _attributes: tuple = ()
    """Optional: list of additional model fields (beyond those in `_identifiers`) that are relevant to this model.

    Only the fields in `_attributes` (as well as any `_children` fields, see below) will be considered
    for the purposes of Diff calculation.
    A model may define additional fields (not included in `_attributes`) for its internal use;
    a common example would be a locally significant database primary key or id value.

    Note: inclusion in `_attributes` is mutually exclusive from inclusion in `_identifiers`; a field cannot be in both!
    """

    _children: Mapping[str, str] = {}
    """Optional: dict of `{_modelname: field_name}` entries describing how to store "child" models in this model.

    When calculating a Diff or performing a sync, DSync will automatically recurse into these child models.
    """

    def __init_subclass__(cls):
        """Validate that the various class attribute declarations correspond to actual instance fields.

        Called automatically on subclass declaration.
        """
        variables = cls.__fields__.keys()
        # Make sure that any field referenced by name actually exists on the model
        for attr in cls._identifiers:
            if attr not in variables and not hasattr(cls, attr):
                raise AttributeError(f"_identifiers {cls._identifiers} references missing or un-annotated attr {attr}")
        for attr in cls._shortname:
            if attr not in variables:
                raise AttributeError(f"_shortname {cls._shortname} references missing or un-annotated attr {attr}")
        for attr in cls._attributes:
            if attr not in variables:
                raise AttributeError(f"_attributes {cls._attributes} references missing or un-annotated attr {attr}")
        for attr in cls._children.values():
            if attr not in variables:
                raise AttributeError(f"_children {cls._children} references missing or un-annotated attr {attr}")

        # Any given field can only be in one of (_identifiers, _attributes, _children)
        id_attr_overlap = set(cls._identifiers).intersection(cls._attributes)
        if id_attr_overlap:
            raise AttributeError(f"Fields {id_attr_overlap} are included in both _identifiers and _attributes.")
        id_child_overlap = set(cls._identifiers).intersection(cls._children.values())
        if id_child_overlap:
            raise AttributeError(f"Fields {id_child_overlap} are included in both _identifiers and _children.")
        attr_child_overlap = set(cls._attributes).intersection(cls._children.values())
        if attr_child_overlap:
            raise AttributeError(f"Fields {attr_child_overlap} are included in both _attributes and _children.")

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
        return cls._modelname

    @classmethod
    def create_unique_id(cls, **identifiers) -> str:
        """Construct a unique identifier for this model class.

        Args:
            **identifiers: Dict of identifiers and their values, as in `get_identifiers()`.
        """
        return "__".join(str(identifiers[key]) for key in cls._identifiers)

    def get_identifiers(self):
        """Get a dict of all identifiers (primary keys) and their values for this object.

        Returns:
            dict: dictionary containing all primary keys for this device, as defined in _identifiers
        """
        return self.dict(include=set(self._identifiers))

    def get_attrs(self):
        """Get all the non-primary-key attributes or parameters for this object.

        Similar to Pydantic's `BaseModel.dict()` method, with the following key differences:
        1. Does not include the fields in `_identifiers`
        2. Only includes fields explicitly listed in `_attributes`
        3. Does not include any additional fields not listed in `_attributes`

        Returns:
            dict: Dictionary of attributes for this object
        """
        return self.dict(include=set(self._attributes))

    def get_unique_id(self):
        """Get the unique ID of an object.

        By default the unique ID is built based on all the primary keys defined in `_identifiers`.

        Returns:
            str: Unique ID for this object
        """
        return self.create_unique_id(**self.get_identifiers())

    def get_shortname(self):
        """Get the (not guaranteed-unique) shortname of an object, if any.

        By default the shortname is built based on all the keys defined in `_shortname`.
        If `_shortname` is not specified, then this function is equivalent to `get_unique_id()`.

        Returns:
            str: Shortname of this object
        """
        if self._shortname:
            return "__".join([str(getattr(self, key)) for key in self._shortname])
        return self.get_unique_id()

    def add_child(self, child):
        """Add a child to an object.

        The child will be automatically saved/indexed by its unique id
        The name of the target attribute is defined in `_children` per object type

        Args:
            child (DSyncModel): Valid  DSyncModel object

        Raises:
            ObjectStoreWrongType: if the type is not part of `_children`
            AttributeError: if the model doesn't have a field matching the entry in `_children`
        """
        child_type = child.get_type()

        if child_type not in self._children:
            raise ObjectStoreWrongType(
                f"Unable to store {child_type} as a child; valid types are {sorted(self._children.keys())}"
            )

        attr_name = self._children[child_type]
        childs = getattr(self, attr_name)
        childs.append(child.get_unique_id())


class DSync:
    """Class for storing a group of DSyncModel instances and diffing or synchronizing to another DSync instance."""

    # Add mapping to objects here:
    # modelname1 = MyModelClass1
    # modelname2 = MyModelClass2

    top_level: List[str] = []
    """List of top-level modelnames to begin from when diffing or synchronizing."""

    def __init__(self):
        """Generic initialization function.

        Subclasses should be careful to call super().__init__() if they override this method.
        """
        self._data = defaultdict(dict)
        """Defaultdict storing model instances.

        `self._data[modelname][unique_id] == model_instance`
        """

    def __init_subclass__(cls):
        """Validate that references to specific DSyncModels use the correct modelnames.

        Called automatically on subclass declaration.
        """
        contents = cls.__dict__
        for name, value in contents.items():
            if isclass(value) and issubclass(value, DSyncModel) and value.get_type() != name:
                raise AttributeError(
                    f'Incorrect field name - {value.__name__} has type name "{value.get_type()}", not "{name}"'
                )

    def load(self):
        """Load all desired data from whatever backend data source into this instance."""
        # No-op in this generic class

    def sync_from(self, source: "DSync"):
        """Synchronize data from the given source DSync object into the current DSync object.

        Args:
            source (DSync): object to sync data from into this one
        """
        diff = self.diff_from(source)

        for child in diff.get_children():
            self._sync_from_diff_element(child)

    def sync_to(self, target: "DSync"):
        """Synchronize data from the current DSync object into the given target DSync object.

        Args:
            target (DSync): object to sync data into from this one.
        """
        target.sync_from(self)

    def _sync_from_diff_element(self, element: DiffElement) -> bool:
        """Synchronize a given DiffElement (and its children, if any) into this DSync.

        Helper method for `sync_from`/`sync_to`; this generally shouldn't be called on its own.

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

        for child in element.get_children():
            self._sync_from_diff_element(child)

        return True

    def diff_from(self, source: "DSync") -> Diff:
        """Generate a Diff describing the difference from the other DSync to this one.

        Args:
            source (DSync): Object to diff against.
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
        """
        return target.diff_from(self)

    def diff_objects(
        self, source: Iterable[DSyncModel], dest: Iterable[DSyncModel], source_root: "DSync"
    ) -> List[DiffElement]:
        """Generate a list of DiffElement between the given lists of objects.

        Args:
          source: List (other types may be supported in future) of source DSyncModel instances
          dest: List (other types may be supported in future) of target DSyncModel instances
          source_root (DSync): TODO

        Raises:
          TypeError: if the source and dest args are not the same type, or if that type is unsupported
        """
        diffs = []

        if isinstance(source, ABCIterable) and isinstance(dest, ABCIterable):
            # Convert list into a Dict and using the str representation as Key
            dict_src = {item.get_unique_id(): item for item in source} if not isinstance(source, ABCMapping) else source
            dict_dst = {item.get_unique_id(): item for item in dest} if not isinstance(dest, ABCMapping) else dest

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
                #     f"{dict_src[i].get_type()} {dict_dst[i]} | following the path for {dict_src[i].children}"
                # )

                for child_type, child_attr in dict_src[key]._children.items():

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
            # In the future we might support set, etc...
            raise TypeError(f"Type {type(source)} is not supported... for now")

        return diffs

    def create_object(self, object_type, keys, params):
        """TODO: move to a `create` method on DSyncModel class."""
        self._crud_change(action="create", keys=keys, object_type=object_type, params=params)

    def update_object(self, object_type, keys, params):
        """TODO: move to a `update` method on DSyncModel class."""
        self._crud_change(
            action="update", object_type=object_type, keys=keys, params=params,
        )

    def delete_object(self, object_type, keys, params=None):
        """TODO: move to a `delete` method on DSyncModel class."""
        if not params:
            params = {}
        self._crud_change(action="delete", object_type=object_type, keys=keys, params=params)

    def _crud_change(self, action: str, object_type: str, keys: dict, params: dict) -> DSyncModel:
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
            ObjectCrudException: Object type does not exist in this class

        Returns:
            DSyncModel: object created/updated/deleted
        """

        if not hasattr(self, object_type):
            if action == "create":
                raise ObjectNotCreated(f"Unable to find object type {object_type}")
            if action == "update":
                raise ObjectNotUpdated(f"Unable to find object type {object_type}")
            if action == "delete":
                raise ObjectNotDeleted(f"Unable to find object type {object_type}")
            raise ObjectCrudException(f"Unable to find object type {object_type}")

        # Check if a specific crud function is available
        #   update_interface or create_device etc ...
        # If not apply the default one

        if hasattr(self, f"{action}_{object_type}"):
            item = getattr(self, f"{action}_{object_type}")(keys=keys, params=params)
            logger.debug("%sd %s - %s", action, object_type, params)
        else:
            item = getattr(self, f"default_{action}")(object_type=object_type, keys=keys, params=params)
            logger.debug("%sd %s = %s - %s (default)", action, object_type, keys, params)
        return item

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
        object_class = getattr(self, object_type)
        item = object_class(**keys, **params)
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
        object_class = getattr(self, object_type)
        uid = object_class.create_unique_id(**keys)
        item = self.get(obj=object_class, keys=[uid])

        for attr, value in params.items():
            setattr(item, attr, value)

        return item

    def default_delete(self, object_type, keys, params):
        """Delete an object locally based on its primary keys and attributes.

        This function will be called if a more specific function of type delete_<object_type> is not defined

        Args:
            object_type (str): Attribute name on this class identifying the DSyncModel subclass of the object
            keys (dict): Dictionnary containings the primary attributes of an object and their value
            params: Unused argument included only for parallels to the other APIs.

        Returns:
            DSyncModel: Return the object that has been deleted
        """
        object_class = getattr(self, object_type)
        uid = object_class.create_unique_id(**keys)
        item = self.get(obj=object_class, keys=[uid])
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

        if uid in self._data[modelname]:
            return self._data[modelname][uid]

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

        return self._data[modelname].values()

    def get_by_uids(self, uids: List[str], obj) -> List[DSyncModel]:
        """Get multiple objects from the store by their unique IDs/Keys and type.

        Args:
            uids (list[str]): List of unique id / key identifying object in the database.
            obj (DSyncModel, str): DSyncModel class or object or string that define the type of the objects to retrieve
        """
        if isinstance(obj, str):
            modelname = obj
        else:
            modelname = obj.get_type()

        # TODO: this returns the results ordered by their storage order in self._data[modelname],
        #       and NOT by the order given in uids. Seems like a bug?
        #
        # TODO: should this raise an exception if any or all of the uids are not found?
        return [value for uid, value in self._data[modelname].items() if uid in uids]

    def add(self, obj: DSyncModel):
        """Add a DSyncModel object to the store.

        Args:
            obj (DSyncModel): Object to store

        Raises:
            ObjectAlreadyExists: if an object with the same uid is already present
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        if uid in self._data[modelname]:
            raise ObjectAlreadyExists(f"Object {uid} already present")

        self._data[modelname][uid] = obj

    def remove(self, obj: DSyncModel):
        """Remove a DSyncModel object from the store.

        Args:
            obj (DSyncModel): object to delete

        Raises:
            ObjectNotFound: if the object is not present
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        if uid not in self._data[modelname]:
            raise ObjectNotFound(f"Object {uid} not present")

        del self._data[modelname][uid]
