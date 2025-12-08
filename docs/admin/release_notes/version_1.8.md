# v1.8 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## [v1.8.0] - 2023-04-18

### Added

- #182 - Added `get_or_add_model_instance()` and `update_or_add_model_instance()` APIs.
- #189 - Added note in `README.md` about running `invoke tests`.
- #190 - Added note in `README.md` about running `invoke build`.

### Changed

- #77/#188 - `sync_from()` and `sync_to()` now return the `Diff` that was applied.
- #211 - Loosened `packaging` and `structlog` library dependency constraints for broader compatibility.
