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
from typing import ClassVar, Iterable, List, Mapping, Optional, Tuple, Type, Union

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

    _modelname: ClassVar[str] = "dsyncmodel"
    """Name of this model, used by DSync to store and look up instances of this model or its equivalents.

    Lowercase by convention; typically corresponds to the class name, but that is not enforced.
    """

    _identifiers: ClassVar[Tuple[str, ...]] = ()
    """List of model fields which together uniquely identify an instance of this model.

    This identifier MUST be globally unique among all instances of this class.
    """

    _shortname: ClassVar[Tuple[str, ...]] = ()
    """Optional: list of model fields that together form a shorter identifier of an instance.

    This MUST be locally unique (e.g., interface shortnames MUST be unique among all interfaces on a given device),
    but does not need to be guaranteed to be globally unique among all instances.
    """

    _attributes: ClassVar[Tuple[str, ...]] = ()
    """Optional: list of additional model fields (beyond those in `_identifiers`) that are relevant to this model.

    Only the fields in `_attributes` (as well as any `_children` fields, see below) will be considered
    for the purposes of Diff calculation.
    A model may define additional fields (not included in `_attributes`) for its internal use;
    a common example would be a locally significant database primary key or id value.

    Note: inclusion in `_attributes` is mutually exclusive from inclusion in `_identifiers`; a field cannot be in both!
    """

    _children: ClassVar[Mapping[str, str]] = {}
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
    def create(cls, dsync: "DSync", ids: dict, attrs: dict) -> Optional["DSyncModel"]:
        """Instantiate this class, along with any platform-specific data creation.

        Args:
            dsync: The master data store for other DSyncModel instances that we might need to reference
            ids: Dictionary of unique-identifiers needed to create the new object
            attrs: Dictionary of additional attributes to set on the new object

        Returns:
            DSyncModel: instance of this class, if all data was successfully created.
            None: if data creation failed in such a way that child objects of this model should not be created.

        Raises:
            ObjectNotCreated: if an error occurred.
        """
        # Generic implementation has no platform-specific data to create and therefore doesn't use the dsync object
        # pylint: disable=unused-argument
        return cls(**ids, **attrs)

    def update(self, dsync: "DSync", attrs: dict) -> Optional["DSyncModel"]:
        """Update the attributes of this instance, along with any platform-specific data updates.

        Args:
            dsync: The master data store for other DSyncModel instances that we might need to reference
            attrs: Dictionary of attributes to update on the object

        Returns:
            DSyncModel: this instance, if all data was successfully updated.
            None: if data updates failed in such a way that child objects of this model should not be modified.

        Raises:
            ObjectNotUpdated: if an error occurred.
        """
        # Generic implementation has no platform-specific data to update and therefore doesn't use the dsync object
        # pylint: disable=unused-argument
        for attr, value in attrs.items():
            # TODO: enforce that only attrs in self._attributes can be updated in this way?
            setattr(self, attr, value)
        return self

    def delete(self, dsync: "DSync") -> Optional["DSyncModel"]:
        """Delete any platform-specific data corresponding to this instance.

        Args:
            dsync: The master data store for other DSyncModel instances that we might need to reference

        Returns:
            DSyncModel: this instance, if all data was successfully deleted.
            None: if data deletion failed in such a way that child objects of this model should not be deleted.

        Raises:
            ObjectNotDeleted: if an error occurred.
        """
        # Generic implementation has no platform-specific data to delete and therefore doesn't use the dsync object
        # pylint: disable=unused-argument
        return self

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

    @classmethod
    def get_children_mapping(cls) -> Mapping[str, str]:
        """Get the mapping of types to fieldnames for child models of this model."""
        return cls._children

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

    def add_child(self, child: "DSyncModel"):
        """Add a child reference to an object.

        The child object isn't stored, only its unique id.
        The name of the target attribute is defined in `_children` per object type

        Raises:
            ObjectStoreWrongType: if the type is not part of `_children`
            ObjectAlreadyExists: if the unique id is already stored
        """
        child_type = child.get_type()

        if child_type not in self._children:
            raise ObjectStoreWrongType(
                f"Unable to store {child_type} as a child; valid types are {sorted(self._children.keys())}"
            )

        attr_name = self._children[child_type]
        childs = getattr(self, attr_name)
        if child.get_unique_id() in childs:
            raise ObjectAlreadyExists(f"Already storing a {child_type} with unique_id {child.get_unique_id()}")
        childs.append(child.get_unique_id())

    def remove_child(self, child: "DSyncModel"):
        """Remove a child reference from an object.

        The name of the storage attribute is defined in `_children` per object type.

        Raises:
            ObjectStoreWrongType: if the child model type is not part of `_children`
            ObjectNotFound: if the child wasn't previously present.
        """
        child_type = child.get_type()

        if child_type not in self._children:
            raise ObjectStoreWrongType(
                f"Unable to store {child_type} as a child; valid types are {sorted(self._children.keys())}"
            )

        attr_name = self._children[child_type]
        childs = getattr(self, attr_name)
        if child.get_unique_id() not in childs:
            raise ObjectNotFound(f"{child} was not found as a child in {attr_name}")
        childs.remove(child.get_unique_id())


class DSync:
    """Class for storing a group of DSyncModel instances and diffing or synchronizing to another DSync instance."""

    # Add mapping of names to specific model classes here:
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

    # ------------------------------------------------------------------------------
    # Synchronization between DSync instances
    # ------------------------------------------------------------------------------

    def sync_from(self, source: "DSync", diff_class: Type[Diff] = Diff, continue_on_failure: bool = False):
        """Synchronize data from the given source DSync object into the current DSync object.

        Args:
            source (DSync): object to sync data from into this one
            diff_class (class): Diff or subclass thereof to use to calculate the diffs to use for synchronization
            continue_on_failure (bool): Whether to continue synchronizing even if failures or errors are encountered.
        """
        diff = self.diff_from(source, diff_class=diff_class)

        logger.info("Beginning sync")
        for child in diff.get_children():
            self._sync_from_diff_element(child, continue_on_failure=continue_on_failure)
        logger.info("Sync complete")

    def sync_to(self, target: "DSync", diff_class: Type[Diff] = Diff):
        """Synchronize data from the current DSync object into the given target DSync object.

        Args:
            target (DSync): object to sync data into from this one.
            diff_class (class): Diff or subclass thereof to use to calculate the diffs to use for synchronization
        """
        target.sync_from(self, diff_class=diff_class)

    def _sync_from_diff_element(
        self, element: DiffElement, continue_on_failure: bool = False, parent_model: DSyncModel = None
    ):
        """Synchronize a given DiffElement (and its children, if any) into this DSync.

        Helper method for `sync_from`/`sync_to`; this generally shouldn't be called on its own.

        Args:
            element: DiffElement to synchronize diffs from
            continue_on_failure: Whether to continue synchronizing even if failures or errors are encountered.
            parent_model: Parent object to update (`add_child`/`remove_child`) if the sync creates/deletes an object.
        """
        # pylint: disable=too-many-branches
        # GFM: I made a few attempts at refactoring this to reduce the branching, but found that it was less readable.
        # So let's live with the slightly too high number of branches (14/12) for now.
        object_class = getattr(self, element.type)
        obj = self.get(object_class, element.keys)
        attrs = (
            {attr_key: element.source_attrs[attr_key] for attr_key in element.get_attrs_keys()}
            if element.source_attrs is not None
            else {}
        )

        try:
            if element.action == "create":
                if obj:
                    raise ObjectNotCreated(f"Failed to create {object_class.get_type()} {element.keys} - it exists!")
                logger.info("Creating %s %s (%s)", object_class.get_type(), element.keys, attrs)
                obj = object_class.create(dsync=self, ids=element.keys, attrs=attrs)
            elif element.action == "update":
                if not obj:
                    raise ObjectNotUpdated(f"Failed to update {object_class.get_type()} {element.keys} - not found!")
                logger.info("Updating %s %s with %s", object_class.get_type(), element.keys, attrs)
                obj = obj.update(dsync=self, attrs=attrs)
            elif element.action == "delete":
                if not obj:
                    raise ObjectNotDeleted(f"Failed to delete {object_class.get_type()} {element.keys} - not found!")
                logger.info("Deleting %s %s", object_class.get_type(), element.keys)
                obj = obj.delete(dsync=self)
        except ObjectCrudException as exception:
            logger.error(
                "Error during %s of %s %s (%s): %s",
                element.action,
                object_class.get_type(),
                element.keys,
                attrs,
                exception,
            )
            if not continue_on_failure:
                raise

        if obj is None:
            logger.warning("Not syncing children of %s %s", element.type, element.keys)
            return

        if element.action == "create":
            self.add(obj)
            if parent_model:
                parent_model.add_child(obj)
        elif element.action == "delete":
            self.remove(obj)
            if parent_model:
                parent_model.remove_child(obj)

        for child in element.get_children():
            self._sync_from_diff_element(child, continue_on_failure=continue_on_failure, parent_model=obj)

    # ------------------------------------------------------------------------------
    # Diff calculation and construction
    # ------------------------------------------------------------------------------

    def diff_from(self, source: "DSync", diff_class: Type[Diff] = Diff) -> Diff:
        """Generate a Diff describing the difference from the other DSync to this one.

        Args:
            source (DSync): Object to diff against.
            diff_class (class): Diff or subclass thereof to use for diff calculation and storage.
        """
        logger.info("Beginning diff")
        diff = diff_class()

        for obj_type in intersection(self.top_level, source.top_level):

            diff_elements = self._diff_objects(
                source=source.get_all(obj_type), dest=self.get_all(obj_type), source_root=source,
            )

            for diff_element in diff_elements:
                diff.add(diff_element)

        # Notify the diff that it has been fully populated, in case it wishes to print, save to a file, etc.
        logger.info("Diff complete")
        diff.complete()
        return diff

    def diff_to(self, target: "DSync", diff_class: Type[Diff] = Diff) -> Diff:
        """Generate a Diff describing the difference from this DSync to another one.

        Args:
            target (DSync): Object to diff against.
            diff_class (class): Diff or subclass thereof to use for diff calculation and storage.
        """
        return target.diff_from(self, diff_class=diff_class)

    def _diff_objects(
        self, source: Iterable[DSyncModel], dest: Iterable[DSyncModel], source_root: "DSync"
    ) -> List[DiffElement]:
        """Generate a list of DiffElement between the given lists of objects.

        Helper method for `diff_from`/`diff_to`; this generally shouldn't be called on its own.

        Args:
          source: DSyncModel instances retrieved from another DSync instance
          dest: DSyncModel instances retrieved from this DSync instance
          source_root (DSync): The other DSync object being diffed against (owner of the `source` models).

        Raises:
          TypeError: if the source and dest args are not the same type, or if that type is unsupported
        """
        diffs = []

        if isinstance(source, ABCIterable) and isinstance(dest, ABCIterable):
            # Convert a list of DSyncModels into a dict using the unique_ids as keys
            dict_src = {item.get_unique_id(): item for item in source} if not isinstance(source, ABCMapping) else source
            dict_dst = {item.get_unique_id(): item for item in dest} if not isinstance(dest, ABCMapping) else dest

            combined_dict = {}
            for uid in dict_src:
                combined_dict[uid] = (dict_src.get(uid), dict_dst.get(uid))
            for uid in dict_dst:
                combined_dict[uid] = (dict_src.get(uid), dict_dst.get(uid))
        else:
            # In the future we might support set, etc...
            raise TypeError(f"Type combination {type(source)}/{type(dest)} is not supported... for now")

        self._validate_objects_for_diff(combined_dict)

        for uid in combined_dict:
            src_obj, dst_obj = combined_dict[uid]

            if src_obj:
                diff_element = DiffElement(
                    obj_type=src_obj.get_type(), name=src_obj.get_shortname(), keys=src_obj.get_identifiers()
                )
            elif dst_obj:
                diff_element = DiffElement(
                    obj_type=dst_obj.get_type(), name=dst_obj.get_shortname(), keys=dst_obj.get_identifiers()
                )
            else:
                # Should be unreachable
                raise RuntimeError(f"UID {uid} is in combined_dict but has neither src_obj nor dst_obj??")

            if src_obj:
                diff_element.add_attrs(source=src_obj.get_attrs(), dest=None)
            if dst_obj:
                diff_element.add_attrs(source=None, dest=dst_obj.get_attrs())

            # Recursively diff the children of src_obj and dst_obj and attach the resulting diffs to the diff_element
            self._diff_child_objects(diff_element, src_obj, dst_obj, source_root)

            diffs.append(diff_element)

        return diffs

    @staticmethod
    def _validate_objects_for_diff(combined_dict: Mapping[str, Tuple[Optional[DSyncModel], Optional[DSyncModel]]]):
        """Check whether all DSyncModels in the given dictionary are valid for comparison to one another.

        Helper method for `_diff_objects`.

        Raises:
            TypeError: If any pair of objects in the dict have differing get_type() values.
            ValueError: If any pair of objects in the dict have differing get_shortname() or get_identifiers() values.
        """
        for uid in combined_dict:
            # TODO: should we check/enforce whether ALL DSyncModels in this dict have the same get_type() output?
            src_obj, dst_obj = combined_dict[uid]
            if src_obj and dst_obj:
                if src_obj.get_type() != dst_obj.get_type():
                    raise TypeError(f"Type mismatch: {src_obj.get_type()} vs {dst_obj.get_type()}")
                if src_obj.get_shortname() != dst_obj.get_shortname():
                    raise ValueError(f"Shortname mismatch: {src_obj.get_shortname()} vs {dst_obj.get_shortname()}")
                if src_obj.get_identifiers() != dst_obj.get_identifiers():
                    raise ValueError(f"Keys mismatch: {src_obj.get_identifiers()} vs {dst_obj.get_identifiers()}")

    def _diff_child_objects(
        self,
        diff_element: DiffElement,
        src_obj: Optional[DSyncModel],
        dst_obj: Optional[DSyncModel],
        source_root: "DSync",
    ):
        """For all children of the given DSyncModel pair, diff them recursively, adding diffs to the given diff_element.

        Helper method for `_diff_objects`.
        """
        children_mapping: Mapping[str, str]
        if src_obj and dst_obj:
            # Get the subset of child types common to both src_obj and dst_obj
            src_mapping = src_obj.get_children_mapping()
            dst_mapping = dst_obj.get_children_mapping()
            children_mapping = {}
            for child_type, child_fieldname in src_mapping.items():
                if child_type in dst_mapping:
                    children_mapping[child_type] = child_fieldname
        elif src_obj:
            children_mapping = src_obj.get_children_mapping()
        elif dst_obj:
            children_mapping = dst_obj.get_children_mapping()
        else:
            # Should be unreachable
            raise RuntimeError("Called with neither src_obj nor dest_obj??")

        for child_type, child_fieldname in children_mapping.items():
            src_uids: List[str] = getattr(src_obj, child_fieldname) if src_obj else []
            dst_uids: List[str] = getattr(dst_obj, child_fieldname) if dst_obj else []
            for child_diff_element in self._diff_objects(
                source=source_root.get_by_uids(src_uids, child_type),
                dest=self.get_by_uids(dst_uids, child_type),
                source_root=source_root,
            ):
                diff_element.add_child(child_diff_element)

    # ------------------------------------------------------------------------------
    # Object Storage Management
    # ------------------------------------------------------------------------------

    def get(self, obj: Union[str, DSyncModel, Type[DSyncModel]], identifier: Union[str, dict]) -> Optional[DSyncModel]:
        """Get one object from the data store based on its unique id.

        Args:
            obj (class, DSyncModel, str): DSyncModel class or DSyncModel instance or modelname string
            identifier (str, dict): Unique ID of the object to retrieve, or dict of unique identifier keys/values
        """
        if isinstance(obj, str):
            modelname = obj
            if not hasattr(self, obj):
                return None
            object_class = getattr(self, obj)
        else:
            object_class = obj
            modelname = obj.get_type()

        if isinstance(identifier, str):
            uid = identifier
        else:
            uid = object_class.create_unique_id(**identifier)

        return self._data[modelname].get(uid)

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

        # TODO: should this raise an exception if any or all of the uids are not found?
        results = []
        for uid in uids:
            if uid in self._data[modelname]:
                results.append(self._data[modelname][uid])
        return results

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
