# DiffSync

DiffSync is a utility library that can be used to compare and synchronize different datasets.

For example, it can be used to compare a list of devices from 2 inventory systems and, if required, synchronize them in either direction.

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

- Black, Pylint, Bandit, flake8, and pydocstyle for Python linting and formatting.
- pytest, coverage, and unittest for unit tests.

# Questions
Please see the [documentation](https://diffsync.readthedocs.io/en/latest/index.html) for detailed documentation on how to use `diffsync`. For any additional questions or comments, feel free to swing by the [Network to Code slack channel](https://networktocode.slack.com/) (channel #networktocode). Sign up [here](http://slack.networktocode.com/)