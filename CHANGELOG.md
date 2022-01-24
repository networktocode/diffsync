# Changelog

## v1.4.0 - 2022-01-24

### Added

- #83 - Add support for Python 3.10
- #59 - Add proper documentation published in Read the doc
- #70 - Add `add_or_update()` method to DiffSync class that requires a DiffSyncModel to be passed in and will attempt to add or update an existing object
- #80 - Add support for an existing Diff object to be passed to `sync_to()` & `sync_from()` to prevent another diff from being calculated.
- #87 - Add new model flags : `SKIP_UNMATCHED_BOTH`, `SKIP_UNMATCHED_SRC` & `SKIP_UNMATCHED_DST` to match the behavior of the global flags
- #81 - Add a new example based on PeeringDB
- #53 - Add a new example based on pynautobot and Nautobot REST API
- #75 - Add support for Structlog v21 in addition to v20.

### Changed

- #69 - Replace Travis CI with Github Actions to run unit tests
- #43 - `get()` and `get_by_uids()` now raises an `ObjectNotFound` exception, instead of silently skipping over unmatched uids
- #90 - Convert list of actions (`create`, `update`, `delete`) to proper Enum
- #82 - Update lock file with latest versions.

### Fixed

- #51 - Update minimum Pydantic version due to security advisory GHSA-5jqp-qgf6-3pvh

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
