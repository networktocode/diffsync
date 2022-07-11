# Changelog

## v1.6.0 - 2022-07-09

### Changed

- #120 - Dropped support for Python 3.6, new minimum is Python 3.7

## v1.5.1 - 2022-06-30

### Added

- #111 - Added example 6, regarding IP prefixes.

### Changed

- #107 - Updated example 5 to use the Redis backend store.

### Fixed

- #115 - Fixed ReadTheDocs rendering pipeline
- #118 - Fixed a regression in `DiffSync.get(modelname, identifiers)` introduced in 1.5.0

## v1.5.0 - 2022-06-07

### Added

- #106 - Add a new, optional, backend store based in Redis

## v1.4.3 - 2022-03-03

### Fixed

- #101 - Revert changed introduced in #90 that affected `DiffElement.action`

**NOTE**: this change is a breaking change against DiffSync 1.4.0 through 1.4.2, but was necessary to restore backward compatibility with DiffSync 1.3.x and earlier. Apologies for any inconvenience this causes.

### Changed

- #103 Update development dependencies

## v1.4.2 - 2022-02-28

**WARNING** - #90 inadvertently introduced a breaking API change in DiffSync 1.4.0 through 1.4.2 (#101); this change was reverted in #102 for DiffSync 1.4.3 and later. We recommend not using this release, and moving to 1.4.3 instead.

### Fixed

- #100 - Added explicit dependency on `packaging`.

## v1.4.1 - 2022-01-26

**WARNING** - #90 inadvertently introduced a breaking API change in DiffSync 1.4.0 through 1.4.2 (#101); this change was reverted in #102 for DiffSync 1.4.3 and later. We recommend not using this release, and moving to 1.4.3 instead.

### Fixed

- #95 - Removed optional dependencies on `sphinx`, `m2r2`, `sphinx-rtd-theme`, `toml`.

## v1.4.0 - 2022-01-24

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

## v1.3.0 - 2021-04-07

### Added

- #48 - added optional `callback` argument to `diff_from`/`diff_to`/`sync_from`/`sync_to` for use with progress reporting.

## v1.2.0 - 2020-12-08

### Added

- #45 - minimum Python version lowered from 3.7 to 3.6, also now tested against Python 3.9.

## v1.1.0 - 2020-12-01

### Added

- #37 - added `sync_complete` callback, triggered on `sync_from` completion with changes.
- #41 - added `summary` API for Diff and DiffElement objects.
- #44 - added `set_status()` and `get_status()` APIs so that DiffSyncModel implementations can provide details for create/update/delete logging

### Changed

- Now requires Pydantic 1.7.2 or later
- #34 - in diff dicts, changed keys `src`/`dst`/`_src`/`_dst` to `-` and `+`
- #43 - `DiffSync.get_by_uids()` now raises `ObjectNotFound` if any of the provided uids cannot be located; `DiffSync.get()` raises `ObjectNotFound` or `ValueError` on failure, instead of returning `None`.

### Fixed

- #44 - On CRUD failure, do not generate an extraneous "success" log message in addition to the "failed" message

## v1.0.0 - 2020-10-23

Initial release
