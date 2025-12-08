# v2.0 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

Major release with Pydantic v2 upgrade and subsequent bug fixes.

## [v2.0.0]

### Changed

- **BREAKING CHANGE** #236/240 - Upgrade to Pydantic v2.

## [v2.0.1]

### Changed

- #276 - Removed upper version bound for `structlog` dependency

### Fixed

- #281 - Properly deprecated `DiffSync` class name
- #273 - Properly capitalized `DiffSync` in documentation
- #273 - Removed more mentions of `DiffSync` in favor of `Adapter`
- #274 - Fixed doc section title for getting started
- #269 - Fixed wording for a couple of docstrings
- #265 - Fixed readthedocs build
