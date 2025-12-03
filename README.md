<<<<<<< HEAD
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

![DiffSync Components](https://raw.githubusercontent.com/networktocode/diffsync/develop/docs/images/diffsync_components.png "DiffSync Components")


Once you have used each adapter to load each data source into a collection of data model records, you can then ask DiffSync to “diff” the two data sets, and it will produce a structured representation of the difference between them. In Python, this is accomplished by calling the `diff_to()` or `diff_from()` method on one adapter and passing the other adapter as a parameter.

![DiffSync Diff Creation](https://raw.githubusercontent.com/networktocode/diffsync/develop/docs/images/diffsync_diff_creation.png "DiffSync Diff Creation")

You can also ask DiffSync to “sync” one data set onto the other, and it will instruct your adapter as to the steps it needs to take to make sure that its data set accurately reflects the other. In Python, this is accomplished by calling the `sync_to()` or `sync_from()` method on one adapter and passing the other adapter as a parameter.

![DiffSync Sync](https://raw.githubusercontent.com/networktocode/diffsync/develop/docs/images/diffsync_sync.png "DiffSync Sync")

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

The project is following Network to Code software development guidelines and is leveraging the following:

- Black, Pylint, Bandit, flake8, and pydocstyle, mypy for Python linting, formatting and type hint checking.
- pytest, coverage, and unittest for unit tests.

You can ensure your contribution adheres to these checks by running `invoke tests` from the CLI.
The command `invoke build` builds a docker container with all the necessary dependencies (including the redis backend) locally to facilitate the execution of these tests.

# Questions
Please see the [documentation](https://diffsync.readthedocs.io/en/latest/index.html) for detailed documentation on how to use `diffsync`. For any additional questions or comments, feel free to swing by the [Network to Code slack channel](https://networktocode.slack.com/) (channel #networktocode). Sign up [here](http://slack.networktocode.com/)
=======
# Diffsync

<!--
Developer Note - Remove Me!

The README will have certain links/images broken until the PR is merged into `develop`. Update the GitHub links with whichever branch you're using (main etc.) if different.

The logo of the project is a placeholder (docs/images/icon-diffsync.png) - please replace it with your app icon, making sure it's at least 200x200px and has a transparent background!

To avoid extra work and temporary links, make sure that publishing docs (or merging a PR) is done at the same time as setting up the docs site on RTD, then test everything.
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/networktocode/diffsync/develop/docs/images/icon-Diffsync.png" class="logo" height="200px">
  <br>
  <a href="https://github.com/networktocode/diffsync/actions"><img src="https://github.com/networktocode/diffsync/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://diffsync.readthedocs.io/en/latest/"><img src="https://readthedocs.org/projects/diffsync/badge/"></a>
  <a href="https://pypi.org/project/diffsync/"><img src="https://img.shields.io/pypi/v/diffsync"></a>
  <a href="https://pypi.org/project/diffsync/"><img src="https://img.shields.io/pypi/dm/diffsync"></a>
  <br>
</p>

## Overview

> Developer Note: Add a long (2-3 paragraphs) description of what the library does, what problems it solves, etc.

## Documentation

Full documentation for this library can be found over on the [Diffsync Docs](https://diffsync.readthedocs.io/) website:

- [User Guide](https://diffsync.readthedocs.io/user/app_overview/) - Overview, Using the Library, Getting Started.
- [Administrator Guide](https://diffsync.readthedocs.io/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the Library.
- [Developer Guide](https://diffsync.readthedocs.io/dev/contributing/) - Extending the Library, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://diffsync.readthedocs.io/admin/release_notes/).
- [Frequently Asked Questions](https://diffsync.readthedocs.io/user/faq/).

### Contributing to the Documentation

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/networktocode/diffsync/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully-generated documentation site, you can build it with [MkDocs](https://www.mkdocs.org/). A container hosting the documentation can be started using the `invoke` commands (details in the [Development Environment Guide](https://diffsync/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). Using this container, as your changes to the documentation are saved, they will be automatically rebuilt and any pages currently being viewed will be reloaded in your browser.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://diffsync.readthedocs.io/en/latest/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#networktocode`), sign up [here](http://slack.networktocode.com/) if you don't have an account.
>>>>>>> c5f3eb1 (Cookie initialy baked by NetworkToCode Cookie Drift Manager Tool)
