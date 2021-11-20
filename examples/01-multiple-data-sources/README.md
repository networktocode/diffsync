# Example 1 - Multiple Data Sources

This is a simple example to show how DiffSync can be used to compare and synchronize multiple data sources.

For this example, we have a shared model for Device and Interface defined in `models.py`
And we have 3 instances of DiffSync based on the same model but with different values (BackendA, BackendB & BackendC).

> The source code for this example is in Github in the [examples/01-multiple-data-sources/](https://github.com/networktocode/diffsync/tree/main/examples/01-multiple-data-sources) directory.

First create and populate all 3 objects:

```python
from backend_a import BackendA
from backend_b import BackendB
from backend_c import BackendC

# Create each

a = BackendA()
a.load()
print(a.str())

b = BackendB()
b.load()
print(b.str())

c = BackendC()
c.load()
print(c.str())
```

Configure verbosity of DiffSync's structured logging to console; the default is full verbosity (all logs including debugging):

```python
from diffsync.logging import enable_console_logging
enable_console_logging(verbosity=0)  # Show WARNING and ERROR logs only
# enable_console_logging(verbosity=1)  # Also include INFO logs
# enable_console_logging(verbosity=2)  # Also include DEBUG logs
```

Show the differences between A and B:

```python
diff_a_b = a.diff_to(b)
print(diff_a_b.str())
```

Show the differences between B and C:

```python
diff_b_c = c.diff_from(b)
print(diff_b_c.str())
```

Synchronize A and B (update B with the contents of A):

```python
a.sync_to(b)
print(a.diff_to(b).str())
# Alternatively you can pass in the diff object from above to prevent another diff calculation
# a.sync_to(b, diff=diff_a_b)
```

Now A and B will show no differences:

```python
diff_a_b = a.diff_to(b)
print(diff_a_b.str())
```

> In the Device model, the `site_name` and `role` are not included in the `_attributes`, so they are not shown when we are comparing the different objects, even if the value is different.
