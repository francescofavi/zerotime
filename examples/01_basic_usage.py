"""
Example 01: Basic Usage
=======================
Introduction to AtomicRule - the fundamental building block.
"""

from datetime import UTC, datetime

from zerotime import AtomicRule

# -----------------------------------------------------------------------------
# Creating a simple rule
# -----------------------------------------------------------------------------

# Every day at noon (12:00:00)
noon_rule = AtomicRule(
    hours="12",
    minutes="0",
    seconds="0",
)

# Find the next noon from now
now = datetime(2025, 6, 15, 10, 30, 0)
next_noon = noon_rule.get_next(now)
print(f"Next noon after {now}: {next_noon}")
# Output: Next noon after 2025-06-15 10:30:00: 2025-06-15 12:00:00

# Find the previous noon
prev_noon = noon_rule.get_prev(now)
print(f"Previous noon before {now}: {prev_noon}")
# Output: Previous noon before 2025-06-15 10:30:00: 2025-06-14 12:00:00

# -----------------------------------------------------------------------------
# Rule with timezone
# -----------------------------------------------------------------------------

# Same rule but timezone-aware
noon_utc = AtomicRule(
    hours="12",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Must use timezone-aware datetime with timezone-bound rules
now_utc = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)
next_noon_utc = noon_utc.get_next(now_utc)
print(f"Next UTC noon: {next_noon_utc}")
# Output: Next UTC noon: 2025-06-15 12:00:00+00:00

# -----------------------------------------------------------------------------
# Default values
# -----------------------------------------------------------------------------

# All fields have defaults that match everything in their range:
# - months: "1..12" (all months)
# - days: "1..31" (all days)
# - weekdays: "1..7" (all weekdays)
# - hours: "0..23" (all hours)
# - minutes: "0..59" (all minutes)
# - seconds: "0..59" (all seconds)

# This rule matches every second of every day
all_seconds = AtomicRule()

# This rule matches every minute at second 0
every_minute = AtomicRule(seconds="0")

# This rule matches every hour at minute 0, second 0
every_hour = AtomicRule(minutes="0", seconds="0")

print(f"\nNext second: {all_seconds.get_next(now)}")
print(f"Next minute: {every_minute.get_next(now)}")
print(f"Next hour: {every_hour.get_next(now)}")

# -----------------------------------------------------------------------------
# Matching semantics: AND logic
# -----------------------------------------------------------------------------

# A datetime matches if ALL constraints are satisfied (AND logic)
# Example: First day of month at 9 AM

first_of_month_9am = AtomicRule(
    days="1",
    hours="9",
    minutes="0",
    seconds="0",
)

# This matches ONLY when:
# - day == 1 AND
# - hour == 9 AND
# - minute == 0 AND
# - second == 0

start = datetime(2025, 1, 1)
end = datetime(2025, 12, 31, 23, 59, 59)

matches = list(first_of_month_9am.generate(start, end))
print(f"\nFirst of month at 9 AM in 2025: {len(matches)} matches")
for m in matches[:3]:
    print(f"  {m}")
# Output shows 12 matches, one for each month
