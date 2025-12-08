# v1.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## [v1.4.3] - 2022-03-03

### Fixed

- #101 - Revert changed introduced in #90 that affected `DiffElement.action`

**NOTE**: this change is a breaking change against DiffSync 1.4.0 through 1.4.2, but was necessary to restore backward compatibility with DiffSync 1.3.x and earlier. Apologies for any inconvenience this causes.

### Changed

- #103 - Update development dependencies

## [v1.4.2] - 2022-02-28

**WARNING** - #90 inadvertently introduced a breaking API change in DiffSync 1.4.0 through 1.4.2 (#101); this change was reverted in #102 for DiffSync 1.4.3 and later. We recommend not using this release, and moving to 1.4.3 instead.

### Fixed

- #100 - Added explicit dependency on `packaging`.

## [v1.4.1] - 2022-01-26

**WARNING** - #90 inadvertently introduced a breaking API change in DiffSync 1.4.0 through 1.4.2 (#101); this change was reverted in #102 for DiffSync 1.4.3 and later. We recommend not using this release, and moving to 1.4.3 instead.

### Fixed

- #95 - Removed optional dependencies on `sphinx`, `m2r2`, `sphinx-rtd-theme`, `toml`.

## [v1.4.0] - 2022-01-24

**WARNING** - #90 inadvertently introduced a breaking API change in DiffSync 1.4.0 through 1.4.2 (#101); this change was reverted in #102 for DiffSync 1.4.3 and later. We recommend not using this release, and moving to 1.4.3 instead.

### Added

- #53 - Add a new example based on pynautobot and Nautobot REST API
- #59 - Add proper documentation published in Read the doc
- #68 - Cleanup Readme, add link to new documentation site
- #70 - Add `add_or_update()` method to DiffSync class that requires a DiffSyncModel to be passed in and will attempt to add or update an existing object
- #72 - Add core engine section in docs and rename example directories
- #75 - Add support for Structlog v21 in addition to v20.
- #80 - Add support for an existing Diff object to be passed to `sync_to()` & `sync_from()` to prevent another diff from being calculated.
- #81 - Add a new example based on PeeringDB
- #83 - Add support for Python 3.10
- #87 - Add new model flags : `SKIP_UNMATCHED_BOTH`, `SKIP_UNMATCHED_SRC` & `SKIP_UNMATCHED_DST` to match the behavior of the global flags

### Changed

- #62 - Update CI Token
- #69 - Replace Travis CI with Github Actions to run unit tests
- #82 - Update lock file with latest versions.
- #90 - Convert list of actions (`create`, `update`, `delete`) to proper Enum

### Fixed

- #51 - Update minimum Pydantic version due to security advisory GHSA-5jqp-qgf6-3pvh
- #63 - Fix type in Readme
