"""BaseStore module."""
from typing import Dict, List, Mapping, Text, Tuple, Type, Union, TYPE_CHECKING
import structlog  # type: ignore

from diffsync.exceptions import ObjectNotFound

if TYPE_CHECKING:
    from diffsync import DiffSyncModel


class BaseStore:
    """Reference store to be implemented in different backends."""

    def __init__(self, *args, diffsync=None, name: str = "", **kwargs) -> None:  # pylint: disable=unused-argument
        """Init method for BaseStore."""
        self.diffsync = diffsync
        self.name = name if name else self.__class__.__name__
        self._log = structlog.get_logger().new(diffsync=self)

    def __str__(self):
        """Render store name."""
        return self.name

    def get_all_model_names(self):
        """Get all the model names stored.

        Return:
            List[str]: List of all the model names.
        """
        raise NotImplementedError

    def get(self, obj: Union[Text, "DiffSyncModel", Type["DiffSyncModel"]], identifier: Union[Text, Mapping]):
        """Get one object from the data store based on its unique id.

        Args:
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the object to retrieve
            identifier: Unique ID of the object to retrieve, or dict of unique identifier keys/values

        Raises:
            ValueError: if obj is a str and identifier is a dict (can't convert dict into a uid str without a model class)
            ObjectNotFound: if the requested object is not present
        """
        raise NotImplementedError

    def get_all(self, obj: Union[Text, "DiffSyncModel", Type["DiffSyncModel"]]) -> List["DiffSyncModel"]:  #
        """Get all objects of a given type.

        Args:
            obj: DiffSyncModel class or instance, or modelname string, that defines the type of the objects to retrieve

        Returns:
            List[DiffSyncModel]: List of Object
        """
        raise NotImplementedError

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
        raise NotImplementedError

    def remove(self, obj: "DiffSyncModel", remove_children: bool = False):  #
        """Remove a DiffSyncModel object from the store.

        Args:
            obj (DiffSyncModel): object to remove
            remove_children (bool): If True, also recursively remove any children of this object

        Raises:
            ObjectNotFound: if the object is not present
        """
        raise NotImplementedError

    def add(self, obj: "DiffSyncModel"):  #
        """Add a DiffSyncModel object to the store.

        Args:
            obj (DiffSyncModel): Object to store

        Raises:
            ObjectAlreadyExists: if a different object with the same uid is already present.
        """
        raise NotImplementedError

    def update(self, obj: "DiffSyncModel"):  #
        """Update a DiffSyncModel object to the store.

        Args:
            obj (DiffSyncModel): Object to update
        """
        raise NotImplementedError

    def count(self, modelname):
        """Returns the number of elements of an specific model name."""
        raise NotImplementedError

    def get_or_instantiate(
        self, model: Type["DiffSyncModel"], ids: Dict, attrs: Dict = None  #
    ) -> Tuple["DiffSyncModel", bool]:  #
        """Attempt to get the object with provided identifiers or instantiate it with provided identifiers and attrs.

        Args:
            model (DiffSyncModel): The DiffSyncModel to get or create.
            ids (Mapping): Identifiers for the DiffSyncModel to get or create with.
            attrs (Mapping, optional): Attributes when creating an object if it doesn't exist. Defaults to None.

        Returns:
            Tuple[DiffSyncModel, bool]: Provides the existing or new object and whether it was created or not.
        """
        created = False
        try:
            obj = self.get(model, ids)
        except ObjectNotFound:
            if not attrs:
                attrs = {}
            obj = model(**ids, **attrs)
            # Add the object to diffsync adapter
            self.add(obj)
            created = True

        return obj, created

    def update_or_instantiate(
        self, model: Type["DiffSyncModel"], ids: Dict, attrs: Dict  #
    ) -> Tuple["DiffSyncModel", bool]:  #
        """Attempt to update an existing object with provided ids/attrs or instantiate it with provided identifiers and attrs.

        Args:
            model (DiffSyncModel): The DiffSyncModel to get or create.
            ids (Dict): Identifiers for the DiffSyncModel to get or create with.
            attrs (Dict): Attributes when creating/updating an object if it doesn't exist. Pass in empty dict, if no specific attrs.

        Returns:
            Tuple[DiffSyncModel, bool]: Provides the existing or new object and whether it was created or not.
        """
        created = False
        try:
            obj = self.get(model, ids)
        except ObjectNotFound:
            obj = model(**ids, **attrs)
            # Add the object to diffsync adapter
            self.add(obj)
            created = True

        # Update existing obj with attrs
        for attr, value in attrs.items():
            if getattr(obj, attr) != value:
                setattr(obj, attr, value)

        return obj, created
