# dsync

DSync is a utility library that can be used to compare and syncronize different datasets. 

For example, it can be used to compare a list of devices from 2 inventories system and, if required, syncronize them in either direction.

```python
A = DSyncSystemA()
B = DSyncSystemB()

A.init()
B.init()

# it will show the difference between both systems 
diff_a_b = A.diff(B)
diff.print_detailed()

# it will update System A to align with the current status of system B
A.sync(B)

# it will update System B to align with the current status of system A
B.sync(A)
```

# Getting Started

To be able to properly compare different datasets, DSync rely on a shared datamodel that both systems must use. 

## Define your model with DSyncModel

DSyncModel is based on [Pydantic](https://pydantic-docs.helpmanual.io/) and is using Python Typing to define the format of each attribute.
Each DSyncModel object support the following attributes:
- `__modelname__` (str) Define the type of the model, it's used to store the data internally (Mandatory)
- `__identifier__` List(str) List of attribute names used as primary keys for this object (Mandatory)
- `__attributes__` List(str) List of optional attribute names for this object (Optional)
- `__shortname__` List(str) List of attribute names to use for a shorter name (Optional)
- `__children__` Dict: Dict of (<modelname>, attribute) name to indicate how children should be stored. (Optional)

> DSyncModel must uniquely identified by their unique id, composed of all attributes defined in `__identifier__`. DSyncModel do not support incremental IDs as primary key.

```python
from dsync import DSyncModel

class Site(DSyncModel):
    __modelname__ = "site"
    __identifier__ = ["name"]
    __shortname__ = []
    __attributes__ = []
    __children__ = {"device": "devices"}

    name: str
    devices: List = list()
```

### Relationship between models.
Currently the relationship between models are very loose, by design. Instead of storing an object, it's recommended to store the uid of an object and retrieve it from the store as needed. 

## DSync

A DSync object must reference each model available at the top of the object by its modelname and must have a `top_level` attribute define to indicate how the diff and the syncronization should be done. In the example below, `"site"` is the only top level objects so the syncronization engine will check all sites and all children of each site (devices)

```python
from dsync import DSync

class BackendA(DSync):

    site = Site
    device = Device

    top_level = ["site"]
```

It's up to the user to populate the internal cache with the appropriate data. In the example below we are using the `init()` method to populate the cache but it's not mandatory, it could be done differently

## Store data in a DSync object

To add a site to the local cache/store, you need to pass a valid DSyncModel object to the `add()` function.
```python

class BackendA(DSync):
    [...]

    def init(self): 
        # Store an individual object
        site = self.site(name="nyc")
        self.add(site)

        # Store an object and define it as a children for another object
        device = self.device(name="rtr-nyc", role="router", site_name="nyc")
        self.add(device)
        site.add_child(device)
```

## Update Remote system on Sync

To update a remote system, you need to extend your DSync object to define your own `create`, `update` or `delete` method for each model. The DSync engine will automatically look for `create_<modelname>`, `update_<modelname>` or  `delete_<modelname>` depending on the status of the object. 
Each method need to accept 2 dict, `keys` and `params` and should return a DSyncModel object:
- `keys` dict containing all identifier for this object
- `params` dict containing all attributes for this object

```python
class BackendA(DSync):
    [...]

    def create_device(self, keys, params):
        ## TODO add your own logic here to create the device on the remote system
        item = self.default_create(object_type="device", keys=keys, params=params)
        return item

    def update_device(self, keys, params):
        ## TODO add your own logic here to update the device on the remote system
        item = self.default_update(object_type="device", keys=keys, params=params)
        return item 
```
