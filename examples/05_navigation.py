"""
Example 05: Temporal Navigation
===============================
Using get_next() and get_prev() to find occurrences.
"""

from datetime import UTC, datetime

from zerotime import AtomicRule, NoMatchFoundError

# -----------------------------------------------------------------------------
# Basic get_next() usage
# -----------------------------------------------------------------------------

# Monthly billing on the 1st at midnight
billing_rule = AtomicRule(
    days="1",
    hours="0",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

now = datetime(2025, 3, 15, 14, 30, 0, tzinfo=UTC)

next_billing = billing_rule.get_next(now)
print(f"Current date: {now.strftime('%B %d, %Y')}")
print(f"Next billing: {next_billing.strftime('%B %d, %Y')}")
# Output: Next billing: April 01, 2025

# -----------------------------------------------------------------------------
# Basic get_prev() usage
# -----------------------------------------------------------------------------

prev_billing = billing_rule.get_prev(now)
print(f"Previous billing: {prev_billing.strftime('%B %d, %Y')}")
# Output: Previous billing: March 01, 2025

# -----------------------------------------------------------------------------
# Search boundaries (max_years parameter)
# -----------------------------------------------------------------------------

# Rare event: February 29 (leap year)
leap_day = AtomicRule(
    months="2",
    days="29",
    hours="0",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Default search is 5 years
now = datetime(2025, 1, 1, tzinfo=UTC)
next_leap = leap_day.get_next(now)
print(f"\nNext Feb 29 after 2025: {next_leap.strftime('%B %d, %Y')}")
# Output: February 29, 2028

# Extend search range for very rare events
next_leap_10y = leap_day.get_next(now, max_years=10)
print(f"Next Feb 29 (10 year search): {next_leap_10y.strftime('%B %d, %Y')}")

# -----------------------------------------------------------------------------
# Handling NoMatchFoundError
# -----------------------------------------------------------------------------

# Impossible rule: June 31 doesn't exist
impossible = AtomicRule(
    months="6",
    days="31",  # June only has 30 days
    hours="0",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

try:
    impossible.get_next(now)
except NoMatchFoundError as e:
    print(f"\nExpected error: {e}")

# -----------------------------------------------------------------------------
# Iterating with get_next()
# -----------------------------------------------------------------------------


def iterate_occurrences(rule, start, count):
    """Get the next N occurrences using get_next()."""
    results = []
    current = start
    for _ in range(count):
        try:
            next_dt = rule.get_next(current)
            results.append(next_dt)
            current = next_dt
        except NoMatchFoundError:
            break
    return results


# Get next 5 monthly billings
next_5 = iterate_occurrences(billing_rule, now, 5)
print("\nNext 5 billing dates:")
for dt in next_5:
    print(f"  {dt.strftime('%B %d, %Y')}")

# -----------------------------------------------------------------------------
# Iterating backwards with get_prev()
# -----------------------------------------------------------------------------


def iterate_backwards(rule, start, count):
    """Get the previous N occurrences using get_prev()."""
    results = []
    current = start
    for _ in range(count):
        try:
            prev_dt = rule.get_prev(current)
            results.append(prev_dt)
            current = prev_dt
        except NoMatchFoundError:
            break
    return results


# Get last 5 quarterly closes (end of Mar, Jun, Sep, Dec)
quarterly_close = AtomicRule(
    months="3,6,9,12",
    days="-1",  # Last day
    hours="23",
    minutes="59",
    seconds="59",
    timezone=UTC,
)

now = datetime(2025, 8, 15, tzinfo=UTC)
last_5_quarters = iterate_backwards(quarterly_close, now, 5)
print(f"\nLast 5 quarterly closes before {now.strftime('%B %Y')}:")
for dt in last_5_quarters:
    print(f"  {dt.strftime('%B %d, %Y')}")

# -----------------------------------------------------------------------------
# Practical example: scheduling
# -----------------------------------------------------------------------------


def get_next_available_slot(rule, after):
    """Find next available time slot."""
    return rule.get_next(after)


def is_scheduled_time(rule, dt):
    """Check if a datetime matches the rule."""
    # Generate a tiny window around the datetime
    from datetime import timedelta

    start = dt
    end = dt + timedelta(seconds=1)

    return any(match == dt for match in rule.generate(start, end))


# Business hours every 30 minutes
meeting_slots = AtomicRule(
    weekdays="1..5",
    hours="9..16",
    minutes="0,30",
    seconds="0",
    timezone=UTC,
)

request_time = datetime(2025, 1, 6, 10, 45, 0, tzinfo=UTC)  # Monday 10:45
next_slot = get_next_available_slot(meeting_slots, request_time)

print(f"\nMeeting request at: {request_time.strftime('%A %H:%M')}")
print(f"Next available slot: {next_slot.strftime('%A %H:%M')}")

# Check if a specific time is valid
check_time = datetime(2025, 1, 6, 11, 0, 0, tzinfo=UTC)
is_valid = is_scheduled_time(meeting_slots, check_time)
print(f"Is {check_time.strftime('%H:%M')} a valid slot? {is_valid}")

# -----------------------------------------------------------------------------
# Combined rules with navigation
# -----------------------------------------------------------------------------

# Business hours minus lunch
business = AtomicRule(weekdays="1..5", hours="9..17", minutes="0", seconds="0", timezone=UTC)
lunch = AtomicRule(weekdays="1..5", hours="12,13", minutes="0", seconds="0", timezone=UTC)
working_hours = business - lunch

# Find next working hour
now = datetime(2025, 1, 6, 11, 30, 0, tzinfo=UTC)  # Monday 11:30
next_work = working_hours.get_next(now)
print(f"\nCurrent time: {now.strftime('%A %H:%M')}")
print(f"Next working hour (skipping lunch): {next_work.strftime('%A %H:%M')}")
# Skips 12:00 and 13:00, goes to 14:00
