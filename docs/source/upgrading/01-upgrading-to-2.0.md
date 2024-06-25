# Upgrading to 2.0

With diffsync 2.0, there a couple of breaking changes. What they are and how to deal with them is described in this document.

## Rename of the `diffsync.DiffSync` class to `diffsync.Adapter`

The main diffsync class `diffsync.DiffSync` has been renamed to `diffsync.Adapter` as we have found that this is the verbiage that is most often used by users and explains the intent of the class clearer. The old name will still be around until 2.1, but is considered deprecated at this point.

As a consequence, a lot of fields have been renamed all across diffsync. To the end user, this will most prominently appear in the signature of the `create` method, where you will have to rename the `diffsync` parameter to `adapter`.

## Upgrade to Pydantic's major version 2

A [migration guide](https://docs.pydantic.dev/latest/migration/) is available in the Pydantic documentation. Here are the key things that may apply to your usage of diffsync:

- Any fields that are of type `Optional` now need to provide an explicit `None` default (you can use [bump-pydantic](https://github.com/pydantic/bump-pydantic) to deal with this automatically for the most part)

```python
from typing import Optional

from diffsync import DiffSyncModel

# Before
class Person(DiffSyncModel):
    _identifiers = ("name",)
    _attributes = ("age",)

    name: str
    age: Optional[int]

# After
class BetterPerson(DiffSyncModel):
    _identifiers = ("name",)
    _attributes = ("age",)

    name: str
    age: Optional[int] = None
```