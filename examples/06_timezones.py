"""
Example 06: Timezone Handling
=============================
Working with timezones, including DST transitions.
"""

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from zerotime import AtomicRule

# -----------------------------------------------------------------------------
# Basic timezone usage
# -----------------------------------------------------------------------------

# Rule bound to UTC
utc_rule = AtomicRule(
    hours="12",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Must use timezone-aware datetime
now_utc = datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC)
next_noon_utc = utc_rule.get_next(now_utc)
print(f"Next UTC noon: {next_noon_utc}")

# -----------------------------------------------------------------------------
# Using ZoneInfo for IANA timezones
# -----------------------------------------------------------------------------

# Rule in Europe/Rome timezone
rome_tz = ZoneInfo("Europe/Rome")
rome_rule = AtomicRule(
    hours="9",
    minutes="0",
    seconds="0",
    timezone=rome_tz,
)

now_rome = datetime(2025, 6, 15, 8, 0, 0, tzinfo=rome_tz)
next_9am_rome = rome_rule.get_next(now_rome)
print(f"Next 9 AM in Rome: {next_9am_rome}")
print(f"  Same time in UTC: {next_9am_rome.astimezone(UTC)}")

# -----------------------------------------------------------------------------
# Fixed UTC offset timezones
# -----------------------------------------------------------------------------

# EST (UTC-5)
est = timezone(timedelta(hours=-5))
est_rule = AtomicRule(
    hours="9",
    minutes="0",
    seconds="0",
    timezone=est,
)

now_est = datetime(2025, 6, 15, 8, 0, 0, tzinfo=est)
next_9am_est = est_rule.get_next(now_est)
print(f"\nNext 9 AM EST: {next_9am_est}")
print(f"  Same time in UTC: {next_9am_est.astimezone(UTC)}")

# -----------------------------------------------------------------------------
# Converting between timezones
# -----------------------------------------------------------------------------

# Generate in one timezone, use in another
paris = ZoneInfo("Europe/Paris")
new_york = ZoneInfo("America/New_York")

paris_rule = AtomicRule(
    weekdays="1..5",
    hours="9",
    minutes="0",
    seconds="0",
    timezone=paris,
)

start = datetime(2025, 1, 6, tzinfo=paris)
end = datetime(2025, 1, 10, 23, 59, 59, tzinfo=paris)

print("\nParis 9 AM meetings shown in New York time:")
for dt in paris_rule.generate(start, end):
    ny_time = dt.astimezone(new_york)
    print(f"  Paris: {dt.strftime('%a %H:%M %Z')} = NY: {ny_time.strftime('%a %H:%M %Z')}")

# -----------------------------------------------------------------------------
# DST Handling - Spring Forward
# -----------------------------------------------------------------------------

# In Europe/Rome, on March 30, 2025 at 02:00 clocks jump to 03:00
# So 02:30 does not exist on that day

rome = ZoneInfo("Europe/Rome")

# Rule for 02:30 AM
rule_230am = AtomicRule(
    months="3",
    days="30",  # DST transition day in 2025
    hours="2",
    minutes="30",
    seconds="0",
    timezone=rome,
)

# Try to generate - the non-existent time is automatically skipped
start = datetime(2025, 3, 30, 0, 0, 0, tzinfo=rome)
end = datetime(2025, 3, 30, 23, 59, 59, tzinfo=rome)

matches = list(rule_230am.generate(start, end))
print(f"\n02:30 AM on March 30, 2025 (DST day) in Rome: {len(matches)} matches")
print("  (Time doesn't exist - clocks jump from 02:00 to 03:00)")

# But 02:30 exists on other days
rule_230am_march = AtomicRule(
    months="3",
    days="1..29",  # Excluding DST day
    hours="2",
    minutes="30",
    seconds="0",
    timezone=rome,
)

march_start = datetime(2025, 3, 1, tzinfo=rome)
march_end = datetime(2025, 3, 29, 23, 59, 59, tzinfo=rome)

matches = list(rule_230am_march.generate(march_start, march_end))
print(f"02:30 AM on other March days: {len(matches)} matches")

# -----------------------------------------------------------------------------
# DST Handling - Fall Back
# -----------------------------------------------------------------------------

# In Europe/Rome, on October 26, 2025 at 03:00 clocks go back to 02:00
# So 02:30 occurs twice on that day

# Zerotime uses fold=0 (first occurrence)
rule_fall = AtomicRule(
    months="10",
    days="26",
    hours="2",
    minutes="30",
    seconds="0",
    timezone=rome,
)

oct_start = datetime(2025, 10, 26, 0, 0, 0, tzinfo=rome)
oct_end = datetime(2025, 10, 26, 23, 59, 59, tzinfo=rome)

matches = list(rule_fall.generate(oct_start, oct_end))
print("\n02:30 AM on Oct 26, 2025 (fall back) in Rome:")
for m in matches:
    print(f"  {m} (fold={m.fold})")
    # Convert to UTC to see the actual instant
    print(f"    UTC: {m.astimezone(UTC)}")

# -----------------------------------------------------------------------------
# Rule without timezone (naive datetimes)
# -----------------------------------------------------------------------------

# Rules without timezone work with naive datetimes
naive_rule = AtomicRule(
    hours="12",
    minutes="0",
    seconds="0",
)

now_naive = datetime(2025, 6, 15, 10, 0, 0)  # No tzinfo
next_naive = naive_rule.get_next(now_naive)
print(f"\nNaive datetime: {next_naive}")
print(f"  tzinfo: {next_naive.tzinfo}")  # None

# -----------------------------------------------------------------------------
# Error: mixing naive and aware
# -----------------------------------------------------------------------------

# Timezone-bound rules require timezone-aware input
utc_rule = AtomicRule(hours="12", minutes="0", seconds="0", timezone=UTC)

try:
    # This fails: naive datetime with timezone-aware rule
    utc_rule.get_next(datetime(2025, 6, 15, 10, 0, 0))
except ValueError as e:
    print(f"\nExpected error (naive with tz-aware rule): {e}")

# -----------------------------------------------------------------------------
# Comparing times across timezones
# -----------------------------------------------------------------------------

# Same instant, different representations
utc_noon = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
rome_noon = utc_noon.astimezone(rome)  # 14:00 in Rome (summer time)

print("\nSame instant:")
print(f"  UTC:  {utc_noon}")
print(f"  Rome: {rome_noon}")
print(f"  Equal? {utc_noon == rome_noon}")  # True - same instant

# -----------------------------------------------------------------------------
# Multi-timezone scheduling
# -----------------------------------------------------------------------------


def find_overlapping_hours(tz1, tz2, hour_range, date):
    """Find hours that fall within business hours in both timezones."""
    overlapping = []

    for hour in range(hour_range[0], hour_range[1] + 1):
        dt_tz1 = datetime(date.year, date.month, date.day, hour, 0, 0, tzinfo=tz1)
        dt_tz2 = dt_tz1.astimezone(tz2)

        # Check if the hour in tz2 is also within business hours
        if hour_range[0] <= dt_tz2.hour <= hour_range[1]:
            overlapping.append((dt_tz1, dt_tz2))

    return overlapping


# Find overlapping business hours (9-17) between Paris and New York
date = datetime(2025, 1, 15)
overlapping = find_overlapping_hours(paris, new_york, (9, 17), date)

print("\nOverlapping business hours Paris/New York on Jan 15:")
for p, ny in overlapping:
    print(f"  Paris {p.strftime('%H:%M')} = NY {ny.strftime('%H:%M')}")
