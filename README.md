<p align="center">
  <img src="https://raw.githubusercontent.com/francescofavi/zerotime/main/logo.png" alt="Zerotime Logo" width="200">
</p>

# Zerotime

[![CI](https://img.shields.io/github/actions/workflow/status/francescofavi/zerotime/ci.yml?branch=main&label=CI&cacheSeconds=0)](https://github.com/francescofavi/zerotime/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/zerotime.svg?cacheSeconds=0)](https://pypi.org/project/zerotime/)
[![Python versions](https://img.shields.io/pypi/pyversions/zerotime.svg?cacheSeconds=0)](https://pypi.org/project/zerotime/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?cacheSeconds=0)](https://github.com/francescofavi/zerotime/blob/main/LICENSE)
[![Status](https://img.shields.io/pypi/status/zerotime.svg?cacheSeconds=0)](https://pypi.org/project/zerotime/)
[![Typed](https://img.shields.io/badge/typed-PEP%20561-blue.svg?cacheSeconds=0)](https://peps.python.org/pep-0561/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg?cacheSeconds=0)]()
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?cacheSeconds=0)](https://docs.astral.sh/ruff/)

A Python datetime rule engine for defining and working with recurring time patterns. Zerotime lets you express complex scheduling rules declaratively using a simple DSL, then query for matching datetimes, generate sequences, or combine rules using set operations.

---

## Problem

Working with recurring events in datetime is harder than it looks. "Every Monday at 9 AM", "the last business day of each quarter", "business hours except lunch" — each one is a small puzzle that ends up as ad-hoc calendar math sprinkled across the codebase. The standard library gives you `datetime` and `timedelta`; everything beyond that — leap years, varying month lengths, weekday alignment, DST gaps, last-day-of-month — is on you.

Existing libraries either model a different problem (cron expressions, parsed but not composable; iCalendar RRULE, powerful but verbose and tied to the iCal format) or are heavy and stateful (full scheduling frameworks). What is missing is a small, dependency-free abstraction that treats *a recurring instant in time* as a first-class value: comparable, composable, serializable.

## Solution

Zerotime models recurring instants as **rules**. A rule answers one question: *"does this datetime match?"*. From that single predicate everything else derives — finding the next or previous match, generating sequences, combining rules with set operators.

Two rule kinds, one interface:

- `AtomicRule` — temporal constraints expressed in a string DSL, one constraint per datetime field. All constraints AND together.
- `CombinedRule` — two rules joined by a set operator (`+` union, `&` intersection, `-` difference). Combinations nest freely.

Both kinds share the `Rule` base, so any operation (`get_next`, `get_prev`, `generate`, `to_json`) works the same regardless of how the rule was built. The library has zero runtime dependencies, ships PEP 561 type information, and uses second-level resolution end-to-end.

## What it gives you

- **Declarative DSL** for each datetime field — values, ranges, steps, lists, exclusions, last-day-of-month negatives.
- **Composable rules** via Python operators — `union + intersection & difference -`, with arbitrary nesting.
- **Lazy generation** — `generate()` yields one datetime at a time, suitable for multi-year ranges.
- **Batched generation** — `generate_batch()` for memory-efficient bulk processing.
- **Temporal navigation** — `get_next()` / `get_prev()` find the nearest match in either direction.
- **Immutable builders** — every `with_*` method returns a new rule; originals are never mutated.
- **Timezone awareness** — optional timezone binding, DST gap handling, naive/aware mismatch detection.
- **JSON round-trip** — `to_json()` / `from_json()` for persistence, with size and depth caps.
- **Thread-safe** — parsed-field cache uses double-checked locking; configuration uses `ContextVar`.
- **Zero runtime dependencies** — standard library only.

## Installation

```bash
pip install zerotime
```

or

```bash
uv add zerotime
```

Requires Python 3.12+.

## Quick start

```python
from datetime import datetime, UTC
from zerotime import AtomicRule

# Business hours: weekdays, 09:00-17:00 on the hour
business_hours = AtomicRule(
    weekdays="1..5",
    hours="9..17",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Lunch break: 12:00 and 13:00
lunch_break = AtomicRule(
    weekdays="1..5",
    hours="12,13",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Working hours = business hours minus lunch
working_hours = business_hours - lunch_break

# Find the next working hour after a reference instant
ref = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
print(working_hours.get_next(ref))
# 2025-01-15 11:00:00+00:00

# Generate every working hour for a single day
day_start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=UTC)
day_end = datetime(2025, 1, 15, 23, 59, 59, tzinfo=UTC)
for dt in working_hours.generate(day_start, day_end):
    print(dt.strftime("%H:%M"))
# 09:00, 10:00, 11:00, 14:00, 15:00, 16:00, 17:00

# Persist and restore
from zerotime import Rule
restored = Rule.from_json(working_hours.to_json())
```

## DSL syntax

Each `AtomicRule` field accepts a string expression:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `"N"` | Single value | `"15"` — day 15 |
| `"N..M"` | Inclusive range | `"1..5"` — Mon to Fri |
| `"N..M/S"` | Range with step | `"0..59/15"` — 0, 15, 30, 45 |
| `"/S"` | Global step | `"/15"` for minutes — 0, 15, 30, 45 |
| `"A,B,C"` | List | `"1,15,-1"` — 1st, 15th, last day |
| `"!N"` | Exclusion | `"1..12,!7,!8"` — all months except July and August |
| `"-N"` | Negative day | `"-1"` — last day of month (days field only) |

Field ranges: `months 1-12`, `days 1-31` (or `-1..-31`), `weekdays 1-7` (Mon=1), `hours 0-23`, `minutes 0-59`, `seconds 0-59`.

## Comparison with alternatives

| Capability | Zerotime | `croniter` | `python-dateutil` (`rrule`) | `recurrent` |
|---|---|---|---|---|
| Pure-Python, stdlib only | yes | yes | no (`six`) | depends on dateutil |
| Set-operator composition (`+ & -`) | yes | no | no | no |
| Negative day-of-month (`-1` = last) | yes | no | partial (`bymonthday=-1`) | no |
| DSL exclusions (`!7`) | yes | no | no | no |
| Last-day / quarterly patterns out of the box | yes | manual | manual | partial |
| JSON round-trip | yes | no | no | no |
| Timezone-aware with DST gap handling | yes | partial | yes | partial |
| Sub-second resolution | no | no | yes | no |
| iCalendar RFC 5545 conformance | no | no | yes | partial |
| Cron-expression input | no | yes | no | no |

If you need cron expressions, use `croniter`. If you need RFC 5545 RRULE compatibility, use `python-dateutil`. Zerotime targets the gap in the middle: a small, composable, stdlib-only rule abstraction with set algebra.

## Known limits and open issues

A small library deliberately solves a small problem. The list below sets expectations up front.

- *limit:* second-level resolution; microseconds are ignored during matching.
- *limit:* year range bounded to `[1, 9999]`; outside that range, methods raise `ValueError`.
- *limit:* negative-day syntax is valid only in the `days` field.
- *limit:* JSON timezone round-trip preserves UTC offsets, not IANA zone names — DST-aware behavior may differ after deserialization.
- *design:* combining a tz-aware rule with a tz-naive rule is rejected at construction time (`InvalidRuleError`); no implicit promotion.
- *design:* `get_next`/`get_prev` search a bounded number of years (default 5) — set `max_years_search` higher when needed.
- *design:* `generate()` over very large ranges with no `max_generate_items` cap can produce unbounded output; use `generate_batch()` or set a cap.
- *open:* the library version in `src/zerotime/__init__.py` may lead the published `CHANGELOG.md` between releases.

## Anti-patterns — how NOT to use this project

A short cheat sheet of usages the library does not support; expanded examples live in [`docs/ANTI_PATTERNS.md`](https://github.com/francescofavi/zerotime/blob/main/docs/ANTI_PATTERNS.md).

- Do not pass a naive datetime to a rule that has a timezone — it raises `ValueError`.
- Do not combine a tz-aware rule with a tz-naive rule — it raises `InvalidRuleError`.
- Do not call `generate()` over multi-year ranges on a high-frequency rule without a cap or batches.
- Do not write a DSL expression that excludes every value in the field — it raises `InvalidExpressionError`.
- Do not use negative values (`"-1"`) outside the `days` field — only `days` accepts them.
- Do not mutate `_*_expr` attributes directly — use `with_*` builder methods.
- Do not assume IANA zone fidelity across `to_json`/`from_json` — only UTC offsets round-trip.
- Do not expect sub-second matching — Zerotime rounds to the second.

## Running tests

```bash
uv run pytest
```

With coverage:

```bash
uv run pytest --cov=zerotime --cov-report=term-missing
```

## Running examples

The `examples/` directory ships ten standalone scripts covering every public feature:

| File | Description |
|---|---|
| `01_basic_usage.py` | `AtomicRule`, `get_next`, `get_prev` |
| `02_dsl_syntax.py` | Every DSL form with one example each |
| `03_rule_combination.py` | `+`, `&`, `-` operators |
| `04_generation_methods.py` | `generate()`, `generate_reverse()`, `generate_batch()` |
| `05_navigation.py` | Temporal navigation and error handling |
| `06_timezones.py` | Timezone-aware rules and DST handling |
| `07_configuration.py` | `RuleConfig` and global settings |
| `08_json_serialization.py` | `to_json` / `from_json` round-trip |
| `09_builder_methods.py` | Immutable `with_*` builders |
| `10_real_world_examples.py` | Billing, scheduling, SLA, maintenance windows |

Run any example directly:

```bash
python examples/01_basic_usage.py
```

## Development

Contributor setup, quality pipeline, pre-commit hooks and release process live in [`docs/DEVELOPMENT.md`](https://github.com/francescofavi/zerotime/blob/main/docs/DEVELOPMENT.md).

## Documentation map

User documentation:

- [`README.md`](https://github.com/francescofavi/zerotime/blob/main/README.md) — this file.
- [`docs/ANTI_PATTERNS.md`](https://github.com/francescofavi/zerotime/blob/main/docs/ANTI_PATTERNS.md) — how NOT to use the library, with worked examples.

Developer documentation:

- [`docs/API_REFERENCE.md`](https://github.com/francescofavi/zerotime/blob/main/docs/API_REFERENCE.md) — every public symbol, verbatim signatures, parameters, raises.
- [`docs/ARCHITECTURE.md`](https://github.com/francescofavi/zerotime/blob/main/docs/ARCHITECTURE.md) — component map, data flow, design decisions.
- [`docs/DEVELOPMENT.md`](https://github.com/francescofavi/zerotime/blob/main/docs/DEVELOPMENT.md) — local setup, test/quality pipeline, commit conventions, release process.
- [`examples/README.md`](https://github.com/francescofavi/zerotime/blob/main/examples/README.md) — runnable examples index.

## Contributing

This repository is maintained as a personal portfolio project. Pull requests are generally not accepted, but exceptional contributions may be considered.

For bug reports and feature requests, please use [GitHub Issues](https://github.com/francescofavi/zerotime/issues).

## License

[MIT License](https://github.com/francescofavi/zerotime/blob/main/LICENSE) — Copyright (c) 2025 Francesco Favi.
