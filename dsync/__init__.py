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
from collections import defaultdict
from collections.abc import Iterable as ABCIterable, Mapping as ABCMapping
import enum
from inspect import isclass
from typing import ClassVar, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Type, Union

from pydantic import BaseModel
import structlog  # type: ignore

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


class DSyncFlags(enum.Flag):
    """Flags that can be passed to a sync_* or diff_* call to affect its behavior."""

    NONE = 0

    CONTINUE_ON_FAILURE = enum.auto()
    """Continue synchronizing even if failures are encountered when syncing individual models."""

    SKIP_UNMATCHED_SRC = enum.auto()
    """Ignore objects that only exist in the source/"from" DSync when determining diffs and syncing.

    If this flag is set, no new objects will be created in the target/"to" DSync.
    """

    SKIP_UNMATCHED_DST = enum.auto()
    """Ignore objects that only exist in the target/"to" DSync when determining diffs and syncing.

    If this flag is set, no objects will be deleted from the target/"to" DSync.
    """

    SKIP_UNMATCHED_BOTH = SKIP_UNMATCHED_SRC | SKIP_UNMATCHED_DST

    LOG_UNCHANGED_RECORDS = enum.auto()
    """If this flag is set, a log message will be generated during synchronization for each model, even unchanged ones.

    By default, when this flag is unset, only models that have actual changes to synchronize will be logged.
    This flag is off by default to reduce the default verbosity of DSync, but can be enabled when debugging.
    """


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

    dsync: Optional["DSync"] = None
    """Optional: the DSync instance that owns this model instance."""

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic class configuration."""

        # Let us have a DSync as an instance variable even though DSync is not a Pydantic model itself.
        arbitrary_types_allowed = True

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
        return cls(**ids, dsync=dsync, **attrs)

    def update(self, attrs: dict) -> Optional["DSyncModel"]:
        """Update the attributes of this instance, along with any platform-specific data updates.

        Args:
            attrs: Dictionary of attributes to update on the object

        Returns:
            DSyncModel: this instance, if all data was successfully updated.
            None: if data updates failed in such a way that child objects of this model should not be modified.

        Raises:
            ObjectNotUpdated: if an error occurred.
        """
        for attr, value in attrs.items():
            # TODO: enforce that only attrs in self._attributes can be updated in this way?
            setattr(self, attr, value)
        return self

    def delete(self) -> Optional["DSyncModel"]:
        """Delete any platform-specific data corresponding to this instance.

        Returns:
            DSyncModel: this instance, if all data was successfully deleted.
            None: if data deletion failed in such a way that child objects of this model should not be deleted.

        Raises:
            ObjectNotDeleted: if an error occurred.
        """
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

    type: ClassVar[Optional[str]] = None
    """Type of the object, will default to the name of the class if not provided."""

    top_level: ClassVar[List[str]] = []
    """List of top-level modelnames to begin from when diffing or synchronizing."""

    _data: MutableMapping[str, MutableMapping[str, DSyncModel]]
    """Defaultdict storing model instances.

    `self._data[modelname][unique_id] == model_instance`
    """

    def __init__(self, name=None):
        """Generic initialization function.

        Subclasses should be careful to call super().__init__() if they override this method.
        """
        self._data = defaultdict(dict)
        self._log = structlog.get_logger().new(dsync=self)

        # If the type is not defined, use the name of the class as the default value
        if self.type is None:
            self.type = self.__class__.__name__

        # If the name has not been provided, use the type as the name
        self.name = name if name else self.type

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

    def __str__(self):
        """String representation of a DSync."""
        if self.type != self.name:
            return f'{self.type} "{self.name}"'
        return self.type

    def __repr__(self):
        return f"<{str(self)}>"

    def load(self):
        """Load all desired data from whatever backend data source into this instance."""
        # No-op in this generic class

    # ------------------------------------------------------------------------------
    # Synchronization between DSync instances
    # ------------------------------------------------------------------------------

    def sync_from(self, source: "DSync", diff_class: Type[Diff] = Diff, flags: DSyncFlags = DSyncFlags.NONE):
        """Synchronize data from the given source DSync object into the current DSync object.

        Args:
            source (DSync): object to sync data from into this one
            diff_class (class): Diff or subclass thereof to use to calculate the diffs to use for synchronization
            flags (DSyncFlags): Flags influencing the behavior of this sync.
        """
        log = self._log.bind(src=source, dst=self, flags=flags).unbind("dsync")
        diff = self.diff_from(source, diff_class=diff_class, flags=flags)

        log.info("Beginning sync")
        for child in diff.get_children():
            self._sync_from_diff_element(child, flags=flags, logger=log)
        log.info("Sync complete")

    def sync_to(self, target: "DSync", diff_class: Type[Diff] = Diff, flags: DSyncFlags = DSyncFlags.NONE):
        """Synchronize data from the current DSync object into the given target DSync object.

        Args:
            target (DSync): object to sync data into from this one.
            diff_class (class): Diff or subclass thereof to use to calculate the diffs to use for synchronization
            flags (DSyncFlags): Flags influencing the behavior of this sync.
        """
        target.sync_from(self, diff_class=diff_class, flags=flags)

    def _sync_from_diff_element(
        self,
        element: DiffElement,
        flags: DSyncFlags = DSyncFlags.NONE,
        logger: structlog.BoundLogger = None,
        parent_model: DSyncModel = None,
    ):
        """Synchronize a given DiffElement (and its children, if any) into this DSync.

        Helper method for `sync_from`/`sync_to`; this generally shouldn't be called on its own.

        Args:
            element: DiffElement to synchronize diffs from
            flags (DSyncFlags): Flags influencing the behavior of this sync.
            logger: Parent logging context
            parent_model: Parent object to update (`add_child`/`remove_child`) if the sync creates/deletes an object.
        """
        # pylint: disable=too-many-branches
        # GFM: I made a few attempts at refactoring this to reduce the branching, but found that it was less readable.
        # So let's live with the slightly too high number of branches (14/12) for now.
        log = logger or self._log
        object_class = getattr(self, element.type)
        obj = self.get(object_class, element.keys)
        # Get the attributes that actually differ between source and dest
        diffs = element.get_attrs_diffs()
        log = log.bind(
            action=element.action,
            model=object_class.get_type(),
            unique_id=object_class.create_unique_id(**element.keys),
            diffs=diffs,
        )

        try:
            if element.action == "create":
                log.debug("Attempting object creation")
                if obj:
                    raise ObjectNotCreated(f"Failed to create {object_class.get_type()} {element.keys} - it exists!")
                obj = object_class.create(dsync=self, ids=element.keys, attrs={key: diffs[key]["src"] for key in diffs})
                log.info("Created successfully", status="success")
            elif element.action == "update":
                log.debug("Attempting object update")
                if not obj:
                    raise ObjectNotUpdated(f"Failed to update {object_class.get_type()} {element.keys} - not found!")
                obj = obj.update(attrs={key: diffs[key]["src"] for key in diffs})
                log.info("Updated successfully", status="success")
            elif element.action == "delete":
                log.debug("Attempting object deletion")
                if not obj:
                    raise ObjectNotDeleted(f"Failed to delete {object_class.get_type()} {element.keys} - not found!")
                obj = obj.delete()
                log.info("Deleted successfully", status="success")
            else:
                if flags & DSyncFlags.LOG_UNCHANGED_RECORDS:
                    log.debug("No action needed", status="success")
        except ObjectCrudException as exception:
            log.error(str(exception), status="error")
            if not flags & DSyncFlags.CONTINUE_ON_FAILURE:
                raise
        else:
            if obj is None:
                log.warning("Non-fatal failure encountered", status="failure")

        if obj is None:
            log.warning("Not syncing children")
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
            self._sync_from_diff_element(child, flags=flags, parent_model=obj, logger=logger)

    # ------------------------------------------------------------------------------
    # Diff calculation and construction
    # ------------------------------------------------------------------------------

    def diff_from(self, source: "DSync", diff_class: Type[Diff] = Diff, flags: DSyncFlags = DSyncFlags.NONE) -> Diff:
        """Generate a Diff describing the difference from the other DSync to this one.

        Args:
            source (DSync): Object to diff against.
            diff_class (class): Diff or subclass thereof to use for diff calculation and storage.
            flags (DSyncFlags): Flags influencing the behavior of this diff operation.
        """
        log = self._log.bind(src=source, dst=self, flags=flags).unbind("dsync")
        log.info("Beginning diff")
        diff = diff_class()

        for obj_type in intersection(self.top_level, source.top_level):

            diff_elements = self._diff_objects(
                source=source.get_all(obj_type),
                dest=self.get_all(obj_type),
                source_root=source,
                flags=flags,
                logger=log,
            )

            for diff_element in diff_elements:
                diff.add(diff_element)

        # Notify the diff that it has been fully populated, in case it wishes to print, save to a file, etc.
        log.info("Diff complete")
        diff.complete()
        return diff

    def diff_to(self, target: "DSync", diff_class: Type[Diff] = Diff, flags: DSyncFlags = DSyncFlags.NONE) -> Diff:
        """Generate a Diff describing the difference from this DSync to another one.

        Args:
            target (DSync): Object to diff against.
            diff_class (class): Diff or subclass thereof to use for diff calculation and storage.
            flags (DSyncFlags): Flags influencing the behavior of this diff operation.
        """
        return target.diff_from(self, diff_class=diff_class, flags=flags)

    def _diff_objects(  # pylint: disable=too-many-arguments
        self,
        source: Iterable[DSyncModel],
        dest: Iterable[DSyncModel],
        source_root: "DSync",
        flags: DSyncFlags = DSyncFlags.NONE,
        logger: structlog.BoundLogger = None,
    ) -> List[DiffElement]:
        """Generate a list of DiffElement between the given lists of objects.

        Helper method for `diff_from`/`diff_to`; this generally shouldn't be called on its own.

        Args:
            source: DSyncModel instances retrieved from another DSync instance
            dest: DSyncModel instances retrieved from this DSync instance
            source_root (DSync): The other DSync object being diffed against (owner of the `source` models, if any)
            flags (DSyncFlags): Flags influencing the behavior of this diff operation.
            logger: Parent logging context

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
            log = logger or self._log
            src_obj, dst_obj = combined_dict[uid]
            if not src_obj and not dst_obj:
                # Should never happen
                raise RuntimeError(f"UID {uid} is in combined_dict but has neither src_obj nor dst_obj??")
            if src_obj:
                log = log.bind(model=src_obj.get_type(), unique_id=src_obj.get_unique_id())
                if flags & DSyncFlags.SKIP_UNMATCHED_SRC and not dst_obj:
                    log.debug("Skipping unmatched source object")
                    continue
                diff_element = DiffElement(
                    obj_type=src_obj.get_type(),
                    name=src_obj.get_shortname(),
                    keys=src_obj.get_identifiers(),
                    source_name=source_root.name,
                    dest_name=self.name,
                )
            elif dst_obj:
                log = log.bind(model=dst_obj.get_type(), unique_id=dst_obj.get_unique_id())
                if flags & DSyncFlags.SKIP_UNMATCHED_DST and not src_obj:
                    log.debug("Skipping unmatched dest object")
                    continue
                diff_element = DiffElement(
                    obj_type=dst_obj.get_type(),
                    name=dst_obj.get_shortname(),
                    keys=dst_obj.get_identifiers(),
                    source_name=source_root.name,
                    dest_name=self.name,
                )

            if src_obj:
                diff_element.add_attrs(source=src_obj.get_attrs(), dest=None)
            if dst_obj:
                diff_element.add_attrs(source=None, dest=dst_obj.get_attrs())

            # Recursively diff the children of src_obj and dst_obj and attach the resulting diffs to the diff_element
            self._diff_child_objects(diff_element, src_obj, dst_obj, source_root, flags=flags, logger=logger)

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
            # TODO: should we check/enforce whether all source models have the same DSync, whether all dest likewise?
            # TODO: should we check/enforce whether ALL DSyncModels in this dict have the same get_type() output?
            src_obj, dst_obj = combined_dict[uid]
            if src_obj and dst_obj:
                if src_obj.get_type() != dst_obj.get_type():
                    raise TypeError(f"Type mismatch: {src_obj.get_type()} vs {dst_obj.get_type()}")
                if src_obj.get_shortname() != dst_obj.get_shortname():
                    raise ValueError(f"Shortname mismatch: {src_obj.get_shortname()} vs {dst_obj.get_shortname()}")
                if src_obj.get_identifiers() != dst_obj.get_identifiers():
                    raise ValueError(f"Keys mismatch: {src_obj.get_identifiers()} vs {dst_obj.get_identifiers()}")

    def _diff_child_objects(  # pylint: disable=too-many-arguments
        self,
        diff_element: DiffElement,
        src_obj: Optional[DSyncModel],
        dst_obj: Optional[DSyncModel],
        source_root: "DSync",
        flags: DSyncFlags,
        logger: structlog.BoundLogger,
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
            # for example, child_type == "device" and child_fieldname == "devices"

            # for example, getattr(src_obj, "devices") --> list of device uids
            #          --> src_dsync.get_by_uids(<list of device uids>, "device") --> list of device instances
            src_objs = source_root.get_by_uids(getattr(src_obj, child_fieldname), child_type) if src_obj else []
            dst_objs = self.get_by_uids(getattr(dst_obj, child_fieldname), child_type) if dst_obj else []

            for child_diff_element in self._diff_objects(
                source=src_objs, dest=dst_objs, source_root=source_root, flags=flags, logger=logger,
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

        if not obj.dsync:
            obj.dsync = self

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

        if obj.dsync is self:
            obj.dsync = None

        del self._data[modelname][uid]


# DSyncModel references DSync and DSync references DSyncModel. Break the typing loop:
DSyncModel.update_forward_refs()
