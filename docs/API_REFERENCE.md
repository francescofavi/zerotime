# API Reference - Zerotime

## Purpose

Detailed API documentation for all public classes, methods, and functions in Zerotime.

## Scope

Covers all public API surface: classes (`Rule`, `AtomicRule`, `CombinedRule`), configuration (`RuleConfig`), exceptions, DSL syntax, and module-level functions. Does not cover internal/private implementation details. For a high-level overview, see the [README](../README.md).

---

## Table of Contents

1. [DSL Syntax](#dsl-syntax)
2. [Configuration](#configuration)
3. [Rule Classes](#rule-classes)
   - [Rule (Abstract Base)](#rule-abstract-base)
   - [AtomicRule](#atomicrule)
   - [CombinedRule](#combinedrule)
4. [Exceptions](#exceptions)
5. [Configuration Functions](#configuration-functions)

---

## DSL Syntax

All temporal fields in `AtomicRule` accept string expressions using a Domain-Specific Language. The DSL supports several constructs that can be combined.

### Single Value

Matches exactly one value.

```
"15"    → matches 15
"0"     → matches 0
```

### Range

Matches all values from start to end (inclusive).

```
"1..12"   → matches 1, 2, 3, ..., 12
"9..17"   → matches 9, 10, 11, ..., 17
```

### Range with Step

Matches values in a range at regular intervals.

```
"0..59/15"  → matches 0, 15, 30, 45
"1..31/7"   → matches 1, 8, 15, 22, 29
```

### Global Step

Matches all multiples of the step value within the field's valid range. For fields starting at 0 (hours, minutes, seconds), starts from 0. For fields starting at 1 (months, days, weekdays), starts from the first multiple >= 1.

```
"/5"   → for minutes (0-59): matches 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55
"/15"  → for minutes (0-59): matches 0, 15, 30, 45
"/5"   → for months (1-12): matches 5, 10 (first multiple of 5 >= 1 is 5)
"/3"   → for months (1-12): matches 3, 6, 9, 12
```

### List

Comma-separated values or expressions.

```
"1,15,31"       → matches 1, 15, 31
"1..5,10..15"   → matches 1-5 and 10-15
"9,12,17"       → matches 9, 12, 17
```

### Exclusion

Prefix with `!` to exclude values from the set. If no inclusions are specified, starts with full range.

```
"1..12,!7,!8"   → all months except July and August
"!6,!7"         → all values except 6 and 7 (full range minus exclusions)
```

### Negative Days (Days Field Only)

Negative values count from the end of the month. Only valid in the `days` field.

```
"-1"    → last day of month (28, 29, 30, or 31 depending on month)
"-2"    → second-to-last day
"-7"    → seventh-to-last day
```

### Field Ranges

| Field | Valid Range | Description |
|-------|-------------|-------------|
| `months` | 1-12 | January=1, December=12 |
| `days` | 1-31 or -1 to -31 | Day of month; negative counts from end |
| `weekdays` | 1-7 | Monday=1, Sunday=7 |
| `hours` | 0-23 | 24-hour format |
| `minutes` | 0-59 | |
| `seconds` | 0-59 | |

---

## Configuration

### RuleConfig

Dataclass controlling global behavior limits and defaults.

```python
@dataclass
class RuleConfig:
    max_years_search: int = 5
    max_generate_items: int | None = None
    max_json_size: int = 1_000_000
    max_recursion_depth: int = 100
    default_batch_size: int = 10_000
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_years_search` | `int` | `5` | Maximum years to search forward/backward in `get_next()`/`get_prev()`. Must be positive. |
| `max_generate_items` | `int \| None` | `None` | Maximum items `generate()` will yield before raising `ValueError`. `None` means unlimited. |
| `max_json_size` | `int` | `1000000` | Maximum JSON string size in bytes for `from_json()`. Prevents denial-of-service from large payloads. |
| `max_recursion_depth` | `int` | `100` | Maximum nesting depth for combined rules in JSON deserialization. |
| `default_batch_size` | `int` | `10000` | Default batch size for `generate_batch()` when not explicitly specified. |

#### Validation

All numeric parameters must be positive. `max_generate_items` may be `None`. Invalid values raise `ValueError` during construction.

#### Example

```python
from zerotime import RuleConfig, set_global_config

# Restrictive config for production
config = RuleConfig(
    max_years_search=2,
    max_generate_items=10000,
    max_json_size=100000
)
set_global_config(config)
```

---

## Rule Classes

### Rule (Abstract Base)

Abstract base class defining the interface for all rules. Cannot be instantiated directly.

#### Methods

##### `get_next(base, max_years=None) -> datetime`

Find the next datetime matching this rule after `base`.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `base` | `datetime` | Yes | Reference datetime to search from |
| `max_years` | `int \| None` | No | Override config's `max_years_search` |

**Returns:** `datetime` - The next matching datetime after `base`

**Raises:**
- `NoMatchFoundError` - No match found within the search range
- `ValueError` - If rule has timezone but `base` is naive

**Examples:**

```python
# Simple: find next match from now
next_dt = rule.get_next(datetime.now())

# With custom search range
next_dt = rule.get_next(base_date, max_years=10)
```

##### `get_prev(base, max_years=None) -> datetime`

Find the previous datetime matching this rule before `base`.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `base` | `datetime` | Yes | Reference datetime to search from |
| `max_years` | `int \| None` | No | Override config's `max_years_search` |

**Returns:** `datetime` - The previous matching datetime before `base`

**Raises:**
- `NoMatchFoundError` - No match found within the search range
- `ValueError` - If rule has timezone but `base` is naive

**Example:**

```python
# Find most recent match before a date
prev_dt = rule.get_prev(datetime(2025, 6, 1))
```

##### `generate(start, end) -> Generator[datetime, None, None]`

Generate all datetimes matching this rule between `start` and `end` (inclusive).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `start` | `datetime` | Yes | Start of range (inclusive) |
| `end` | `datetime` | Yes | End of range (inclusive) |

**Yields:** `datetime` objects in chronological order

**Raises:**
- `ValueError` - If `start > end` or if max_generate_items exceeded

**Example:**

```python
# Generate all matches in January
start = datetime(2025, 1, 1)
end = datetime(2025, 1, 31, 23, 59, 59)

for dt in rule.generate(start, end):
    print(dt)
```

##### `generate_reverse(start, end) -> Generator[datetime, None, None]`

Generate all datetimes matching this rule between `start` and `end` in **reverse chronological order**.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `start` | `datetime` | Yes | Start of range (inclusive) |
| `end` | `datetime` | Yes | End of range (inclusive) |

**Yields:** `datetime` objects in reverse chronological order (latest first)

**Raises:**
- `ValueError` - If `start > end` or if max_generate_items exceeded

**Example:**

```python
# Get most recent matches first
for dt in rule.generate_reverse(start, end):
    print(dt)  # Latest matches first
```

**Note:** This method is used internally by `get_prev()` for efficient backward search.

##### `generate_batch(start, end, batch_size=None) -> Generator[list[datetime], None, None]`

Generate datetimes in batches for memory-efficient processing of large ranges.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `start` | `datetime` | Yes | Start of range (inclusive) |
| `end` | `datetime` | Yes | End of range (inclusive) |
| `batch_size` | `int \| None` | No | Items per batch. `None` uses config default. |

**Yields:** Lists of datetime objects

**Example:**

```python
# Process in batches of 1000
for batch in rule.generate_batch(start, end, batch_size=1000):
    db.bulk_insert(batch)
```

##### `to_json() -> str`

Serialize rule to JSON string.

**Returns:** JSON string representation

**Example:**

```python
json_str = rule.to_json()
# Store in database, file, etc.
```

##### `Rule.from_json(json_str) -> Rule` (Static)

Deserialize rule from JSON string. Automatically detects rule type (atomic or combined).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `json_str` | `str` | Yes | JSON string to deserialize |

**Returns:** `AtomicRule` or `CombinedRule` instance

**Raises:**
- `ValueError` - Invalid JSON, unknown rule type, or exceeds size limit

**Example:**

```python
from zerotime import Rule

rule = Rule.from_json(stored_json)
```

#### Operators

##### `rule1 + rule2` (Union)

Returns a `CombinedRule` matching when **either** rule matches.

```python
weekends = saturday_rule + sunday_rule
```

##### `rule1 & rule2` (Intersection)

Returns a `CombinedRule` matching only when **both** rules match.

```python
# First Monday of each month
first_week = AtomicRule(days="1..7")
mondays = AtomicRule(weekdays="1")
first_monday = first_week & mondays
```

##### `rule1 - rule2` (Difference)

Returns a `CombinedRule` matching when the first rule matches but the second does not.

```python
working_hours = business_hours - lunch_break
```

---

### AtomicRule

Fundamental rule type based on temporal constraints.

#### Constructor

```python
AtomicRule(
    months: str = "1..12",
    days: str = "1..31",
    weekdays: str = "1..7",
    hours: str = "0..23",
    minutes: str = "0..59",
    seconds: str = "0..59",
    timezone: timezone | None = None
)
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `months` | `str` | `"1..12"` | Month constraint (1-12) |
| `days` | `str` | `"1..31"` | Day constraint (1-31, negative allowed) |
| `weekdays` | `str` | `"1..7"` | Weekday constraint (1=Mon, 7=Sun) |
| `hours` | `str` | `"0..23"` | Hour constraint (0-23) |
| `minutes` | `str` | `"0..59"` | Minute constraint (0-59) |
| `seconds` | `str` | `"0..59"` | Second constraint (0-59) |
| `timezone` | `timezone \| None` | `None` | Optional timezone binding |

**Raises:**
- `InvalidRuleError` - Invalid DSL expression in any field

**Semantics:** A datetime matches if ALL constraints are satisfied (AND logic).

**Examples:**

```python
# Every day at midnight
midnight = AtomicRule(hours="0", minutes="0", seconds="0")

# Weekdays at 9 AM
workday_start = AtomicRule(
    weekdays="1..5",
    hours="9",
    minutes="0",
    seconds="0"
)

# Last day of each quarter
quarter_end = AtomicRule(
    months="3,6,9,12",
    days="-1",
    hours="23",
    minutes="59",
    seconds="59"
)

# With timezone
from datetime import UTC
utc_rule = AtomicRule(hours="12", timezone=UTC)
```

#### Methods

Inherits all methods from `Rule`. Additionally:

##### `generate(start, end, max_items=None) -> Generator[datetime, None, None]`

Extended signature with optional `max_items` parameter.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `start` | `datetime` | Yes | Start of range |
| `end` | `datetime` | Yes | End of range |
| `max_items` | `int \| None` | No | Override config's `max_generate_items` |

##### `generate_reverse(start, end, max_items=None) -> Generator[datetime, None, None]`

Extended signature with optional `max_items` parameter.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `start` | `datetime` | Yes | Start of range |
| `end` | `datetime` | Yes | End of range |
| `max_items` | `int \| None` | No | Override config's `max_generate_items` |

##### `with_months(months) -> AtomicRule`

Return new rule with updated months constraint.

```python
q1_rule = base_rule.with_months("1,2,3")
```

##### `with_days(days) -> AtomicRule`

Return new rule with updated days constraint.

```python
last_day = base_rule.with_days("-1")
```

##### `with_weekdays(weekdays) -> AtomicRule`

Return new rule with updated weekdays constraint.

```python
weekend = base_rule.with_weekdays("6,7")
```

##### `with_hours(hours) -> AtomicRule`

Return new rule with updated hours constraint.

```python
morning = base_rule.with_hours("6..11")
```

##### `with_minutes(minutes) -> AtomicRule`

Return new rule with updated minutes constraint.

```python
quarter_hour = base_rule.with_minutes("/15")
```

##### `with_seconds(seconds) -> AtomicRule`

Return new rule with updated seconds constraint.

```python
on_the_minute = base_rule.with_seconds("0")
```

##### `with_timezone(tz) -> AtomicRule`

Return new rule with updated timezone.

```python
from datetime import timezone, timedelta

est = timezone(timedelta(hours=-5))
eastern_rule = utc_rule.with_timezone(est)
```

##### `AtomicRule.from_json(json_str) -> AtomicRule` (Static)

Deserialize specifically as AtomicRule.

**Raises:**
- `ValueError` - If JSON doesn't represent an atomic rule

---

### CombinedRule

Rule created by combining two rules with an operator. Usually created via operators (`+`, `&`, `-`), not directly.

#### Constructor

```python
CombinedRule(left: Rule, right: Rule, operator: str)
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `left` | `Rule` | Yes | First rule |
| `right` | `Rule` | Yes | Second rule |
| `operator` | `str` | Yes | One of: `"union"`, `"intersection"`, `"difference"` |

**Raises:**
- `ValueError` - Invalid operator
- `InvalidRuleError` - Timezone mismatch (combining tz-aware rule with tz-naive rule)

**Example:**

```python
# Equivalent ways to create union
combined = rule1 + rule2
combined = CombinedRule(rule1, rule2, "union")
```

#### Methods

Inherits all methods from `Rule`.

##### `CombinedRule.from_json(json_str, _depth=0) -> CombinedRule` (Static)

Deserialize specifically as CombinedRule.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `json_str` | `str` | Yes | JSON string |
| `_depth` | `int` | No | Internal recursion counter (do not use) |

---

## Exceptions

### RecurrentError

Base exception for all Zerotime errors.

```python
class RecurrentError(Exception):
    pass
```

### InvalidExpressionError

Raised when DSL expression parsing fails.

```python
class InvalidExpressionError(RecurrentError):
    pass
```

**Common causes:**
- Value outside valid range (`"13"` for months)
- Invalid syntax (`"1...5"`, `"abc"`)
- Empty expression
- All values excluded

### InvalidRuleError

Raised when rule construction fails due to invalid expressions.

```python
class InvalidRuleError(RecurrentError):
    pass
```

### NoMatchFoundError

Raised when `get_next()` or `get_prev()` finds no match within the search range.

```python
class NoMatchFoundError(RecurrentError):
    pass
```

---

## Configuration Functions

### get_config() -> RuleConfig

Get the current global configuration.

```python
from zerotime import get_config

config = get_config()
print(config.max_years_search)  # 5
```

### set_global_config(config: RuleConfig) -> None

Set the global configuration.

```python
from zerotime import RuleConfig, set_global_config

set_global_config(RuleConfig(max_years_search=10))
```

### reset_config() -> None

Reset global configuration to defaults.

```python
from zerotime import reset_config

reset_config()
```

---

## Timezone Handling

When a rule has a timezone:

1. **Input datetimes must be timezone-aware.** Passing a naive datetime raises `ValueError`.

2. **Input datetimes are converted** to the rule's timezone before matching.

3. **Generated datetimes have the rule's timezone** attached.

```python
from datetime import datetime, UTC, timezone, timedelta

# Rule in UTC
utc_rule = AtomicRule(hours="12", minutes="0", seconds="0", timezone=UTC)

# Must use timezone-aware datetime
now = datetime.now(UTC)
next_noon = utc_rule.get_next(now)
print(next_noon.tzinfo)  # UTC

# This raises ValueError:
# utc_rule.get_next(datetime.now())  # naive datetime!
```

Rules without timezone accept both naive and timezone-aware datetimes, returning datetimes with the same timezone awareness as the input.

---

## DST Handling

When using timezone-aware rules with `ZoneInfo` timezones (from the `zoneinfo` module), zerotime properly handles Daylight Saving Time transitions:

### Spring Forward (Gap)

During spring forward, certain local times don't exist (e.g., 02:30 when clocks jump from 02:00 to 03:00). Zerotime automatically **skips non-existent times**.

```python
from zoneinfo import ZoneInfo

rome = ZoneInfo("Europe/Rome")
# In 2024, Rome springs forward on March 31 at 02:00 -> 03:00
rule = AtomicRule(
    months="3",
    days="31",
    hours="2",
    minutes="30",
    seconds="0",
    timezone=rome
)

# 02:30 doesn't exist on 2024-03-31 in Rome
# generate() will skip this time silently
```

### Fall Back (Ambiguous)

During fall back, certain local times occur twice. Zerotime uses the **first occurrence** (fold=0).

### Detection Method

Non-existent times are detected via UTC round-trip: the datetime is converted to UTC and back. If the local time changes, the original time didn't exist.

---

## Thread Safety

Zerotime is designed for concurrent use:

- **Rule instances** are effectively immutable after construction
- **Parsed field caches** use double-checked locking with `threading.Lock`
- **Configuration** uses `contextvars.ContextVar` for proper inheritance to child threads and async tasks

```python
import threading
from zerotime import AtomicRule

# Safe to share across threads
rule = AtomicRule(hours="9", minutes="0", seconds="0")

def worker():
    next_dt = rule.get_next(datetime.now())
    # ...

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
```
