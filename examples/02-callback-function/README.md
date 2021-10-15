# Example 2 - Callback Function

This example shows how you can set up DiffSync to invoke a callback function to update its status as a sync proceeds. This could be used to, for example, update a status bar (such as with the [tqdm](https://github.com/tqdm/tqdm) library), although here for simplicity we'll just have the callback print directly to the console.

> The source code for this example is in Github in the [examples/02-callback-function/](https://github.com/networktocode/diffsync/tree/main/examples/02-callback-function) directory.


```python
from diffsync.logging import enable_console_logging
from main import DiffSync1, DiffSync2, print_callback

enable_console_logging(verbosity=0)  # Show WARNING and ERROR logs only

# Create a DiffSync1 instance and populate it with records numbered 1-100
ds1 = DiffSync1()
ds1.load(count=100)

# Create a DiffSync2 instance and populate it with 100 random records in the range 1-200
ds2 = DiffSync2()
ds2.load(count=100)

# Identify and attempt to resolve the differences between the two,
# periodically invoking print_callback() as DiffSync progresses
ds1.sync_to(ds2, callback=print_callback)
```

You should see output similar to the following:
```
diff: Processed   1/200 records.
diff: Processed   3/200 records.
...
diff: Processed 199/200 records.
diff: Processed 200/200 records.
sync: Processed   1/134 records.
sync: Processed   2/134 records.
...
sync: Processed 134/134 records.
```

A few points to note:

- For each record in `ds1` and `ds2`, either it exists in both, exists only in `ds1`, or exists only in `ds2`.
- The total number of records reported during the `"diff"` stage is the sum of the number of records in both `ds1` and `ds2`.
- For this very simple set of models, the progress counter during the `"diff"` stage will increase at each step by 2 (if a corresponding pair of models is identified between`ds1` and `ds2`) or by 1 (if a model exists only in `ds1` or only in `ds2`).
- The total number of records reported during the `"sync"` stage is the number of distinct records existing across `ds1` and `ds2` combined, so it will be less than the total reported during the `"diff"` stage.
- By design for this example, `ds2` is populated semi-randomly with records, so the exact number reported during the `"sync"` stage may differ for you.
