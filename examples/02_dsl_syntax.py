"""
Example 02: DSL Syntax
======================
Complete reference for the Domain-Specific Language expressions.
"""

from datetime import datetime

from zerotime import AtomicRule

# -----------------------------------------------------------------------------
# Single Value
# -----------------------------------------------------------------------------
# Matches exactly one value

# Only January
january = AtomicRule(months="1", days="1", hours="0", minutes="0", seconds="0")

# Only day 15
day_15 = AtomicRule(days="15", hours="0", minutes="0", seconds="0")

# Only at 3 PM
at_3pm = AtomicRule(hours="15", minutes="0", seconds="0")

# -----------------------------------------------------------------------------
# Range (inclusive)
# -----------------------------------------------------------------------------
# Syntax: "N..M" - matches all values from N to M

# January through March (Q1)
q1 = AtomicRule(months="1..3", days="1", hours="0", minutes="0", seconds="0")

# Monday through Friday (weekdays)
weekdays = AtomicRule(weekdays="1..5", hours="9", minutes="0", seconds="0")

# Business hours: 9 AM to 5 PM
business_hours = AtomicRule(hours="9..17", minutes="0", seconds="0")

# -----------------------------------------------------------------------------
# Range with Step
# -----------------------------------------------------------------------------
# Syntax: "N..M/S" - matches values from N to M, stepping by S

# Every 15 minutes within an hour
every_15_min = AtomicRule(minutes="0..59/15", seconds="0")
# Matches: 0, 15, 30, 45

# Every 2 hours during business hours
every_2h_business = AtomicRule(hours="9..17/2", minutes="0", seconds="0")
# Matches: 9, 11, 13, 15, 17

# Every week (days 1, 8, 15, 22, 29)
weekly_from_1st = AtomicRule(days="1..31/7", hours="0", minutes="0", seconds="0")

# -----------------------------------------------------------------------------
# Global Step
# -----------------------------------------------------------------------------
# Syntax: "/S" - matches multiples of S
# For fields starting at 0: starts from 0
# For fields starting at 1: starts from first multiple >= 1

# Every 15 minutes (0, 15, 30, 45)
quarter_hour = AtomicRule(minutes="/15", seconds="0")

# Every 5 seconds (0, 5, 10, 15, ..., 55)
every_5_sec = AtomicRule(seconds="/5")

# Every 3 months (3, 6, 9, 12) - for months, starts from first multiple >= 1
quarterly = AtomicRule(months="/3", days="1", hours="0", minutes="0", seconds="0")

# Every 5 months (5, 10) - first multiple of 5 >= 1 is 5
every_5_months = AtomicRule(months="/5", days="1", hours="0", minutes="0", seconds="0")

# Verify quarterly matches
start = datetime(2025, 1, 1)
end = datetime(2025, 12, 31, 23, 59, 59)
print("Quarterly (months /3):")
for dt in quarterly.generate(start, end):
    print(f"  {dt.strftime('%B %d')}")
# Output: March 01, June 01, September 01, December 01

# -----------------------------------------------------------------------------
# List (comma-separated)
# -----------------------------------------------------------------------------
# Syntax: "A,B,C" - matches any of the listed values

# Specific months: Jan, Apr, Jul, Oct
fiscal_quarters = AtomicRule(months="1,4,7,10", days="1", hours="0", minutes="0", seconds="0")

# Specific days: 1st, 15th, last day
paydays = AtomicRule(days="1,15,-1", hours="12", minutes="0", seconds="0")

# Weekend
weekend = AtomicRule(weekdays="6,7", hours="10", minutes="0", seconds="0")

# Combining ranges and single values
work_hours = AtomicRule(hours="9,10,11,14,15,16,17", minutes="0", seconds="0")
# Or equivalently with ranges:
work_hours_v2 = AtomicRule(hours="9..11,14..17", minutes="0", seconds="0")

# -----------------------------------------------------------------------------
# Exclusion
# -----------------------------------------------------------------------------
# Syntax: "!N" - excludes value N from the set
# Can combine with inclusions or use alone (starts with full range)

# All months except July and August (summer vacation)
no_summer = AtomicRule(months="1..12,!7,!8", days="1", hours="0", minutes="0", seconds="0")

# All weekdays except Wednesday
no_wednesday = AtomicRule(weekdays="1..5,!3", hours="9", minutes="0", seconds="0")

# Using exclusion alone - starts with full range then excludes
# All hours except midnight (0) and noon (12)
no_midnight_noon = AtomicRule(hours="!0,!12", minutes="0", seconds="0")

print("\nMonths excluding summer:")
for dt in no_summer.generate(start, end):
    print(f"  {dt.strftime('%B')}")

# -----------------------------------------------------------------------------
# Negative Days (days field only)
# -----------------------------------------------------------------------------
# Syntax: "-N" - counts from end of month
# -1 = last day, -2 = second-to-last, etc.

# Last day of every month
last_day = AtomicRule(days="-1", hours="23", minutes="59", seconds="59")

# Second-to-last day
penultimate = AtomicRule(days="-2", hours="12", minutes="0", seconds="0")

# Last 3 days of month
last_3_days = AtomicRule(days="-1,-2,-3", hours="9", minutes="0", seconds="0")

# Last week of month (last 7 days)
last_week = AtomicRule(days="-7,-6,-5,-4,-3,-2,-1", hours="9", minutes="0", seconds="0")

print("\nLast day of each month in 2025:")
for dt in last_day.generate(start, end):
    print(f"  {dt.strftime('%B %d')} (day {dt.day})")

# -----------------------------------------------------------------------------
# Complex combinations
# -----------------------------------------------------------------------------

# Business hours on weekdays, every 30 minutes, excluding lunch
complex_rule = AtomicRule(
    weekdays="1..5",  # Monday-Friday
    hours="9..11,14..17",  # 9-11 and 14-17 (skip lunch 12-13)
    minutes="0,30",  # On the hour and half hour
    seconds="0",
)

# First Monday of each quarter
first_monday_quarter = AtomicRule(
    months="1,4,7,10",  # Quarter starts
    days="1..7",  # First 7 days (one will be Monday)
    weekdays="1",  # Monday
    hours="9",
    minutes="0",
    seconds="0",
)

print("\nFirst Monday of each quarter 2025:")
for dt in first_monday_quarter.generate(start, end):
    print(f"  {dt.strftime('%B %d, %A')}")
