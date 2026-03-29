# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.1]: https://github.com/francescofavi/zerotime/releases/tag/v0.1.1
[0.1.0]: https://github.com/francescofavi/zerotime/releases/tag/v0.1.0
