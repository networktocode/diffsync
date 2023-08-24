# DiffSync

DiffSync is a utility library that can be used to compare and synchronize different datasets.

For example, it can be used to compare a list of devices from 2 inventory systems and, if required, synchronize them in either direction.

# Primary Use Cases

DiffSync is at its most useful when you have multiple sources or sets of data to compare and/or synchronize, and especially if any of the following are true:

- If you need to repeatedly compare or synchronize the data sets as one or both change over time.
- If you need to account for not only the creation of new records, but also changes to and deletion of existing records as well.
- If various types of data in your data set naturally form a tree-like or parent-child relationship with other data.
- If the different data sets have some attributes in common and other attributes that are exclusive to one or the other.

# Overview of DiffSync

DiffSync acts as an intermediate translation layer between all of the data sets you are diffing and/or syncing. In practical terms, this means that to use DiffSync, you will define a set of data models as well as the “adapters” needed to translate between each base data source and the data model. In Python terms, the adapters will be subclasses of the `Adapter` class, and each data model class will be a subclass of the `DiffSyncModel` class.

![Diffsync Components](https://raw.githubusercontent.com/networktocode/diffsync/develop/docs/images/diffsync_components.png "Diffsync Components")


Once you have used each adapter to load each data source into a collection of data model records, you can then ask DiffSync to “diff” the two data sets, and it will produce a structured representation of the difference between them. In Python, this is accomplished by calling the `diff_to()` or `diff_from()` method on one adapter and passing the other adapter as a parameter.

![Diffsync Diff Creation](https://raw.githubusercontent.com/networktocode/diffsync/develop/docs/images/diffsync_diff_creation.png "Diffsync Diff Creation")

You can also ask DiffSync to “sync” one data set onto the other, and it will instruct your adapter as to the steps it needs to take to make sure that its data set accurately reflects the other. In Python, this is accomplished by calling the `sync_to()` or `sync_from()` method on one adapter and passing the other adapter as a parameter.

![Diffsync Sync](https://raw.githubusercontent.com/networktocode/diffsync/develop/docs/images/diffsync_sync.png "Diffsync Sync")

# Simple Example

```python
A = DiffSyncSystemA()
B = DiffSyncSystemB()

A.load()
B.load()

# Show the difference between both systems, that is, what would change if we applied changes from System B to System A
diff_a_b = A.diff_from(B)
print(diff_a_b.str())

# Update System A to align with the current status of system B
A.sync_from(B)

# Update System B to align with the current status of system A
A.sync_to(B)
```

> You may wish to peruse the `diffsync` [GitHub topic](https://github.com/topics/diffsync) for examples of projects using this library.

# Documentation

The documentation is available [on Read The Docs](https://diffsync.readthedocs.io/en/latest/index.html).

# Installation

### Option 1: Install from PyPI.

```
$ pip install diffsync
```

### Option 2: Install from a GitHub branch, such as main as shown below.
```
$ pip install git+https://github.com/networktocode/diffsync.git@main
```

# Contributing
Pull requests are welcomed and automatically built and tested against multiple versions of Python through GitHub Actions.

The project is following Network to Code software development guidelines and are leveraging the following:

- Black, Pylint, Bandit, flake8, and pydocstyle, mypy for Python linting, formatting and type hint checking.
- pytest, coverage, and unittest for unit tests.

You can ensure your contribution adheres to these checks by running `invoke tests` from the CLI.
The command `invoke build` builds a docker container with all the necessary dependencies (including the redis backend) locally to facilitate the execution of these tests.

# Questions
Please see the [documentation](https://diffsync.readthedocs.io/en/latest/index.html) for detailed documentation on how to use `diffsync`. For any additional questions or comments, feel free to swing by the [Network to Code slack channel](https://networktocode.slack.com/) (channel #networktocode). Sign up [here](http://slack.networktocode.com/)
