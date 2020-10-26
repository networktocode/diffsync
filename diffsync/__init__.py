"""DiffSync core classes and logic.

Copyright (c) 2020 Network To Code, LLC <info@networktocode.com>

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
from typing import ClassVar, Dict, Iterable, List, Mapping, MutableMapping, Optional, Text, Tuple, Type, Union

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


class DiffSyncModelFlags(enum.Flag):
    """Flags that can be set on a DiffSyncModel class or instance to affect its usage."""

    NONE = 0

    IGNORE = 0b1
    """Do not render diffs containing this model; do not make any changes to this model when synchronizing.

    Can be used to indicate a model instance that exists but should not be changed by DiffSync.
    """

    SKIP_CHILDREN_ON_DELETE = 0b10
    """When deleting this model, do not recursively delete its children.

    Can be used for the case where deletion of a model results in the automatic deletion of all its children.
    """


class DiffSyncFlags(enum.Flag):
    """Flags that can be passed to a sync_* or diff_* call to affect its behavior."""

    NONE = 0

    CONTINUE_ON_FAILURE = 0b1
    """Continue synchronizing even if failures are encountered when syncing individual models."""

    SKIP_UNMATCHED_SRC = 0b10
    """Ignore objects that only exist in the source/"from" DiffSync when determining diffs and syncing.

    If this flag is set, no new objects will be created in the target/"to" DiffSync.
    """

    SKIP_UNMATCHED_DST = 0b100
    """Ignore objects that only exist in the target/"to" DiffSync when determining diffs and syncing.

    If this flag is set, no objects will be deleted from the target/"to" DiffSync.
    """

    SKIP_UNMATCHED_BOTH = SKIP_UNMATCHED_SRC | SKIP_UNMATCHED_DST

    LOG_UNCHANGED_RECORDS = 0b1000
    """If this flag is set, a log message will be generated during synchronization for each model, even unchanged ones.

    By default, when this flag is unset, only models that have actual changes to synchronize will be logged.
    This flag is off by default to reduce the default verbosity of DiffSync, but can be enabled when debugging.
    """


class DiffSyncModel(BaseModel):
    """Base class for all DiffSync object models.

    Note that read-only APIs of this class are implemented as `get_*()` functions rather than as properties;
    this is intentional as specific model classes may want to use these names (`type`, `keys`, `attrs`, etc.)
    as model attributes and we want to avoid any ambiguity or collisions.

    This class has several underscore-prefixed class variables that subclasses should set as desired; see below.

    NOTE: The groupings _identifiers, _attributes, and _children are mutually exclusive; any given field name can
          be included in **at most** one of these three tuples.
    """

    _modelname: ClassVar[str] = "diffsyncmodel"
    """Name of this model, used by DiffSync to store and look up instances of this model or its equivalents.

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

    When calculating a Diff or performing a sync, DiffSync will automatically recurse into these child models.

    Note: inclusion in `_children` is mutually exclusive from inclusion in `_identifiers` or `_attributes`.
    """

    model_flags: DiffSyncModelFlags = DiffSyncModelFlags.NONE
    """Optional: any non-default behavioral flags for this DiffSyncModel.

    Can be set as a class attribute or an instance attribute as needed.
    """

    diffsync: Optional["DiffSync"] = None
    """Optional: the DiffSync instance that owns this model instance."""

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic class configuration."""

        # Let us have a DiffSync as an instance variable even though DiffSync is not a Pydantic model itself.
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

    def dict(self, **kwargs) -> dict:
        """Convert this DiffSyncModel to a dict, excluding the diffsync field by default as it is not serializable."""
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"diffsync"}
        return super().dict(**kwargs)

    def json(self, **kwargs) -> str:
        """Convert this DiffSyncModel to a JSON string, excluding the diffsync field by default as it is not serializable."""
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"diffsync"}
        if "exclude_defaults" not in kwargs:
            kwargs["exclude_defaults"] = True
        return super().json(**kwargs)

    def str(self, include_children: bool = True, indent: int = 0) -> str:
        """Build a detailed string representation of this DiffSyncModel and optionally its children."""
        margin = " " * indent
        output = f"{margin}{self.get_type()}: {self.get_unique_id()}: {self.get_attrs()}"
        for modelname, fieldname in self._children.items():
            output += f"\n{margin}  {fieldname}"
            child_ids = getattr(self, fieldname)
            if not child_ids:
                output += ": []"
            elif not self.diffsync or not include_children:
                output += f": {child_ids}"
            else:
                for child_id in child_ids:
                    child = self.diffsync.get(modelname, child_id)
                    if not child:
                        output += f"\n{margin}    {child_id} (details unavailable)"
                    else:
                        output += "\n" + child.str(include_children=include_children, indent=indent + 4)
        return output

    @classmethod
    def create(cls, diffsync: "DiffSync", ids: Mapping, attrs: Mapping) -> Optional["DiffSyncModel"]:
        """Instantiate this class, along with any platform-specific data creation.

        Args:
            diffsync: The master data store for other DiffSyncModel instances that we might need to reference
            ids: Dictionary of unique-identifiers needed to create the new object
            attrs: Dictionary of additional attributes to set on the new object

        Returns:
            DiffSyncModel: instance of this class, if all data was successfully created.
            None: if data creation failed in such a way that child objects of this model should not be created.

        Raises:
            ObjectNotCreated: if an error occurred.
        """
        return cls(**ids, diffsync=diffsync, **attrs)

    def update(self, attrs: Mapping) -> Optional["DiffSyncModel"]:
        """Update the attributes of this instance, along with any platform-specific data updates.

        Args:
            attrs: Dictionary of attributes to update on the object

        Returns:
            DiffSyncModel: this instance, if all data was successfully updated.
            None: if data updates failed in such a way that child objects of this model should not be modified.

        Raises:
            ObjectNotUpdated: if an error occurred.
        """
        for attr, value in attrs.items():
            # TODO: enforce that only attrs in self._attributes can be updated in this way?
            setattr(self, attr, value)
        return self

    def delete(self) -> Optional["DiffSyncModel"]:
        """Delete any platform-specific data corresponding to this instance.

        Returns:
            DiffSyncModel: this instance, if all data was successfully deleted.
            None: if data deletion failed in such a way that child objects of this model should not be deleted.

        Raises:
            ObjectNotDeleted: if an error occurred.
        """
        return self

    @classmethod
    def get_type(cls) -> Text:
        """Return the type AKA modelname of the object or the class

        Returns:
            str: modelname of the class, used in to store all objects
        """
        return cls._modelname

    @classmethod
    def create_unique_id(cls, **identifiers) -> Text:
        """Construct a unique identifier for this model class.

        Args:
            **identifiers: Dict of identifiers and their values, as in `get_identifiers()`.
        """
        return "__".join(str(identifiers[key]) for key in cls._identifiers)

    @classmethod
    def get_children_mapping(cls) -> Mapping[Text, Text]:
        """Get the mapping of types to fieldnames for child models of this model."""
        return cls._children

    def get_identifiers(self) -> Mapping:
        """Get a dict of all identifiers (primary keys) and their values for this object.

        Returns:
            dict: dictionary containing all primary keys for this device, as defined in _identifiers
        """
        return self.dict(include=set(self._identifiers))

    def get_attrs(self) -> Mapping:
        """Get all the non-primary-key attributes or parameters for this object.

        Similar to Pydantic's `BaseModel.dict()` method, with the following key differences:
        1. Does not include the fields in `_identifiers`
        2. Only includes fields explicitly listed in `_attributes`
        3. Does not include any additional fields not listed in `_attributes`

        Returns:
            dict: Dictionary of attributes for this object
        """
        return self.dict(include=set(self._attributes))

    def get_unique_id(self) -> Text:
        """Get the unique ID of an object.

        By default the unique ID is built based on all the primary keys defined in `_identifiers`.

        Returns:
            str: Unique ID for this object
        """
        return self.create_unique_id(**self.get_identifiers())

    def get_shortname(self) -> Text:
        """Get the (not guaranteed-unique) shortname of an object, if any.

        By default the shortname is built based on all the keys defined in `_shortname`.
        If `_shortname` is not specified, then this function is equivalent to `get_unique_id()`.

        Returns:
            str: Shortname of this object
        """
        if self._shortname:
            return "__".join([str(getattr(self, key)) for key in self._shortname])
        return self.get_unique_id()

    def add_child(self, child: "DiffSyncModel"):
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

    def remove_child(self, child: "DiffSyncModel"):
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


class DiffSync:
    """Class for storing a group of DiffSyncModel instances and diffing/synchronizing to another DiffSync instance."""

    # Add mapping of names to specific model classes here:
    # modelname1 = MyModelClass1
    # modelname2 = MyModelClass2

    type: ClassVar[Optional[str]] = None
    """Type of the object, will default to the name of the class if not provided."""

    top_level: ClassVar[List[str]] = []
    """List of top-level modelnames to begin from when diffing or synchronizing."""

    _data: MutableMapping[str, MutableMapping[str, DiffSyncModel]]
    """Defaultdict storing model instances.

    `self._data[modelname][unique_id] == model_instance`
    """

    def __init__(self, name=None):
        """Generic initialization function.

        Subclasses should be careful to call super().__init__() if they override this method.
        """
        self._data = defaultdict(dict)
        self._log = structlog.get_logger().new(diffsync=self)

        # If the type is not defined, use the name of the class as the default value
        if self.type is None:
            self.type = self.__class__.__name__

        # If the name has not been provided, use the type as the name
        self.name = name if name else self.type

    def __init_subclass__(cls):
        """Validate that references to specific DiffSyncModels use the correct modelnames.

        Called automatically on subclass declaration.
        """
        contents = cls.__dict__
        for name, value in contents.items():
            if isclass(value) and issubclass(value, DiffSyncModel) and value.get_type() != name:
                raise AttributeError(
                    f'Incorrect field name - {value.__name__} has type name "{value.get_type()}", not "{name}"'
                )

    def __str__(self):
        """String representation of a DiffSync."""
        if self.type != self.name:
            return f'{self.type} "{self.name}"'
        return self.type

    def __repr__(self):
        return f"<{str(self)}>"

    def load(self):
        """Load all desired data from whatever backend data source into this instance."""
        # No-op in this generic class

    def dict(self, exclude_defaults: bool = True, **kwargs) -> Mapping:
        """Represent the DiffSync contents as a dict, as if it were a Pydantic model."""
        data: Dict[str, Dict[str, Dict]] = {}
        for modelname in self._data:
            data[modelname] = {}
            for unique_id, model in self._data[modelname].items():
                data[modelname][unique_id] = model.dict(exclude_defaults=exclude_defaults, **kwargs)
        return data

    def str(self, indent: int = 0) -> str:
        """Build a detailed string representation of this DiffSync."""
        margin = " " * indent
        output = ""
        for modelname in self.top_level:
            output += f"{margin}{modelname}"
            models = self.get_all(modelname)
            if not models:
                output += ": []"
            else:
                for model in models:
                    output += "\n" + model.str(indent=indent + 2)
        return output

    # ------------------------------------------------------------------------------
    # Synchronization between DiffSync instances
    # ------------------------------------------------------------------------------

    def sync_from(self, source: "DiffSync", diff_class: Type[Diff] = Diff, flags: DiffSyncFlags = DiffSyncFlags.NONE):
        """Synchronize data from the given source DiffSync object into the current DiffSync object.

        Args:
            source (DiffSync): object to sync data from into this one
            diff_class (class): Diff or subclass thereof to use to calculate the diffs to use for synchronization
            flags (DiffSyncFlags): Flags influencing the behavior of this sync.
        """
        log = self._log.bind(src=source, dst=self, flags=flags).unbind("diffsync")
        diff = self.diff_from(source, diff_class=diff_class, flags=flags)

        log.info("Beginning sync")
        for child in diff.get_children():
            self._sync_from_diff_element(child, flags=flags, logger=log)
        log.info("Sync complete")

    def sync_to(self, target: "DiffSync", diff_class: Type[Diff] = Diff, flags: DiffSyncFlags = DiffSyncFlags.NONE):
        """Synchronize data from the current DiffSync object into the given target DiffSync object.

        Args:
            target (DiffSync): object to sync data into from this one.
            diff_class (class): Diff or subclass thereof to use to calculate the diffs to use for synchronization
            flags (DiffSyncFlags): Flags influencing the behavior of this sync.
        """
        target.sync_from(self, diff_class=diff_class, flags=flags)

    def _sync_from_diff_element(
        self,
        element: DiffElement,
        flags: DiffSyncFlags = DiffSyncFlags.NONE,
        logger: structlog.BoundLogger = None,
        parent_model: DiffSyncModel = None,
    ):
        """Synchronize a given DiffElement (and its children, if any) into this DiffSync.

        Helper method for `sync_from`/`sync_to`; this generally shouldn't be called on its own.

        Args:
            element: DiffElement to synchronize diffs from
            flags (DiffSyncFlags): Flags influencing the behavior of this sync.
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
                obj = object_class.create(diffsync=self, ids=element.keys, attrs=diffs["src"])
                log.info("Created successfully", status="success")
            elif element.action == "update":
                log.debug("Attempting object update")
                if not obj:
                    raise ObjectNotUpdated(f"Failed to update {object_class.get_type()} {element.keys} - not found!")
                obj = obj.update(attrs=diffs["src"])
                log.info("Updated successfully", status="success")
            elif element.action == "delete":
                log.debug("Attempting object deletion")
                if not obj:
                    raise ObjectNotDeleted(f"Failed to delete {object_class.get_type()} {element.keys} - not found!")
                obj = obj.delete()
                log.info("Deleted successfully", status="success")
            else:
                if flags & DiffSyncFlags.LOG_UNCHANGED_RECORDS:
                    log.debug("No action needed", status="success")
        except ObjectCrudException as exception:
            log.error(str(exception), status="error")
            if not flags & DiffSyncFlags.CONTINUE_ON_FAILURE:
                raise
        else:
            if obj is None:
                log.warning("Non-fatal failure encountered", status="failure")

        if obj is None:
            log.warning("Not syncing children")
            return

        if element.action == "create":
            if parent_model:
                parent_model.add_child(obj)
            self.add(obj)
        elif element.action == "delete":
            if parent_model:
                parent_model.remove_child(obj)
            if obj.model_flags & DiffSyncModelFlags.SKIP_CHILDREN_ON_DELETE:
                # We don't need to process the child objects, but we do need to discard them
                self.remove(obj, remove_children=True)
                return
            self.remove(obj)

        for child in element.get_children():
            self._sync_from_diff_element(child, flags=flags, parent_model=obj, logger=logger)

    # ------------------------------------------------------------------------------
    # Diff calculation and construction
    # ------------------------------------------------------------------------------

    def diff_from(
        self, source: "DiffSync", diff_class: Type[Diff] = Diff, flags: DiffSyncFlags = DiffSyncFlags.NONE
    ) -> Diff:
        """Generate a Diff describing the difference from the other DiffSync to this one.

        Args:
            source (DiffSync): Object to diff against.
            diff_class (class): Diff or subclass thereof to use for diff calculation and storage.
            flags (DiffSyncFlags): Flags influencing the behavior of this diff operation.
        """
        differ = DiffSyncDiffer(src_diffsync=source, dst_diffsync=self, flags=flags, diff_class=diff_class)
        return differ.calculate_diffs()

    def diff_to(
        self, target: "DiffSync", diff_class: Type[Diff] = Diff, flags: DiffSyncFlags = DiffSyncFlags.NONE
    ) -> Diff:
        """Generate a Diff describing the difference from this DiffSync to another one.

        Args:
            target (DiffSync): Object to diff against.
            diff_class (class): Diff or subclass thereof to use for diff calculation and storage.
            flags (DiffSyncFlags): Flags influencing the behavior of this diff operation.
        """
        return target.diff_from(self, diff_class=diff_class, flags=flags)

    # ------------------------------------------------------------------------------
    # Object Storage Management
    # ------------------------------------------------------------------------------

    def get(
        self, obj: Union[Text, DiffSyncModel, Type[DiffSyncModel]], identifier: Union[Text, Mapping]
    ) -> Optional[DiffSyncModel]:
        """Get one object from the data store based on its unique id.

        Args:
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the object to retrieve
            identifier: Unique ID of the object to retrieve, or dict of unique identifier keys/values
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
            self._log.warning(
                f"Tried to look up a {modelname} by identifier {identifier}, "
                "but don't know how to convert that to a uid string",
            )
            return None

        return self._data[modelname].get(uid)

    def get_all(self, obj: Union[Text, DiffSyncModel, Type[DiffSyncModel]]):
        """Get all objects of a given type.

        Args:
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve

        Returns:
            ValuesList[DiffSyncModel]: List of Object
        """
        if isinstance(obj, str):
            modelname = obj
        else:
            modelname = obj.get_type()

        return self._data[modelname].values()

    def get_by_uids(
        self, uids: List[Text], obj: Union[Text, DiffSyncModel, Type[DiffSyncModel]]
    ) -> List[DiffSyncModel]:
        """Get multiple objects from the store by their unique IDs/Keys and type.

        Args:
            uids: List of unique id / key identifying object in the database.
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve
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

    def add(self, obj: DiffSyncModel):
        """Add a DiffSyncModel object to the store.

        Args:
            obj (DiffSyncModel): Object to store

        Raises:
            ObjectAlreadyExists: if an object with the same uid is already present
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        if uid in self._data[modelname]:
            raise ObjectAlreadyExists(f"Object {uid} already present")

        if not obj.diffsync:
            obj.diffsync = self

        self._data[modelname][uid] = obj

    def remove(self, obj: DiffSyncModel, remove_children: bool = False):
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
            raise ObjectNotFound(f"Object {uid} not present")

        if obj.diffsync is self:
            obj.diffsync = None

        del self._data[modelname][uid]

        if remove_children:
            for child_type, child_fieldname in obj.get_children_mapping().items():
                for child_id in getattr(obj, child_fieldname):
                    child_obj = self.get(child_type, child_id)
                    if child_obj:
                        self.remove(child_obj, remove_children=remove_children)


# DiffSyncModel references DiffSync and DiffSync references DiffSyncModel. Break the typing loop:
DiffSyncModel.update_forward_refs()


class DiffSyncDiffer:
    """Helper class implementing diff calculation logic for DiffSync.

    Independent from Diff and DiffElement as those classes are purely data objects, while this stores some state.
    """

    def __init__(
        self, src_diffsync: DiffSync, dst_diffsync: DiffSync, flags: DiffSyncFlags, diff_class: Type[Diff] = Diff
    ):
        """Create a DiffSyncDiffer for calculating diffs between the provided DiffSync instances."""
        self.src_diffsync = src_diffsync
        self.dst_diffsync = dst_diffsync
        self.flags = flags

        self.logger = structlog.get_logger().new(src=src_diffsync, dst=dst_diffsync, flags=flags)
        self.diff_class = diff_class
        self.diff: Optional[Diff] = None

    def calculate_diffs(self) -> Diff:
        """Calculate diffs between the src and dst DiffSync objects and return the resulting Diff."""
        if self.diff is not None:
            return self.diff

        self.logger.info("Beginning diff calculation")
        self.diff = self.diff_class()
        for obj_type in intersection(self.dst_diffsync.top_level, self.src_diffsync.top_level):
            diff_elements = self.diff_object_list(
                src=self.src_diffsync.get_all(obj_type), dst=self.dst_diffsync.get_all(obj_type),
            )

            for diff_element in diff_elements:
                self.diff.add(diff_element)

        self.logger.info("Diff calculation complete")
        self.diff.complete()
        return self.diff

    def diff_object_list(self, src: Iterable[DiffSyncModel], dst: Iterable[DiffSyncModel]) -> List[DiffElement]:
        """Calculate diffs between two lists of like objects.

        Helper method to `calculate_diffs`, usually doesn't need to be called directly.

        These helper methods work in a recursive cycle:
        diff_object_list -> diff_object_pair -> diff_child_objects -> diff_object_list -> etc.
        """
        diff_elements = []

        if isinstance(src, ABCIterable) and isinstance(dst, ABCIterable):
            # Convert a list of DiffSyncModels into a dict using the unique_ids as keys
            dict_src = {item.get_unique_id(): item for item in src} if not isinstance(src, ABCMapping) else src
            dict_dst = {item.get_unique_id(): item for item in dst} if not isinstance(dst, ABCMapping) else dst

            combined_dict = {}
            for uid in dict_src:
                combined_dict[uid] = (dict_src.get(uid), dict_dst.get(uid))
            for uid in dict_dst:
                combined_dict[uid] = (dict_src.get(uid), dict_dst.get(uid))
        else:
            # In the future we might support set, etc...
            raise TypeError(f"Type combination {type(src)}/{type(dst)} is not supported... for now")

        self.validate_objects_for_diff(combined_dict.values())

        for uid in combined_dict:
            src_obj, dst_obj = combined_dict[uid]
            diff_element = self.diff_object_pair(src_obj, dst_obj)

            if diff_element:
                diff_elements.append(diff_element)

        return diff_elements

    @staticmethod
    def validate_objects_for_diff(object_pairs: Iterable[Tuple[Optional[DiffSyncModel], Optional[DiffSyncModel]]]):
        """Check whether all DiffSyncModels in the given dictionary are valid for comparison to one another.

        Helper method for `diff_object_list`.

        Raises:
            TypeError: If any pair of objects in the dict have differing get_type() values.
            ValueError: If any pair of objects in the dict have differing get_shortname() or get_identifiers() values.
        """
        for src_obj, dst_obj in object_pairs:
            # TODO: should we check/enforce whether all source models have the same DiffSync, whether all dest likewise?
            # TODO: should we check/enforce whether ALL DiffSyncModels in this dict have the same get_type() output?
            if src_obj and dst_obj:
                if src_obj.get_type() != dst_obj.get_type():
                    raise TypeError(f"Type mismatch: {src_obj.get_type()} vs {dst_obj.get_type()}")
                if src_obj.get_shortname() != dst_obj.get_shortname():
                    raise ValueError(f"Shortname mismatch: {src_obj.get_shortname()} vs {dst_obj.get_shortname()}")
                if src_obj.get_identifiers() != dst_obj.get_identifiers():
                    raise ValueError(f"Keys mismatch: {src_obj.get_identifiers()} vs {dst_obj.get_identifiers()}")

    def diff_object_pair(
        self, src_obj: Optional[DiffSyncModel], dst_obj: Optional[DiffSyncModel]
    ) -> Optional["DiffElement"]:
        """Diff the two provided DiffSyncModel objects and return a DiffElement or None.

        Helper method to `calculate_diffs`, usually doesn't need to be called directly.

        These helper methods work in a recursive cycle:
        diff_object_list -> diff_object_pair -> diff_child_objects -> diff_object_list -> etc.
        """
        if src_obj:
            model = src_obj.get_type()
            unique_id = src_obj.get_unique_id()
            shortname = src_obj.get_shortname()
            keys = src_obj.get_identifiers()
        elif dst_obj:
            model = dst_obj.get_type()
            unique_id = dst_obj.get_unique_id()
            shortname = dst_obj.get_shortname()
            keys = dst_obj.get_identifiers()
        else:
            raise RuntimeError("diff_object_pair() called with neither src_obj nor dst_obj??")

        log = self.logger.bind(model=model, unique_id=unique_id)
        if self.flags & DiffSyncFlags.SKIP_UNMATCHED_SRC and not dst_obj:
            log.debug("Skipping unmatched source object")
            return None
        if self.flags & DiffSyncFlags.SKIP_UNMATCHED_DST and not src_obj:
            log.debug("Skipping unmatched dest object")
            return None
        if src_obj and src_obj.model_flags & DiffSyncModelFlags.IGNORE:
            log.debug("Skipping due to IGNORE flag on source object")
            return None
        if dst_obj and dst_obj.model_flags & DiffSyncModelFlags.IGNORE:
            log.debug("Skipping due to IGNORE flag on dest object")
            return None

        diff_element = DiffElement(
            obj_type=model,
            name=shortname,
            keys=keys,
            source_name=self.src_diffsync.name,
            dest_name=self.dst_diffsync.name,
            diff_class=self.diff_class,
        )

        if src_obj:
            diff_element.add_attrs(source=src_obj.get_attrs(), dest=None)
        if dst_obj:
            diff_element.add_attrs(source=None, dest=dst_obj.get_attrs())

        # Recursively diff the children of src_obj and dst_obj and attach the resulting diffs to the diff_element
        self.diff_child_objects(diff_element, src_obj, dst_obj)

        return diff_element

    def diff_child_objects(
        self, diff_element: DiffElement, src_obj: Optional[DiffSyncModel], dst_obj: Optional[DiffSyncModel],
    ):
        """For all children of the given DiffSyncModel pair, diff recursively, adding diffs to the given diff_element.

        Helper method to `calculate_diffs`, usually doesn't need to be called directly.

        These helper methods work in a recursive cycle:
        diff_object_list -> diff_object_pair -> diff_child_objects -> diff_object_list -> etc.
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
            raise RuntimeError("Called with neither src_obj nor dest_obj??")

        for child_type, child_fieldname in children_mapping.items():
            # for example, child_type == "device" and child_fieldname == "devices"

            # for example, getattr(src_obj, "devices") --> list of device uids
            #          --> src_diffsync.get_by_uids(<list of device uids>, "device") --> list of device instances
            src_objs = self.src_diffsync.get_by_uids(getattr(src_obj, child_fieldname), child_type) if src_obj else []
            dst_objs = self.dst_diffsync.get_by_uids(getattr(dst_obj, child_fieldname), child_type) if dst_obj else []

            for child_diff_element in self.diff_object_list(src=src_objs, dst=dst_objs):
                diff_element.add_child(child_diff_element)

        return diff_element
