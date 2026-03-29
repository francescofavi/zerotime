"""
Example 09: Builder Methods
===========================
Using with_* methods to create modified rule copies.
"""

from datetime import UTC, datetime, timedelta, timezone

from zerotime import AtomicRule

# -----------------------------------------------------------------------------
# Basic builder pattern
# -----------------------------------------------------------------------------

# Start with a base rule
base = AtomicRule(
    hours="9",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Create variations without modifying the original
morning = base.with_hours("9")
noon = base.with_hours("12")
evening = base.with_hours("18")

print("Base rule and variations:")
now = datetime(2025, 1, 1, 8, 0, 0, tzinfo=UTC)
print(f"  Morning (9 AM): {morning.get_next(now).strftime('%H:%M')}")
print(f"  Noon (12 PM):   {noon.get_next(now).strftime('%H:%M')}")
print(f"  Evening (6 PM): {evening.get_next(now).strftime('%H:%M')}")

# Original is unchanged
print(f"  Original:       {base.get_next(now).strftime('%H:%M')}")

# -----------------------------------------------------------------------------
# All builder methods
# -----------------------------------------------------------------------------

base = AtomicRule(timezone=UTC)

# with_months - change month constraint
quarterly = base.with_months("3,6,9,12")  # Quarter ends

# with_days - change day constraint
first_of_month = base.with_days("1")
last_of_month = base.with_days("-1")

# with_weekdays - change weekday constraint
weekdays_only = base.with_weekdays("1..5")
weekends_only = base.with_weekdays("6,7")

# with_hours - change hour constraint
business_hours = base.with_hours("9..17")
night_hours = base.with_hours("22..23,0..5")

# with_minutes - change minute constraint
on_the_hour = base.with_minutes("0")
quarter_hour = base.with_minutes("/15")

# with_seconds - change second constraint
on_the_minute = base.with_seconds("0")

# with_timezone - change timezone
est = timezone(timedelta(hours=-5))
utc_rule = base.with_timezone(UTC)
est_rule = base.with_timezone(est)
naive_rule = base.with_timezone(None)

# -----------------------------------------------------------------------------
# Chaining builder methods
# -----------------------------------------------------------------------------

# Build up a complex rule step by step
work_schedule = (
    AtomicRule()
    .with_weekdays("1..5")  # Monday-Friday
    .with_hours("9..17")  # 9 AM - 5 PM
    .with_minutes("0")  # On the hour
    .with_seconds("0")
    .with_timezone(UTC)
)

print("\nChained builder - work schedule:")
start = datetime(2025, 1, 6, tzinfo=UTC)  # Monday
end = datetime(2025, 1, 6, 23, 59, 59, tzinfo=UTC)
for dt in work_schedule.generate(start, end):
    print(f"  {dt.strftime('%H:%M')}")

# -----------------------------------------------------------------------------
# Deriving rules from templates
# -----------------------------------------------------------------------------


def create_daily_event(hour: int, minute: int = 0) -> AtomicRule:
    """Create a daily event at a specific time."""
    return AtomicRule(seconds="0", timezone=UTC).with_hours(str(hour)).with_minutes(str(minute))


def create_weekly_event(weekday: int, hour: int) -> AtomicRule:
    """Create a weekly event on a specific day and time."""
    return (
        AtomicRule(seconds="0", timezone=UTC)
        .with_weekdays(str(weekday))
        .with_hours(str(hour))
        .with_minutes("0")
    )


# Create various events from templates
standup = create_daily_event(10, 0)  # Daily standup at 10:00
weekly_review = create_weekly_event(5, 15)  # Friday at 3 PM
lunch_reminder = create_daily_event(12, 30)  # 12:30 daily

print("\nEvents from templates:")
now = datetime(2025, 1, 6, 8, 0, 0, tzinfo=UTC)
print(f"  Next standup: {standup.get_next(now)}")
print(f"  Next weekly review: {weekly_review.get_next(now)}")
print(f"  Next lunch reminder: {lunch_reminder.get_next(now)}")

# -----------------------------------------------------------------------------
# Creating schedule variations
# -----------------------------------------------------------------------------

# Base schedule for 9 AM
daily_9am = AtomicRule(
    hours="9",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Time zone variations
new_york = timezone(timedelta(hours=-5))
london = timezone(timedelta(hours=0))
tokyo = timezone(timedelta(hours=9))

schedules = {
    "New York": daily_9am.with_timezone(new_york),
    "London": daily_9am.with_timezone(london),
    "Tokyo": daily_9am.with_timezone(tokyo),
}

print("\nSame meeting time in different offices:")
base_date = datetime(2025, 6, 15, 0, 0, 0, tzinfo=UTC)
for office, schedule in schedules.items():
    next_meeting = schedule.get_next(base_date)
    print(f"  {office}: {next_meeting}")

# -----------------------------------------------------------------------------
# Seasonal variations
# -----------------------------------------------------------------------------

# Summer schedule (later start)
base_schedule = AtomicRule(
    weekdays="1..5",
    hours="9",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

summer_schedule = base_schedule.with_hours("10")  # Start at 10 in summer
winter_schedule = base_schedule.with_hours("8")  # Start at 8 in winter


def get_current_schedule(date: datetime) -> AtomicRule:
    """Get schedule based on month."""
    if 6 <= date.month <= 8:  # June-August
        return summer_schedule
    elif date.month in [12, 1, 2]:  # Dec-Feb
        return winter_schedule
    else:
        return base_schedule


print("\nSeasonal schedule variation:")
for month in [1, 6, 10]:
    date = datetime(2025, month, 15, 7, 0, 0, tzinfo=UTC)
    schedule = get_current_schedule(date)
    next_work = schedule.get_next(date)
    print(f"  {date.strftime('%B')}: Start at {next_work.strftime('%H:%M')}")

# -----------------------------------------------------------------------------
# Immutability demonstration
# -----------------------------------------------------------------------------

original = AtomicRule(
    hours="9",
    minutes="0",
    seconds="0",
    timezone=UTC,
)

# Create many variations - original never changes
variations = [
    original.with_hours("10"),
    original.with_hours("11"),
    original.with_minutes("30"),
    original.with_weekdays("1..5"),
]

print("\nImmutability - original unchanged after creating variations:")
print("  Original hours: 9")  # Still 9, not affected by with_hours calls

# Each variation is independent
now = datetime(2025, 1, 1, 8, 0, 0, tzinfo=UTC)
print("\nVariations are independent:")
for i, var in enumerate(variations):
    next_time = var.get_next(now)
    print(f"  Variation {i + 1}: {next_time.strftime('%H:%M')}")
