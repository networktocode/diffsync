
# Global and Model Flags

These flags offer a powerful way to instruct the core engine how to handle some specific situation without changing the data. One way to think of the flags is to represent them as configuration for the core engine. Currently 2 sets of flags are supported:
- **global flags**: applicable to all data.
- **model flags**: applicable to a specific model or to individual instances of a model.

> *The flags are stored in binary format which allows storing multiple flags in a single variable. See the section below [Working with flags](#working-with-flags) to learn how to manage them.*

The list of supported flags is expected to grow over time as more use cases are identified. If you think some additional flags should be supported, please reach out via Github to start a discussion.

## Global flags

Global flags can be defined at runtime when calling one of these functions : `diff_to` ,`diff_from`,  `sync_to` or `sync_from`

```python
from diffsync.enum import DiffSyncFlags
flags = DiffSyncFlags.SKIP_UNMATCHED_DST
diff = nautobot.diff_from(local, flags=flags)
```

### Supported Global Flags

| Name | Description | Binary Value |
|---|---|---|
| CONTINUE_ON_FAILURE | Continue synchronizing even if failures are encountered when syncing individual models. | 0b1 |
| SKIP_UNMATCHED_SRC | Ignore objects that only exist in the source/"from" DiffSync when determining diffs and syncing.  If this flag is set, no new objects will be created in the target/"to" DiffSync. | 0b10 |
| SKIP_UNMATCHED_DST | Ignore objects that only exist in the target/"to" DiffSync when determining diffs and syncing.  If this flag is set, no objects will be deleted from the target/"to" DiffSync. | 0b100 |
| SKIP_UNMATCHED_BOTH | Convenience value combining both SKIP_UNMATCHED_SRC and SKIP_UNMATCHED_DST into a single flag | 0b110 |
| LOG_UNCHANGED_RECORDS | If this flag is set, a log message will be generated during synchronization for each model, even unchanged ones. | 0b1000 |

## Model flags

Model flags are stored in the attribute `model_flags` of each model and are usually set when the data is being loaded into the adapter.

```python
from diffsync import DiffSync
from diffsync.enum import DiffSyncModelFlags
from model import MyDeviceModel

class MyAdapter(DiffSync):

    device = MyDeviceModel

    def load(self, data):
        """Load all devices into the adapter and add the flag IGNORE to all firewall devices."""
        for device in data.get("devices"):
            obj = self.device(name=device["name"])
            if "firewall" in device["name"]:
                obj.model_flags = DiffSyncModelFlags.IGNORE
            self.add(obj)
```

### Supported Model Flags

| Name | Description | Binary Value |
|---|---|---|
| IGNORE | Do not render diffs containing this model; do not make any changes to this model when synchronizing.  Can be used to indicate a model instance that exists but should not be changed by DiffSync. | 0b1 |
| SKIP_CHILDREN_ON_DELETE | When deleting this model, do not recursively delete its children. Can be used for the case where deletion of a model results in the automatic deletion of all its children. | 0b10 |
| SKIP_UNMATCHED_SRC | Ignore the model if it only exists in the source/"from" DiffSync when determining diffs and syncing. If this flag is set, no new model will be created in the target/"to" DiffSync. | 0b100 |
| SKIP_UNMATCHED_DST | Ignore the model if it only exists in the target/"to" DiffSync when determining diffs and syncing. If this flag is set, the model will not be deleted from the target/"to" DiffSync. | 0b1000 |
| SKIP_UNMATCHED_BOTH | Convenience value combining both SKIP_UNMATCHED_SRC and SKIP_UNMATCHED_DST into a single flag | 0b1100 |

## Working with flags

Flags are stored in binary format. In binary format, each bit of a variable represents 1 flag which allow us to have up to many flags stored in a single variable. Using binary flags provides more flexibility to add support for more flags in the future without redefining the current interfaces and the current DiffSync API.

### Enable a flag (Bitwise OR)

Enabling a flag is possible with the bitwise OR operator `|=`. It's important to use the bitwise operator OR when enabling a flags to ensure that the value of other flags remains unchanged.

```python
>>> from diffsync.enum import DiffSyncFlags
>>> flags = DiffSyncFlags.CONTINUE_ON_FAILURE
>>> flags
<DiffSyncFlags.CONTINUE_ON_FAILURE: 1>
>>> bin(flags.value)
'0b1'
>>> flags |= DiffSyncFlags.SKIP_UNMATCHED_DST
>>> flags
<DiffSyncFlags.SKIP_UNMATCHED_DST|CONTINUE_ON_FAILURE: 5>
>>> bin(flags.value)
'0b101'
```

### Checking the value of a specific flag (bitwise AND)

Validating if a flag is enabled is possible with the bitwise operator AND: `&`. The AND operator will return 0 if the flag is not set and the binary value of the flag if it's enabled. To convert the result of the test into a proper conditional it's possible to wrap the bitwise AND operator into a `bool` function.

```python
>>> from diffsync.enum import DiffSyncFlags
>>> flags = DiffSyncFlags.NONE
>>> bool(flags & DiffSyncFlags.CONTINUE_ON_FAILURE)
False
>>> flags |= DiffSyncFlags.CONTINUE_ON_FAILURE
>>> bool(flags & DiffSyncFlags.CONTINUE_ON_FAILURE)
True
```

### Disable a flag (bitwise NOT)

After a flag has been enabled, it's possible to disable it with a bitwise AND NOT operator : `&= ~`

```python
>>> from diffsync.enum import DiffSyncFlags
>>> flags = DiffSyncFlags.NONE
# Setting the flags SKIP_UNMATCHED_DST and CONTINUE_ON_FAILURE
>>> flags |= DiffSyncFlags.SKIP_UNMATCHED_DST | DiffSyncFlags.CONTINUE_ON_FAILURE
>>> flags
<DiffSyncFlags.SKIP_UNMATCHED_DST|CONTINUE_ON_FAILURE: 5>
>>> bool(flags & DiffSyncFlags.SKIP_UNMATCHED_DST)
True
# Unsetting the flag SKIP_UNMATCHED_DST; CONTINUE_ON_FAILURE remains set
>>> flags &= ~DiffSyncFlags.SKIP_UNMATCHED_DST
>>> flags
<DiffSyncFlags.CONTINUE_ON_FAILURE: 1>
>>> bool(flags & DiffSyncFlags.SKIP_UNMATCHED_DST)
False
```
