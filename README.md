<p align="center">
  <img src="https://raw.githubusercontent.com/francescofavi/zerotime/main/logo.png" alt="Zerotime Logo" width="200">
</p>

# Zerotime

[![CI](https://github.com/francescofavi/zerotime/actions/workflows/ci.yml/badge.svg)](https://github.com/francescofavi/zerotime/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/zerotime.svg)](https://pypi.org/project/zerotime/)
[![Python](https://img.shields.io/pypi/pyversions/zerotime.svg)](https://pypi.org/project/zerotime/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/pypi/status/zerotime.svg)](https://pypi.org/project/zerotime/)
[![Typed](https://img.shields.io/badge/typed-yes-blue.svg)](https://peps.python.org/pep-0561/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](https://github.com/francescofavi/zerotime)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)

A Python datetime rule engine for defining and working with recurring time patterns. Zerotime lets you express complex scheduling rules declaratively using a simple DSL (Domain-Specific Language), then query for matching datetimes, generate sequences, or combine rules using set operations.

## Why Zerotime?

Working with recurring events in datetime is surprisingly complex. You might need "every Monday at 9 AM", "the last day of each month", or "business hours except lunch break". Traditional approaches involve writing custom logic for each pattern, handling edge cases like leap years, varying month lengths, and weekday calculations.

Zerotime solves this by providing a unified `Rule` abstraction. Rules can be atomic (based on month, day, hour constraints) or combined using operators (`+` for union, `&` for intersection, `-` for difference). The library handles all the complexity of calendar math internally, provides memory-efficient generation of large date ranges, and includes JSON serialization for persistence.

## Technical Design

Zerotime uses **only the Python standard library** (no external dependencies). The core design principles:

- **Declarative DSL**: Each temporal field (months, days, weekdays, hours, minutes, seconds) accepts string expressions like `"1..5"` (range), `"/15"` (step), `"1,15,-1"` (list with last-day), or `"1..12,!7,!8"` (exclusions)
- **Composable Rules**: Rules combine via Python operators, enabling complex schedules from simple building blocks
- **Lazy Generation**: The `generate()` method yields datetimes on demand, suitable for large date ranges
- **Immutable Rules**: All `with_*` methods return new rule instances; original rules are never modified
- **Timezone Support**: Rules optionally bind to a timezone, with proper DST handling and validation of timezone-aware vs naive datetimes
- **Thread Safety**: Parsed expressions are cached with double-checked locking for safe concurrent use

## Components Overview

The library consists of three main components:

- **AtomicRule**: The fundamental building block. Defines temporal constraints using DSL expressions for each datetime field. All constraints must match (AND logic).

- **CombinedRule**: Created by combining two rules with an operator. Supports union (either matches), intersection (both match), and difference (first matches but not second).

- **RuleConfig**: Global configuration controlling search limits, generation caps, JSON size limits, and batch sizes for memory-efficient processing.

## Usage Example

Here's a realistic example showing how to define business working hours excluding lunch breaks and holidays:

```python
from datetime import datetime, UTC
from zerotime import AtomicRule

# Business hours: weekdays 9-17, on the hour
business_hours = AtomicRule(
    weekdays="1..5",        # Monday to Friday
    hours="9..17",          # 9 AM to 5 PM
    minutes="0",            # On the hour
    seconds="0",
    timezone=UTC
)

# Lunch break: 12-13
lunch_break = AtomicRule(
    weekdays="1..5",
    hours="12,13",
    minutes="0",
    seconds="0",
    timezone=UTC
)

# Working hours = business hours minus lunch
working_hours = business_hours - lunch_break

# Find the next working hour from now
now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
next_slot = working_hours.get_next(now)
print(f"Next working hour: {next_slot}")  # 2025-01-15 11:00:00+00:00

# Generate all working hours for a day
start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=UTC)
end = datetime(2025, 1, 15, 23, 59, 59, tzinfo=UTC)
for dt in working_hours.generate(start, end):
    print(dt)
# Output: 09:00, 10:00, 11:00, 14:00, 15:00, 16:00, 17:00

# Serialize for storage
json_str = working_hours.to_json()

# Restore later
from zerotime import Rule
restored = Rule.from_json(json_str)
```

## Main APIs

### AtomicRule

Creates rules from temporal constraints. Each field uses DSL syntax.

**Simple usage** - every day at noon:
```python
rule = AtomicRule(hours="12", minutes="0", seconds="0")
```

**Complex usage** - quarterly reports on the last business day:
```python
rule = AtomicRule(
    months="3,6,9,12",      # End of quarter
    days="-1,-2,-3",        # Last 3 days (will pick based on weekday)
    weekdays="1..5",        # Must be a weekday
    hours="17",
    minutes="0",
    seconds="0"
)
```

### Rule Operators

Combine rules using Python operators:

```python
# Union: matches if either rule matches
holidays = rule1 + rule2

# Intersection: matches only if both rules match
overlap = rule1 & rule2

# Difference: matches first rule but not second
working_days = all_days - holidays
```

### Temporal Navigation

Find next/previous matching datetime:

```python
# Simple - find next match
next_match = rule.get_next(datetime.now())

# Complex - search up to 10 years ahead
next_match = rule.get_next(base_date, max_years=10)
```

### Generation

Generate all matching datetimes in a range:

```python
# Simple - iterate all matches
for dt in rule.generate(start, end):
    process(dt)

# Memory-efficient - process in batches
for batch in rule.generate_batch(start, end, batch_size=1000):
    bulk_process(batch)
```

### Configuration

Adjust global limits:

```python
from zerotime import RuleConfig, set_global_config

config = RuleConfig(
    max_years_search=10,        # How far to search in get_next/get_prev
    max_generate_items=100000,  # Cap on generated items (None = unlimited)
    default_batch_size=5000     # Batch size for generate_batch
)
set_global_config(config)
```

## DSL Syntax Reference

| Syntax | Meaning | Example |
|--------|---------|---------|
| `"N"` | Single value | `"15"` - day 15 |
| `"N..M"` | Range (inclusive) | `"1..5"` - Mon-Fri |
| `"N..M/S"` | Range with step | `"0..59/15"` - 0,15,30,45 |
| `"/S"` | Global step (multiples of S) | `"/15"` - 0,15,30,45 for minutes |
| `"A,B,C"` | List | `"1,15,-1"` - 1st, 15th, last |
| `"!N"` | Exclusion | `"1..12,!7,!8"` - all except Jul,Aug |
| `"-N"` | Negative (days only) | `"-1"` - last day of month |

## Installation

```bash
pip install zerotime
```

**Requirements:**
- Python 3.11+
- No external dependencies (standard library only)

## Running Tests

```bash
uv run pytest
```

With coverage:

```bash
uv run pytest --cov=zerotime --cov-report=term-missing
```

## Examples

The `examples/` directory contains comprehensive, runnable examples covering all features:

| File | Description |
|------|-------------|
| `01_basic_usage.py` | Introduction to AtomicRule, get_next, get_prev |
| `02_dsl_syntax.py` | Complete DSL reference with all syntax patterns |
| `03_rule_combination.py` | Combining rules with +, &, - operators |
| `04_generation_methods.py` | generate(), generate_reverse(), generate_batch() |
| `05_navigation.py` | Temporal navigation and error handling |
| `06_timezones.py` | Timezone handling including DST transitions |
| `07_configuration.py` | RuleConfig and global settings |
| `08_json_serialization.py` | Saving and restoring rules with JSON |
| `09_builder_methods.py` | Immutable rule modification with with_* methods |
| `10_real_world_examples.py` | Practical use cases: billing, scheduling, SLA, maintenance windows |

Run any example directly:

```bash
python examples/01_basic_usage.py
```

## Further Documentation

- [Full API Reference](https://github.com/francescofavi/zerotime/blob/main/docs/API_REFERENCE.md)
- [Functional Analysis](https://github.com/francescofavi/zerotime/blob/main/docs/FUNCTIONAL_ANALYSIS.md)
- [Architecture](https://github.com/francescofavi/zerotime/blob/main/docs/ARCHITECTURE.md)
- [Anti-Patterns](https://github.com/francescofavi/zerotime/blob/main/docs/ANTI_PATTERNS.md)
- [Development](https://github.com/francescofavi/zerotime/blob/main/docs/DEVELOPMENT.md)
- [Examples README](https://github.com/francescofavi/zerotime/blob/main/examples/README.md)

## License

[MIT License](https://github.com/francescofavi/zerotime/blob/main/LICENSE) - Copyright (c) 2025 Francesco Favi
