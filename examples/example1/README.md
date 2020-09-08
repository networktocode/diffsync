

This is a simple example to show how dsync can be used to compare and syncronize multiple data sources.

For this example, we have a shared model for Device and Interface defined in `models.py`
And we have 3 instances of DSync based on the same model but with different values (BackendA, BackendB & BackendC).


First initialize all 3 objects
```python
from backend_a import BackendA
from backend_b import BackendB
from backend_c import BackendC

# Create each

a = BackendA()
a.init()
b = BackendB()
b.init(
c = BackendC()
c.init()
```

Show the differences between A and B
```python
diff_a_b = a.diff(b)
diff_a_b.print_detailed()
```

Show the differences between B and C
```python
diff_b_c = b.diff(c)
diff_b_c.print_detailed()
```

Syncronize A and B
```python
a.sync(b)
a.diff(b).print_detailed()
```

Now A and B will show no differences
```python
diff_a_b = a.diff(b)
diff_a_b.print_detailed()
```

> In the Device model, the role is not defined as an attribute so it's not showned with we are comparing the different objects, even if the value is different.
