"""BaseStore module."""
from typing import Dict, List, Tuple, Type, Union, TYPE_CHECKING, Optional, Set, Any
import structlog  # type: ignore

from diffsync.exceptions import ObjectNotFound

if TYPE_CHECKING:
    from diffsync import DiffSyncModel
    from diffsync import Adapter


class BaseStore:
    """Reference store to be implemented in different backends."""

    def __init__(
        self,  # pylint: disable=unused-argument
        *args: Any,  # pylint: disable=unused-argument
        adapter: Optional["Adapter"] = None,
        name: str = "",
        **kwargs: Any,  # pylint: disable=unused-argument
    ) -> None:
        """Init method for BaseStore."""
        self.adapter = adapter
        self.name = name or self.__class__.__name__
        self._log = structlog.get_logger().new(store=self)

    def __str__(self) -> str:
        """Render store name."""
        return self.name

    def get_all_model_names(self) -> Set[str]:
        """Get all the model names stored.

        Return:
            Set of all the model names.
        """
        raise NotImplementedError

    def get(
        self, *, model: Union[str, "DiffSyncModel", Type["DiffSyncModel"]], identifier: Union[str, Dict]
    ) -> "DiffSyncModel":
        """Get one object from the data store based on its unique id.

        Args:
            model: DiffSyncModel class or instance, or modelname string, that defines the type of the object to retrieve
            identifier: Unique ID of the object to retrieve, or dict of unique identifier keys/values

        Raises:
            ValueError: if obj is a str and identifier is a dict (can't convert dict into a uid str without a model class)
            ObjectNotFound: if the requested object is not present
        """
        raise NotImplementedError

    def get_all(self, *, model: Union[str, "DiffSyncModel", Type["DiffSyncModel"]]) -> List["DiffSyncModel"]:
        """Get all objects of a given type.

        Args:
            model: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve

        Returns:
            List of Object
        """
        raise NotImplementedError

    def get_by_uids(
        self, *, uids: List[str], model: Union[str, "DiffSyncModel", Type["DiffSyncModel"]]
    ) -> List["DiffSyncModel"]:
        """Get multiple objects from the store by their unique IDs/Keys and type.

        Args:
            uids: List of unique id / key identifying object in the database.
            model: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve

        Raises:
            ObjectNotFound: if any of the requested UIDs are not found in the store
        """
        raise NotImplementedError

    def remove_item(self, modelname: str, uid: str) -> None:
        """Remove one item from store."""
        raise NotImplementedError

    def remove(self, *, obj: "DiffSyncModel", remove_children: bool = False) -> None:
        """Remove a DiffSyncModel object from the store.

        Args:
            obj: object to remove
            remove_children: If True, also recursively remove any children of this object

        Raises:
            ObjectNotFound: if the object is not present
        """
        modelname = obj.get_type()
        uid = obj.get_unique_id()

        self.remove_item(modelname, uid)

        if obj.adapter:
            obj.adapter = None

        if remove_children:
            for child_type, child_fieldname in obj.get_children_mapping().items():
                for child_id in getattr(obj, child_fieldname):
                    try:
                        child_obj = self.get(model=child_type, identifier=child_id)
                        self.remove(obj=child_obj, remove_children=remove_children)
                    except ObjectNotFound:
                        # Since this is "cleanup" code, log an error and continue, instead of letting the exception raise
                        self._log.error(
                            "Unable to remove child element as it was not found!",
                            child_type=child_type,
                            child_id=child_id,
                            parent_type=modelname,
                            parent_id=uid,
                        )

    def add(self, *, obj: "DiffSyncModel") -> None:
        """Add a DiffSyncModel object to the store.

        Args:
            obj: Object to store

        Raises:
            ObjectAlreadyExists: if a different object with the same uid is already present.
        """
        raise NotImplementedError

    def update(self, *, obj: "DiffSyncModel") -> None:
        """Update a DiffSyncModel object to the store.

        Args:
            obj: Object to update
        """
        raise NotImplementedError

    def count(self, *, model: Union[str, "DiffSyncModel", Type["DiffSyncModel"], None] = None) -> int:
        """Returns the number of elements of a specific model, or all elements in the store if not specified."""
        raise NotImplementedError

    def get_or_instantiate(
        self, *, model: Type["DiffSyncModel"], ids: Dict, attrs: Optional[Dict] = None
    ) -> Tuple["DiffSyncModel", bool]:
        """Attempt to get the object with provided identifiers or instantiate it with provided identifiers and attrs.

        Args:
            model: The DiffSyncModel to get or create.
            ids: Identifiers for the DiffSyncModel to get or create with.
            attrs: Attributes when creating an object if it doesn't exist. Defaults to None.

        Returns:
            Provides the existing or new object and whether it was created or not.
        """
        created = False
        try:
            obj = self.get(model=model, identifier=ids)
        except ObjectNotFound:
            if not attrs:
                attrs = {}
            obj = model(**ids, **attrs)
            # Add the object to diffsync adapter
            self.add(obj=obj)
            created = True

        return obj, created

    def get_or_add_model_instance(self, obj: "DiffSyncModel") -> Tuple["DiffSyncModel", bool]:
        """Attempt to get the object with provided obj identifiers or instantiate obj.

        Args:
            obj: An obj of the DiffSyncModel to get or add.

        Returns:
            Provides the existing or new object and whether it was added or not.
        """
        model = obj.get_type()
        ids = obj.get_unique_id()

        try:
            return self.get(model=model, identifier=ids), False
        except ObjectNotFound:
            self.add(obj=obj)
            return obj, True

    def update_or_instantiate(
        self, *, model: Type["DiffSyncModel"], ids: Dict, attrs: Dict
    ) -> Tuple["DiffSyncModel", bool]:
        """Attempt to update an existing object with provided ids/attrs or instantiate it with provided identifiers and attrs.

        Args:
            model: The DiffSyncModel to get or create.
            ids: Identifiers for the DiffSyncModel to get or create with.
            attrs: Attributes when creating/updating an object if it doesn't exist. Pass in empty dict, if no specific attrs.

        Returns:
            Provides the existing or new object and whether it was created or not.
        """
        created = False
        try:
            obj = self.get(model=model, identifier=ids)
        except ObjectNotFound:
            obj = model(**ids, **attrs)
            # Add the object to diffsync adapter
            self.add(obj=obj)
            created = True

        # Update existing obj with attrs
        for attr, value in attrs.items():
            if getattr(obj, attr) != value:
                setattr(obj, attr, value)

        return obj, created

    def update_or_add_model_instance(self, obj: "DiffSyncModel") -> Tuple["DiffSyncModel", bool]:
        """Attempt to update an existing object with provided ids/attrs or instantiate obj.

        Args:
            obj: An instance of the DiffSyncModel to update or create.

        Returns:
            Provides the existing or new object and whether it was added or not.
        """
        model = obj.get_type()
        ids = obj.get_unique_id()
        attrs = obj.get_attrs()

        added = False
        try:
            obj = self.get(model=model, identifier=ids)
        except ObjectNotFound:
            # Add the object to the diffsync instance
            self.add(obj=obj)
            added = True

        # Update existing obj with attrs
        for attr, value in attrs.items():
            setattr(obj, attr, value)

        return obj, added

    def _get_object_class_and_model(
        self, model: Union[str, "DiffSyncModel", Type["DiffSyncModel"]]
    ) -> Tuple[Union["DiffSyncModel", Type["DiffSyncModel"], None], str]:
        """Get object class and model name for a model."""
        if isinstance(model, str):
            modelname = model
            if not hasattr(self.adapter, model):
                return None, modelname
            object_class = getattr(self.adapter, model)
        else:
            object_class = model
            modelname = model.get_type()

        return object_class, modelname

    @staticmethod
    def _get_uid(
        model: Union[str, "DiffSyncModel", Type["DiffSyncModel"]],
        object_class: Union["DiffSyncModel", Type["DiffSyncModel"], None],
        identifier: Union[str, Dict],
    ) -> str:
        """Get the related uid for a model and an identifier."""
        if isinstance(identifier, str):
            uid = identifier
        elif object_class:
            uid = object_class.create_unique_id(**identifier)
        else:
            raise ValueError(
                f"Invalid args: ({model}, {object_class}, {identifier}): "
                f"either {object_class} should be a class/instance or {identifier} should be a str"
            )
        return uid
