# Changelog

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
