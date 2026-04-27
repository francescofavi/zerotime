# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.0 (2026-04-27)


### Features

* initial release of zerotime datetime rule engine ([2a52c64](https://github.com/francescofavi/zerotime/commit/2a52c64de9265009e58b8a489462d1b9696f6ca2))


### Bug Fixes

* fix PyPI README badge rendering ([a5674e9](https://github.com/francescofavi/zerotime/commit/a5674e9ecf08501de2a2bcc6103f276a20df036b))


### Documentation

* add project logo to README ([13d2213](https://github.com/francescofavi/zerotime/commit/13d2213c8c596f7efd010c1fe3ad9db8c3655311))
* sync internal doc line references and LOC counts ([55863fb](https://github.com/francescofavi/zerotime/commit/55863fb9f21f90a3f1ec5da9d71d323950c28a16))

## [0.1.2] - 2026-03-30

### Changed

- Add README badges for status, typed, dependencies, and code style
- Fix shields.io badge URLs with .svg extension for PyPI rendering
- Convert relative links to absolute GitHub URLs for PyPI compatibility

## [0.1.1] - 2026-03-29

### Fixed

- Fix PyPI README badge rendering (relative LICENSE link replaced with absolute URL)

## [0.1.0] - 2026-03-29

### Added

- Initial release
- Core Rule engine for datetime patterns
- Atomic rules and combined rules
- DSL syntax for temporal constraints
- Rule combination operators (union, intersection, difference)
- Temporal navigation (get_next, get_prev)
- Lazy generation with batch support
- JSON serialization and deserialization
- Timezone and DST handling
- Comprehensive test suite
- Full type hints with py.typed marker

[0.1.2]: https://github.com/francescofavi/zerotime/releases/tag/v0.1.2
[0.1.1]: https://github.com/francescofavi/zerotime/releases/tag/v0.1.1
[0.1.0]: https://github.com/francescofavi/zerotime/releases/tag/v0.1.0
