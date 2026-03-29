"""
Example 08: JSON Serialization
==============================
Saving and restoring rules with to_json() and from_json().
"""

import json
from datetime import UTC, datetime, timedelta, timezone

from zerotime import AtomicRule, CombinedRule, Rule

# -----------------------------------------------------------------------------
# Basic serialization
# -----------------------------------------------------------------------------

# Create a rule
rule = AtomicRule(
    months="1,4,7,10",
    days="1",
    hours="9",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Serialize to JSON string
json_str = rule.to_json()
print("Serialized AtomicRule:")
print(json.dumps(json.loads(json_str), indent=2))

# -----------------------------------------------------------------------------
# Deserialization
# -----------------------------------------------------------------------------

# Restore from JSON - auto-detects rule type
restored = Rule.from_json(json_str)
print(f"\nRestored rule type: {type(restored).__name__}")

# Or deserialize specifically as AtomicRule
restored_atomic = AtomicRule.from_json(json_str)

# Verify it works the same
now = datetime(2025, 1, 1, tzinfo=UTC)
original_next = rule.get_next(now)
restored_next = restored.get_next(now)
print(f"Original next: {original_next}")
print(f"Restored next: {restored_next}")
print(f"Match: {original_next == restored_next}")

# -----------------------------------------------------------------------------
# Combined rules serialization
# -----------------------------------------------------------------------------

# Create combined rule
business = AtomicRule(weekdays="1..5", hours="9..17", minutes="0", seconds="0", timezone=UTC)
lunch = AtomicRule(weekdays="1..5", hours="12,13", minutes="0", seconds="0", timezone=UTC)
working_hours = business - lunch

# Serialize combined rule
combined_json = working_hours.to_json()
print("\nSerialized CombinedRule:")
print(json.dumps(json.loads(combined_json), indent=2))

# Restore combined rule
restored_combined = Rule.from_json(combined_json)
print(f"\nRestored combined rule type: {type(restored_combined).__name__}")

# Or specifically as CombinedRule
restored_combined = CombinedRule.from_json(combined_json)

# -----------------------------------------------------------------------------
# Nested combined rules
# -----------------------------------------------------------------------------

# Complex: (A + B) - C
weekday_9am = AtomicRule(weekdays="1..5", hours="9", minutes="0", seconds="0", timezone=UTC)
weekend_10am = AtomicRule(weekdays="6,7", hours="10", minutes="0", seconds="0", timezone=UTC)
holidays = AtomicRule(months="12", days="25", hours="0..23", minutes="0", seconds="0", timezone=UTC)

complex_rule = (weekday_9am + weekend_10am) - holidays

complex_json = complex_rule.to_json()
print("\nNested combined rule:")
print(json.dumps(json.loads(complex_json), indent=2)[:500] + "...")

# Restore nested rule
restored_complex = Rule.from_json(complex_json)
print(f"Restored nested rule type: {type(restored_complex).__name__}")

# -----------------------------------------------------------------------------
# Timezone serialization
# -----------------------------------------------------------------------------

# UTC timezone
utc_rule = AtomicRule(hours="12", minutes="0", seconds="0", timezone=UTC)
print(f"\nUTC rule JSON timezone: {json.loads(utc_rule.to_json())['timezone']}")

# Fixed offset timezone
est = timezone(timedelta(hours=-5))
est_rule = AtomicRule(hours="12", minutes="0", seconds="0", timezone=est)
print(f"EST rule JSON timezone: {json.loads(est_rule.to_json())['timezone']}")

# Positive offset
jst = timezone(timedelta(hours=9))
jst_rule = AtomicRule(hours="12", minutes="0", seconds="0", timezone=jst)
print(f"JST rule JSON timezone: {json.loads(jst_rule.to_json())['timezone']}")

# No timezone
naive_rule = AtomicRule(hours="12", minutes="0", seconds="0")
print(f"Naive rule JSON timezone: {json.loads(naive_rule.to_json())['timezone']}")

# -----------------------------------------------------------------------------
# Storing in database (example)
# -----------------------------------------------------------------------------


def save_schedule_to_db(schedule_id: str, rule: Rule):
    """Simulate saving to database."""
    json_str = rule.to_json()
    # In real code: db.execute("INSERT INTO schedules (id, rule_json) VALUES (?, ?)",
    #                          (schedule_id, json_str))
    print(f"Saved schedule '{schedule_id}': {len(json_str)} bytes")
    return json_str


def load_schedule_from_db(json_str: str) -> Rule:
    """Simulate loading from database."""
    # In real code: json_str = db.execute("SELECT rule_json FROM schedules WHERE id=?",
    #                                     (schedule_id,)).fetchone()[0]
    return Rule.from_json(json_str)


# Example workflow
daily_standup = AtomicRule(weekdays="1..5", hours="10", minutes="0", seconds="0", timezone=UTC)

saved_json = save_schedule_to_db("daily-standup", daily_standup)
loaded_rule = load_schedule_from_db(saved_json)

print(f"Loaded schedule works: {loaded_rule.get_next(datetime(2025, 1, 1, tzinfo=UTC))}")

# -----------------------------------------------------------------------------
# JSON format reference
# -----------------------------------------------------------------------------

print("\n" + "=" * 60)
print("JSON FORMAT REFERENCE")
print("=" * 60)

# AtomicRule format
atomic_example = AtomicRule(
    months="1..12",
    days="1,15,-1",
    weekdays="1..5",
    hours="9..17",
    minutes="/15",
    seconds="0",
    timezone=UTC,
)
print("\nAtomicRule JSON format:")
print(json.dumps(json.loads(atomic_example.to_json()), indent=2))

# CombinedRule format
combined_example = AtomicRule(hours="9", timezone=UTC) + AtomicRule(hours="17", timezone=UTC)
print("\nCombinedRule JSON format:")
print(json.dumps(json.loads(combined_example.to_json()), indent=2))

# -----------------------------------------------------------------------------
# Error handling
# -----------------------------------------------------------------------------

print("\nError handling:")

# Invalid JSON
try:
    Rule.from_json("not valid json")
except ValueError as e:
    print(f"  Invalid JSON: {type(e).__name__}")

# Unknown rule type
try:
    Rule.from_json('{"type": "unknown"}')
except ValueError as e:
    print(f"  Unknown type: {e}")

# Missing required fields
try:
    AtomicRule.from_json('{"type": "atomic"}')  # Missing all fields
except (ValueError, KeyError) as e:
    print(f"  Missing fields: {type(e).__name__}")

# -----------------------------------------------------------------------------
# Comparing serialized rules
# -----------------------------------------------------------------------------


def rules_equivalent(rule1: Rule, rule2: Rule, test_range_days: int = 30) -> bool:
    """Check if two rules produce the same results."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=test_range_days)

    results1 = list(rule1.generate(start, end))
    results2 = list(rule2.generate(start, end))

    return results1 == results2


# Test serialization roundtrip
original = AtomicRule(
    months="3,6,9,12", days="-1", hours="17", minutes="0", seconds="0", timezone=UTC
)
roundtrip = Rule.from_json(original.to_json())

print(f"\nRoundtrip equivalence: {rules_equivalent(original, roundtrip)}")
