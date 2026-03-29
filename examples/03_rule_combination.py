"""
Example 03: Rule Combination
============================
Combining rules with union (+), intersection (&), and difference (-).
"""

from datetime import UTC, datetime

from zerotime import AtomicRule, CombinedRule

# -----------------------------------------------------------------------------
# Union (+) - matches if EITHER rule matches
# -----------------------------------------------------------------------------

# Weekend rule
saturday = AtomicRule(weekdays="6", hours="10", minutes="0", seconds="0", timezone=UTC)
sunday = AtomicRule(weekdays="7", hours="10", minutes="0", seconds="0", timezone=UTC)

# Combined: matches Saturday OR Sunday at 10 AM
weekend = saturday + sunday

start = datetime(2025, 1, 1, tzinfo=UTC)
end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=UTC)

print("Weekend days at 10 AM in January 2025:")
for dt in weekend.generate(start, end):
    print(f"  {dt.strftime('%A, %B %d')}")

# -----------------------------------------------------------------------------
# Alternative: single AtomicRule for same result
# -----------------------------------------------------------------------------

# Often a single rule can achieve what union does
weekend_single = AtomicRule(weekdays="6,7", hours="10", minutes="0", seconds="0", timezone=UTC)

# Union is more useful when rules have different time components
saturday_morning = AtomicRule(weekdays="6", hours="9", minutes="0", seconds="0", timezone=UTC)
sunday_afternoon = AtomicRule(weekdays="7", hours="15", minutes="0", seconds="0", timezone=UTC)

# Saturday 9 AM OR Sunday 3 PM - can't do this with single AtomicRule!
weekend_special = saturday_morning + sunday_afternoon

print("\nSpecial weekend times:")
for dt in weekend_special.generate(start, end):
    print(f"  {dt.strftime('%A %H:%M')}")

# -----------------------------------------------------------------------------
# Intersection (&) - matches only if BOTH rules match
# -----------------------------------------------------------------------------

# All Fridays
fridays = AtomicRule(weekdays="5", hours="0..23", minutes="0", seconds="0", timezone=UTC)

# Day 13 of any month
day_13 = AtomicRule(days="13", hours="0..23", minutes="0", seconds="0", timezone=UTC)

# Friday the 13th! (matches when it's BOTH Friday AND day 13)
friday_13th = fridays & day_13

start_year = datetime(2025, 1, 1, tzinfo=UTC)
end_year = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

print("\nFriday the 13th in 2025 (at midnight):")
friday_13th_midnight = AtomicRule(
    weekdays="5", hours="0", minutes="0", seconds="0", timezone=UTC
) & AtomicRule(days="13", hours="0", minutes="0", seconds="0", timezone=UTC)

for dt in friday_13th_midnight.generate(start_year, end_year):
    print(f"  {dt.strftime('%B %d, %Y - %A')}")

# -----------------------------------------------------------------------------
# Practical intersection: business hours on specific days
# -----------------------------------------------------------------------------

# All hours on weekdays
weekday_hours = AtomicRule(weekdays="1..5", hours="0..23", minutes="0", seconds="0", timezone=UTC)

# 9-5 business hours any day
nine_to_five = AtomicRule(hours="9..17", minutes="0", seconds="0", timezone=UTC)

# Business hours on weekdays only
business_weekday = weekday_hours & nine_to_five

print("\nBusiness hours on Jan 6-10, 2025 (weekdays):")
week_start = datetime(2025, 1, 6, tzinfo=UTC)
week_end = datetime(2025, 1, 10, 23, 59, 59, tzinfo=UTC)
for dt in business_weekday.generate(week_start, week_end):
    print(f"  {dt.strftime('%A %H:00')}")

# -----------------------------------------------------------------------------
# Difference (-) - matches first rule BUT NOT second
# -----------------------------------------------------------------------------

# Business hours: 9 AM to 5 PM, on the hour
business_hours = AtomicRule(weekdays="1..5", hours="9..17", minutes="0", seconds="0", timezone=UTC)

# Lunch break: noon to 1 PM
lunch = AtomicRule(weekdays="1..5", hours="12,13", minutes="0", seconds="0", timezone=UTC)

# Working hours = business hours minus lunch
working_hours = business_hours - lunch

print("\nWorking hours (excluding lunch) on Monday Jan 6:")
monday = datetime(2025, 1, 6, tzinfo=UTC)
monday_end = datetime(2025, 1, 6, 23, 59, 59, tzinfo=UTC)
for dt in working_hours.generate(monday, monday_end):
    print(f"  {dt.strftime('%H:%M')}")
# Output: 09:00, 10:00, 11:00, 14:00, 15:00, 16:00, 17:00

# -----------------------------------------------------------------------------
# Complex example: workdays excluding holidays
# -----------------------------------------------------------------------------

# All workday mornings at 9 AM
workday_9am = AtomicRule(weekdays="1..5", hours="9", minutes="0", seconds="0", timezone=UTC)

# New Year's Day 2025 (Wednesday)
new_years = AtomicRule(months="1", days="1", hours="9", minutes="0", seconds="0", timezone=UTC)

# Christmas 2025 (Thursday)
christmas = AtomicRule(months="12", days="25", hours="9", minutes="0", seconds="0", timezone=UTC)

# All holidays combined
holidays = new_years + christmas

# Workdays excluding holidays
workdays_no_holidays = workday_9am - holidays

print("\nFirst 5 workdays of 2025 at 9 AM (excluding New Year's):")
jan_start = datetime(2025, 1, 1, tzinfo=UTC)
jan_end = datetime(2025, 1, 10, 23, 59, 59, tzinfo=UTC)
for i, dt in enumerate(workdays_no_holidays.generate(jan_start, jan_end)):
    print(f"  {dt.strftime('%A, %B %d')}")
    if i >= 4:  # 0-indexed, so 4 means 5 items
        break

# -----------------------------------------------------------------------------
# Chaining operations
# -----------------------------------------------------------------------------

# Rules can be chained: (A + B) - C or A & (B + C)
morning = AtomicRule(hours="9", minutes="0", seconds="0", timezone=UTC)
afternoon = AtomicRule(hours="15", minutes="0", seconds="0", timezone=UTC)
weekend_days = AtomicRule(weekdays="6,7", timezone=UTC)

# Morning or afternoon, but not on weekends
meetings = (morning + afternoon) - weekend_days

# This is equivalent to:
# meetings = CombinedRule(
#     CombinedRule(morning, afternoon, "union"),
#     weekend_days,
#     "difference"
# )

print("\nMeeting times in first week of Jan (weekdays only):")
for dt in meetings.generate(jan_start, jan_end):
    print(f"  {dt.strftime('%A %H:%M')}")

# -----------------------------------------------------------------------------
# Creating CombinedRule directly (alternative to operators)
# -----------------------------------------------------------------------------

# Using operators (preferred)
union_op = saturday + sunday
intersection_op = fridays & day_13
difference_op = business_hours - lunch

# Using constructor (equivalent)
union_ctor = CombinedRule(saturday, sunday, "union")
intersection_ctor = CombinedRule(fridays, day_13, "intersection")
difference_ctor = CombinedRule(business_hours, lunch, "difference")

print("\nOperator vs constructor - both work identically")
