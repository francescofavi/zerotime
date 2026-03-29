"""
Example 04: Generation Methods
==============================
Using generate(), generate_reverse(), and generate_batch().
"""

from datetime import UTC, datetime
from itertools import islice

from zerotime import AtomicRule

# -----------------------------------------------------------------------------
# generate() - forward chronological order
# -----------------------------------------------------------------------------

rule = AtomicRule(
    weekdays="1..5",  # Monday-Friday
    hours="9",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

start = datetime(2025, 1, 1, tzinfo=UTC)
end = datetime(2025, 1, 15, 23, 59, 59, tzinfo=UTC)

print("Weekday mornings at 9 AM (forward order):")
for dt in rule.generate(start, end):
    print(f"  {dt.strftime('%A, %B %d')}")

# -----------------------------------------------------------------------------
# generate_reverse() - reverse chronological order
# -----------------------------------------------------------------------------

print("\nWeekday mornings at 9 AM (reverse order):")
for dt in rule.generate_reverse(start, end):
    print(f"  {dt.strftime('%A, %B %d')}")

# -----------------------------------------------------------------------------
# Practical use: get most recent N occurrences
# -----------------------------------------------------------------------------


def get_last_n_occurrences(rule, before, n):
    """Get the N most recent occurrences before a datetime."""
    # Search back up to 1 year
    search_start = datetime(before.year - 1, before.month, before.day, tzinfo=before.tzinfo)
    search_end = before

    results = []
    for dt in rule.generate_reverse(search_start, search_end):
        results.append(dt)
        if len(results) >= n:
            break
    return results


now = datetime(2025, 1, 20, 12, 0, 0, tzinfo=UTC)
last_5 = get_last_n_occurrences(rule, now, 5)

print(f"\nLast 5 weekday 9 AM before {now.strftime('%B %d')}:")
for dt in last_5:
    print(f"  {dt.strftime('%A, %B %d')}")

# -----------------------------------------------------------------------------
# generate_batch() - memory-efficient batch processing
# -----------------------------------------------------------------------------

# Rule that generates many matches
every_minute = AtomicRule(seconds="0", timezone=UTC)

start = datetime(2025, 1, 1, tzinfo=UTC)
end = datetime(2025, 1, 1, 1, 0, 0, tzinfo=UTC)  # 1 hour = 61 minutes

print("\nProcessing in batches of 10:")
for i, batch in enumerate(every_minute.generate_batch(start, end, batch_size=10), 1):
    print(f"  Batch {i}: {len(batch)} items, first={batch[0].strftime('%H:%M')}")

# -----------------------------------------------------------------------------
# Batch processing use case: database inserts
# -----------------------------------------------------------------------------


def simulate_db_insert(records):
    """Simulate bulk database insert."""
    print(f"    Inserting {len(records)} records...")
    # db.bulk_insert(records)


# Generate a year of daily events in memory-efficient batches
daily_noon = AtomicRule(hours="12", minutes="0", seconds="0", timezone=UTC)

year_start = datetime(2025, 1, 1, tzinfo=UTC)
year_end = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

print("\nSimulating batch database insert for daily events:")
total = 0
for batch in daily_noon.generate_batch(year_start, year_end, batch_size=100):
    simulate_db_insert(batch)
    total += len(batch)
print(f"  Total records: {total}")

# -----------------------------------------------------------------------------
# Limiting generation with max_items
# -----------------------------------------------------------------------------

# High-frequency rule: every second
every_second = AtomicRule(timezone=UTC)

# Without limit, this would generate 86400 items per day!
# Use max_items to prevent runaway generation
start = datetime(2025, 1, 1, tzinfo=UTC)
end = datetime(2025, 1, 1, 0, 0, 10, tzinfo=UTC)  # 10 seconds

# With max_items, generation stops and raises error when limit is exceeded
# To get exactly N items, use islice or a counter

print("\nFirst 5 seconds (using islice to limit):")
for dt in islice(every_second.generate(start, end), 5):
    print(f"  {dt}")

# If generation would exceed max_items, it raises ValueError
try:
    # This would try to generate 11 items but limit is 5
    list(every_second.generate(start, end, max_items=5))
except ValueError as e:
    print(f"\nExpected error when exceeding limit: {e}")

# -----------------------------------------------------------------------------
# Counting matches without storing all in memory
# -----------------------------------------------------------------------------


def count_matches(rule, start, end):
    """Count matches without storing them all."""
    count = 0
    for _ in rule.generate(start, end):
        count += 1
    return count


workday_rule = AtomicRule(weekdays="1..5", hours="9..17", minutes="0", seconds="0", timezone=UTC)

year_start = datetime(2025, 1, 1, tzinfo=UTC)
year_end = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

print(f"\nWorkday hours in 2025: {count_matches(workday_rule, year_start, year_end)}")

# -----------------------------------------------------------------------------
# Converting to list (be careful with large ranges!)
# -----------------------------------------------------------------------------

# Safe: limited range
small_range_start = datetime(2025, 1, 1, tzinfo=UTC)
small_range_end = datetime(2025, 1, 7, 23, 59, 59, tzinfo=UTC)

all_matches = list(workday_rule.generate(small_range_start, small_range_end))
print(f"\nWorkday hours in first week: {len(all_matches)} matches")
print(f"  First: {all_matches[0]}")
print(f"  Last: {all_matches[-1]}")
