
# Custom Diff Class

When performing a diff or a sync operation, a diff object is generated. A diff object is itself composed of DiffElement objects representing the different elements of the original datasets with their differences.  

The diff object helps to access all the DiffElements. It's possible to provide your own Diff class in order to customize some of its capabilities including:
- The rendering of the result of the diff
- The order in which the elements are processed 

## Using your own Diff class

To use your own diff class, you need to provide it at runtime when calling one of these functions : `diff_to`, `diff_from`, `sync_to` or `sync_from`.

```python
>>> from diffsync.enum import DiffSyncFlags
>>> from diff import AlphabeticalOrderDiff
>>> diff = remote_adapter.diff_from(local_adapter, diff_class=AlphabeticalOrderDiff)
>>> type(diff)
<class 'AlphabeticalOrderDiff'>
```

## Change the rendering of the result of the diff

To update how the result of a diff is rendered by default, you can provide your own `str()` function of the diff class.

```python
>>> from diffsync.diff import Diff
class MyDiff(Diff):

    def str(self):
        # Generate a string representation of the diff
```

## Change the order in which the element are being processed 

By default, all objects of the same type will be stored in a dictionary and as such the order in which they will be processed during a diff or a sync operation is not guaranteed (although in most cases, it will match the order in which they were initially loaded and added to the adapter). When the order in which a given group of object should be processed is important, it's possible to define your own ordering inside a custom Diff class.

When iterating over a list of objects, either at the top level or as a group of children of a given object, the core engine is looking for a function named after the type of the object `order_children_<type>` and if none is found it will rely on the default function `order_children_default`. Either function need to be present and need to return an Iterator of DiffElement. 

In the example below, by default all devices will be sorted per type of CRUD operations (`order_children_device`) while all other objects will be sorted alphabetically (`order_children_default`)

```python
class AlphabeticalOrderDiff(Diff):
    """Simple diff to return all children country in alphabetical order."""

    @classmethod
    def order_children_default(cls, children):
        """Simple diff to return all children in alphabetical order."""
        for child_name, child in sorted(children.items()):
            yield children[child_name]

    @classmethod
    def order_children_device(cls, children):
        """Return a list of device sorted by CRUD action and alphabetically."""
        children_by_type = defaultdict(list)

        # Organize the children's name by action create, update or delete
        for child_name, child in children.items():
            action = child.action or "update
            children_by_type[action].append(child_name)

        # Create a global list, organized per action
        sorted_children = sorted(children_by_type["create"])
        sorted_children += sorted(children_by_type["update"])
        sorted_children += sorted(children_by_type["delete"])

        for name in sorted_children:
            yield children[name]
```

