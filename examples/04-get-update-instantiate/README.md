# Example 4 - Using get or update helpers

This example aims to expand on [Example 1](https://github.com/networktocode/diffsync/tree/main/examples/01-multiple-data-sources/README.md) that will take advantage of two new helper methods on the `DiffSync` class; `get_or_instantiate` and `update_or_instantiate`.

Both methods act similar to Django's `get_or_create` function to return the object and then a boolean to identify whether the object was created or not. Let's dive into each of them.

## get_or_instantiate

The following arguments are supported: model (`DiffSyncModel`), ids (dictionary), and attrs (dictionary). The `model` and `ids` are used to find an existing object. If the object does not currently exist within the `DiffSync` adapter, it will then use `model`, `ids`, and `attrs` to add the object.

It will then return a tuple that can be unpacked.

```python
obj, created = self.get_or_instantiate(Interface, {"device_name": "test100", "name": "eth0"}, {"description": "Test description"})
```

If the object already exists, `created` will be `False` or else it will return `True` if the object had to be created.

## update_or_instantiate

This helper is similar to `get_or_instantiate`, but it will update an existing object or add a new instance with the provided `ids` and `attrs`. The method does accept the same arguments, but requires `attrs`, whereas `get_or_instantiate` does not.

```python
obj, created = self.update_or_instantiate(Interface, {"device_name": "test100", "name": "eth0"}, {"description": "Test description"})
```

## Example Walkthrough

We can take a look at the data we will be loading into each backend to understand why these helper methods are valuable.

### Example Data

```python
BACKEND_DATA_A = [
    {
        "name": "nyc-spine1",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"},
        "site": "nyc",
    },
    {
        "name": "nyc-spine2",
        "role": "spine",
        "interfaces": {"eth0": "Interface 0", "eth1": "Interface 1"},
        "site": "nyc",
    },
]
```

## Example Load

```python
    def load(self):
        """Initialize the BackendA Object by loading some site, device and interfaces from DATA."""
        for device_data in BACKEND_DATA_A:
            device, instantiated = self.get_or_instantiate(
                self.device, {"name": device_data["name"]}, {"role": device_data["role"]}
            )

            site, instantiated = self.get_or_instantiate(self.site, {"name": device_data["site"]})
            if instantiated:
                device.add_child(site)

            for intf_name, desc in device_data["interfaces"].items():
                intf, instantiated = self.update_or_instantiate(
                    self.interface, {"name": intf_name, "device_name": device_data["name"]}, {"description": desc}
                )
                if instantiated:
                    device.add_child(intf)
```

The new methods are helpful due to having devices that are part of the same site. As we iterate over the data and load it into the `DiffSync` adapter, we would have to account for `ObjectAlreadyExists` exceptions when we go to add each duplicate site we encounter within the data or possibly several other models depending how complex the synchronization of data is between backends.
