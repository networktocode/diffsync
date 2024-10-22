import enum
from collections import defaultdict
from typing import Dict, NewType, ClassVar, TypedDict, Any, Optional, Set, Tuple, Union
from typing_extensions import Self

from pydantic import BaseModel, ConfigDict

ModelName = NewType("ModelName", str)


class NGObjectAlreadyExists(Exception):
    pass


class NGModelFieldKind(enum.Enum):
    """Specify type of field."""
    ATTRIBUTE = "attribute"
    IDENTIFIER = "identifier"


class NGModelMetadata(TypedDict):
    """Used to store metadata about a model.

    """
    model_name: ModelName


class NGModel(BaseModel):
    # Class vars are automatically excluded attributes: https://docs.pydantic.dev/latest/concepts/models/#class-vars
    model_config = ConfigDict(frozen=True)
    metadata: ClassVar[NGModelMetadata]
    identifiers: ClassVar[Set[str]] = set()
    attributes: ClassVar[Set[str]] = set()

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Set class vars and validate that fields have their field type set.

        Ensure that
        - field types are set as type annotations
        - `identifiers` and `attributes` class vars are set according to those field types
        """
        field_categories = {
            kind: [] for kind in NGModelFieldKind
        }
        for field_name, field_info in cls.model_fields.items():
            field_type = next((m for m in field_info.metadata if isinstance(m, NGModelFieldKind)), None)
            if not field_type:
                raise ValueError(f"Field '{field_name}' on '{cls.__name__}' does not define a field type.")
            field_categories[field_type].append(field_name)
        cls.identifiers = set(field_categories[NGModelFieldKind.IDENTIFIER])
        cls.attributes = set(field_categories[NGModelFieldKind.ATTRIBUTE])
        if not hasattr(cls, "__hash__"):
            raise ValueError("All fields must be hashable.")

    def get_identifiers(self) -> Dict[str, Any]:
        return self.model_dump(include=self.identifiers)

    def get_attributes(self) -> Dict[str, Any]:
        return self.model_dump(include=self.attributes)

    def diff_to(self, other: "NGModel") -> frozenset[Tuple[str, Any]]:
        """Diff to another model.

        :returns: Dictionary that shows which fields need to be updated to what values
        """
        my_attributes = set(self.model_dump(include=self.attributes).items())
        other_attributes = set(other.model_dump(include=other.attributes).items())
        return frozenset(other_attributes - my_attributes)


class NGAdapter:
    def __init__(self):
        self._store: Dict[ModelName, Dict[frozenset, NGModel]] = defaultdict(dict)

    def add(self, obj: NGModel) -> None:
        """Adds a model to the store.

        :raises NGObjectAlreadyExists: Raised when the identifier key is already present in the store.
        """
        key = frozenset(obj.get_identifiers().items())
        if key in self._store[obj.metadata["model_name"]]:
            raise NGObjectAlreadyExists(f"Failed adding \"{obj}\". Key '{key}' already exists.")
        self._store[obj.metadata["model_name"]][key] = obj

    def get_keys(self, model_name: ModelName) -> Set[frozenset]:
        return set(self._store[model_name].keys())

    def get(self, model_name: ModelName, key: Union[frozenset[Tuple[str, Any]], Dict[str, Any]]) -> Optional[NGModel]:
        if isinstance(key, dict):
            key = frozenset(key.items())
        return self._store[model_name].get(key, None)

    @property
    def models(self) -> Set[ModelName]:
        return set(self._store.keys())


class NGDiff:
    def __init__(
        self,
        to_create: Dict[ModelName, Set[frozenset]],
        to_delete: Dict[ModelName, Set[frozenset]],
        to_update: Dict[ModelName, Dict[frozenset, dict[str, Any]]],
    ):
        self.to_create = to_create
        self.to_delete = to_delete
        self.to_update = to_update

    def report(self):
        output = ""
        model_names = set(self.to_create.keys()) | set(self.to_delete.keys()) | set(self.to_update.keys())
        for model_name in sorted(model_names):
            output += f"{model_name}:\n"
            if self.to_create[model_name]:
                output += "+\n"
            for key in self.to_create[model_name]:
                output += f"- {key}\n"
            if self.to_delete[model_name]:
                output += "-\n"
            for key in self.to_delete[model_name]:
                output += f"- {key}\n"
            if self.to_update[model_name]:
                output += "~\n"
            for key in self.to_update[model_name]:
                output += f"- {key}\n"
        return output

    @classmethod
    def diff(cls, source: NGAdapter, destination: NGAdapter) -> Self:
        to_create: Dict[ModelName, Set[frozenset]] = {}
        to_delete: Dict[ModelName, Set[frozenset]] = {}
        to_update: Dict[ModelName, Dict[frozenset, dict[str, Any]]] = defaultdict(dict)
        models_to_diff = source.models | destination.models
        for model_name in models_to_diff:
            existing_source_keys = source.get_keys(model_name)
            existing_destination_keys = destination.get_keys(model_name)
            to_create[model_name] = existing_source_keys - existing_destination_keys
            to_delete[model_name] = existing_destination_keys - existing_source_keys
            for key in existing_source_keys & existing_destination_keys:
                if diff_dict := source.get(model_name, key).diff_to(destination.get(model_name, key)):
                    to_update[model_name][key] = diff_dict
        return cls(to_create=to_create, to_delete=to_delete, to_update=to_update)
