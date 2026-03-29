# Zerotime Examples

This directory contains comprehensive examples demonstrating all features of the zerotime library.

## Examples Overview

| File | Description |
|------|-------------|
| `01_basic_usage.py` | Introduction to AtomicRule - creating rules, get_next, get_prev |
| `02_dsl_syntax.py` | Complete DSL reference - ranges, steps, lists, exclusions, negative days |
| `03_rule_combination.py` | Combining rules with union (+), intersection (&), difference (-) |
| `04_generation_methods.py` | Using generate(), generate_reverse(), generate_batch() |
| `05_navigation.py` | Temporal navigation with get_next() and get_prev() |
| `06_timezones.py` | Timezone handling including DST transitions |
| `07_configuration.py` | RuleConfig for controlling library behavior |
| `08_json_serialization.py` | Saving and restoring rules with JSON |
| `09_builder_methods.py` | Using with_* methods for immutable rule modification |
| `10_real_world_examples.py` | Practical use cases (billing, scheduling, SLA, etc.) |

## Running Examples

Each example is self-contained and can be run directly:

```bash
cd examples
python 01_basic_usage.py
python 02_dsl_syntax.py
# ... etc
```

Or run all examples:

```bash
for f in examples/*.py; do echo "=== $f ===" && python "$f" && echo; done
```

## Quick Reference

### Creating Rules

```python
from datetime import UTC
from zerotime import AtomicRule

# Simple rule
rule = AtomicRule(hours="9", minutes="0", seconds="0", timezone=UTC)

# Complex rule with DSL
rule = AtomicRule(
    months="1..12,!7,!8",   # All except July, August
    days="1,15,-1",          # 1st, 15th, last day
    weekdays="1..5",         # Monday-Friday
    hours="9..17",           # 9 AM - 5 PM
    minutes="/15",           # Every 15 minutes
    seconds="0",
    timezone=UTC,
)
```

### Combining Rules

```python
# Union: matches either
weekends = saturday + sunday

# Intersection: matches both
friday_13th = fridays & day_13

# Difference: matches first but not second
working_hours = business_hours - lunch
```

### Querying

```python
# Next occurrence
next_match = rule.get_next(datetime.now(UTC))

# Previous occurrence
prev_match = rule.get_prev(datetime.now(UTC))

# Generate range
for dt in rule.generate(start, end):
    print(dt)

# Reverse order
for dt in rule.generate_reverse(start, end):
    print(dt)
```

### Persistence

```python
# Save
json_str = rule.to_json()

# Load
rule = Rule.from_json(json_str)
```

## Feature Coverage

| Feature | Example File |
|---------|--------------|
| AtomicRule basics | 01, 02 |
| DSL syntax | 02 |
| Rule combination | 03 |
| generate() | 04 |
| generate_reverse() | 04 |
| generate_batch() | 04 |
| get_next() | 01, 05 |
| get_prev() | 01, 05 |
| Timezones | 06 |
| DST handling | 06 |
| RuleConfig | 07 |
| JSON serialization | 08 |
| Builder methods | 09 |
| Real-world patterns | 10 |
