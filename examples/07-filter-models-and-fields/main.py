from pathlib import Path

import yaml

from diffsync import DiffSyncModel, DiffSync
from diffsync.helpers import filter_model_fields

this_dir = Path(__file__).parent


class Site(DiffSyncModel):
    """Example site base model."""

    _modelname = "site"
    _identifiers = ("name",)
    _attributes = ("description",)

    name: str
    description: str


class Prefix(DiffSyncModel):
    """Example prefix base model."""

    _modelname = "prefix"
    _identifiers = ("prefix",)
    _attributes = ("description",)

    prefix: str
    description: str


class ExampleBackend(DiffSync):
    """Abstract backend example base class."""

    site = Site
    prefix = Prefix

    top_level = ["site", "prefix"]

    def load(self):
        for data in self.data["site"]:
            site = self.site(**data)
            self.add(site)
        for data in self.data["prefix"]:
            prefix = self.prefix(**data)
            self.add(prefix)


class BackendA(ExampleBackend):
    """Example backend A."""

    def __init__(self, *args, **kwargs):
        with open(this_dir / "data" / "data_a.yml", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)
        super().__init__(*args, **kwargs)


class BackendB(ExampleBackend):
    """Example backend B."""

    def __init__(self, *args, **kwargs):
        with open(this_dir / "data" / "data_b.yml", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

        super().__init__(*args, **kwargs)


@filter_model_fields(fields_to_filter=["description"])
class FilteredSite(Site):
    pass


class FilteredBackendA(ExampleBackend):
    """Example backend A after filtering."""

    site = FilteredSite

    def __init__(self, *args, **kwargs):
        with open(this_dir / "data" / "data_a_filtered.yml", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

        super().__init__(*args, **kwargs)


class FilteredBackendB(ExampleBackend):
    """Example backend B after filtering."""

    site = FilteredSite

    def __init__(self, *args, **kwargs):
        with open(this_dir / "data" / "data_b_filtered.yml", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

        super().__init__(*args, **kwargs)


if __name__ == "__main__":
    print("\n")
    print("Unfiltered example:")
    print("\n")
    backend_a = BackendA()
    backend_b = BackendB()
    backend_a.load()
    backend_b.load()
    diff = backend_a.diff_to(backend_b)
    print(diff.str())

    print("\n")
    print("Filtered example:")
    print("\n")
    filtered_backend_a = FilteredBackendA()
    filtered_backend_b = FilteredBackendB()
    filtered_backend_a.load()
    filtered_backend_b.load()
    diff = filtered_backend_a.diff_to(filtered_backend_b)
    print(diff.str())
