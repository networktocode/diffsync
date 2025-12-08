# v1.1 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## [v1.1.0] - 2020-12-01

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

