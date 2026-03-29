# Anti-Patterns - Zerotime

## Purpose

Documents common misuses and incorrect patterns when working with Zerotime, with correct alternatives.

## Scope

Covers usage-level anti-patterns. Does not cover internal implementation concerns.

---

## 1. Naive datetime with timezone-bound rule

**Description**: Passing a naive datetime (no `tzinfo`) to a rule that has a timezone set.

**Why wrong**: Zerotime cannot determine the intended timezone of the input. The call raises `ValueError` immediately.

**Correct approach**:

```python
# Wrong
rule = AtomicRule(hours="9", timezone=UTC)
rule.get_next(datetime(2025, 1, 1))  # ValueError

# Correct
rule.get_next(datetime(2025, 1, 1, tzinfo=UTC))
```

---

## 2. Mixing timezone-aware and timezone-naive rules in combination

**Description**: Combining a rule with a timezone and a rule without one using `+`, `&`, or `-`.

**Why wrong**: The combined rule cannot reconcile tz-aware and tz-naive generation. Raises `InvalidRuleError` at construction time.

**Correct approach**: Ensure both rules use the same timezone (or both use `None`).

```python
# Wrong
rule_a = AtomicRule(hours="9", timezone=UTC)
rule_b = AtomicRule(hours="12")  # no timezone
combined = rule_a + rule_b  # InvalidRuleError

# Correct
rule_b = AtomicRule(hours="12", timezone=UTC)
combined = rule_a + rule_b
```

---

## 3. Unbounded generation over large ranges

**Description**: Calling `generate()` over a multi-year range on a rule that matches every second (or very frequently).

**Why wrong**: Produces millions of datetimes, consuming memory and CPU. May trigger `ValueError` if `max_generate_items` is configured.

**Correct approach**: Use `generate_batch()` for large ranges, or set `max_generate_items` via `RuleConfig` as a safety net.

```python
# Risky
list(rule.generate(start, end))  # may produce millions of items

# Better
for batch in rule.generate_batch(start, end, batch_size=1000):
    process(batch)
```

---

## 4. Excluding all values in a DSL expression

**Description**: Writing a DSL expression that excludes every value in the field's valid range, e.g., `"!1,!2,!3,!4,!5,!6,!7,!8,!9,!10,!11,!12"` for months.

**Why wrong**: The result is an empty set, which raises `InvalidExpressionError`. Note that exclusion-only expressions that leave at least one value *do* work: `"!7"` is equivalent to `"1..12,!7"` because the parser implicitly starts from the full range when no inclusions are specified.

**Correct approach**: Ensure at least one value remains after exclusions.

```python
# Wrong — excludes all months
AtomicRule(months="!1,!2,!3,!4,!5,!6,!7,!8,!9,!10,!11,!12")  # InvalidExpressionError

# Fine — exclusion-only with remaining values (implicit full range)
AtomicRule(months="!7")  # equivalent to "1..12,!7"

# Explicit — same result, more readable
AtomicRule(months="1..12,!7")
```

---

## 5. Expecting sub-second resolution

**Description**: Assuming Zerotime can match or generate datetimes at millisecond or microsecond granularity.

**Why wrong**: Zerotime operates at second-level resolution. Microseconds in input datetimes are ignored during matching.

**Correct approach**: Accept second-level granularity as a design constraint.

---

## 6. Assuming negative days work in all fields

**Description**: Using negative values (e.g., `"-1"`) in fields other than `days`.

**Why wrong**: Negative values are only supported in the `days` field (to mean "last day of month", etc.). Other fields raise `InvalidExpressionError`.

**Correct approach**: Use negative values only in the `days` parameter.

```python
# Wrong
AtomicRule(hours="-1")  # InvalidExpressionError

# Correct
AtomicRule(days="-1")  # last day of month
```

---

## 7. Mutating rules instead of using with_* methods

**Description**: Attempting to modify rule attributes directly after construction.

**Why wrong**: `AtomicRule` uses `__slots__` and is designed to be immutable after construction. Direct attribute modification may fail or produce undefined behavior.

**Correct approach**: Use `with_*` builder methods to create modified copies.

```python
# Wrong (will fail)
rule._months_expr = "1,2,3"

# Correct
new_rule = rule.with_months("1,2,3")
```

---

## 8. Relying on JSON timezone round-trip for IANA zones

**Description**: Expecting `to_json()` / `from_json()` to preserve IANA timezone names (e.g., `"Europe/Rome"`).

**Why wrong**: JSON serialization preserves UTC offsets only, not IANA zone names. After deserialization, DST-aware behavior may differ from the original rule.

**Correct approach**: If IANA timezone fidelity is needed, store the timezone name separately and re-apply it after deserialization.
