# dsync

DSync is a utility library that can be used to compare and synchronize different datasets.

For example, it can be used to compare a list of devices from 2 inventories system and, if required, synchronize them in either direction.

```python
A = DSyncSystemA()
B = DSyncSystemB()

A.load()
B.load()

# it will show the difference between both systems
diff_a_b = A.diff_from(B)
diff.print_detailed()

# it will update System A to align with the current status of system B
A.sync_from(B)

# it will update System B to align with the current status of system A
A.sync_to(B)
```

# Getting Started

To be able to properly compare different datasets, DSync rely on a shared datamodel that both systems must use.

## Define your model with DSyncModel

DSyncModel is based on [Pydantic](https://pydantic-docs.helpmanual.io/) and is using Python Typing to define the format of each attribute.
Each DSyncModel class supports the following class-level attributes:
- `_modelname` (str) Define the type of the model, it's used to store the data internally (Mandatory)
- `_identifiers` List(str) List of instance field names used as primary keys for this object (Mandatory)
- `_shortname` List(str) List of instance field names to use for a shorter name (Optional)
- `_attributes` List(str) List of additional instance field names for this object (Optional)
- `_children` Dict: Dict of {`<modelname>`: `field_name`} to indicate how child objects should be stored. (Optional)

> DSyncModel must uniquely identified by their unique id, composed of all fields defined in `_identifiers`. DSyncModel do not support incremental IDs as primary key.

```python
from dsync import DSyncModel

class Site(DSyncModel):
    _modelname = "site"
    _identifiers = ("name",)
    _shortname = ()
    _attributes = ("contact_phone",)
    _children = {"device": "devices"}

    name: str
    contact_phone: str
    devices: List = list()
```

### Relationship between models.
Currently the relationship between models are very loose, by design. Instead of storing an object, it's recommended to store the uid of an object and retrieve it from the store as needed.

## DSync

A DSync object must reference each model available at the top of the object by its modelname and must have a `top_level` attribute defined to indicate how the diff and the synchronization should be done. In the example below, `"site"` is the only top level objects so the synchronization engine will check all sites and all children of each site (devices)

```python
from dsync import DSync

class BackendA(DSync):

    site = Site
    device = Device

    top_level = ["site"]
```

It's up to the user to populate the internal cache with the appropriate data. In the example below we are using the `load()` method to populate the cache but it's not mandatory, it could be done differently

## Store data in a DSync object

To add a site to the local cache/store, you need to pass a valid DSyncModel object to the `add()` function.
```python

class BackendA(DSync):
    [...]

    def load(self):
        # Store an individual object
        site = self.site(name="nyc")
        self.add(site)

        # Store an object and define it as a children for another object
        device = self.device(name="rtr-nyc", role="router", site_name="nyc")
        self.add(device)
        site.add_child(device)
```

## Update Remote system on Sync

To update a remote system, you need to extend your DSyncModel class(es) to define your own `create`, `update` and/or `delete` methods for each model.
A DSyncModel instance stores a reference to its parent DSync class in case you need to use it to look up other model instances from the DSync's cache.

```python
class Device(DSyncModel):
    [...]

    @classmethod
    def create(cls, dsync, ids, attrs):
        ## TODO add your own logic here to create the device on the remote system
        super().create(ids=ids, dsync=dsync, attrs=attrs)

    def update(self, attrs):
        ## TODO add your own logic here to update the device on the remote system
        return super().update(attrs)

    def delete(self):
        ## TODO add your own logic here to delete the device on the remote system
        super().delete()
        return self
```
