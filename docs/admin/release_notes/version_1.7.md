# v1.7 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## [v1.7.0] - 2022-11-03

### Changed

- #176 - Remove pytest-redislite in favor of pytest-redis.
- #174 - Update Dockerfile to install build-essential

### Added

- #174 - Add methods to load data from dictionary and enable tree traversal
- #174 - Add a `get_or_none` method to the DiffSync class
- #168 - Add 'skip' counter to diff.summary()
- #169/#170 - Add documentation about model processing order
- #121/#140 - Add and configure renovate
- #140 - Add renovate configuration validation to the CI

### Fixed

- #149 - Limit redundant CI concurrency
