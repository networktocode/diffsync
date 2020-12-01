# Changelog

## Unreleased

- Now requires Pydantic 1.7.2 or later

- Added `set_status()` API so that DiffSyncModel implementations can provide details for create/update/delete logging
- `DiffSync.get_by_uids()` now raises `ObjectNotFound` if any of the provided uids cannot be located.
- `DiffSync.get()` raises `ObjectNotFound` or `ValueError` on failure, instead of returning `None`.
- #34 - in diff dicts, change keys `src`/`dst`/`_src`/`_dst` to `-` and `+`
- #37 - add `sync_complete` callback, triggered on `sync_from` completion with changes.
- #41 - add `summary` API for Diff and DiffElement objects.

## v1.0.0 - 2020-10-23

Initial release
