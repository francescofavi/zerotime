"""
Example 10: Real-World Examples
===============================
Practical use cases showing zerotime in action.
"""

from datetime import UTC, datetime, timedelta

from zerotime import AtomicRule, Rule

# =============================================================================
# USE CASE 1: Business Hours Calendar
# =============================================================================


def create_business_hours_calendar():
    """
    Create a business hours calendar with:
    - Weekdays 9 AM - 5 PM
    - Lunch break 12-1 PM
    - Meetings every 30 minutes
    """
    # All possible meeting slots
    all_slots = AtomicRule(
        weekdays="1..5",
        hours="9..17",
        minutes="0,30",
        seconds="0",
        timezone=UTC,
    )

    # Lunch break slots to exclude
    lunch = AtomicRule(
        weekdays="1..5",
        hours="12",
        minutes="0,30",
        seconds="0",
        timezone=UTC,
    )

    # Available meeting slots
    return all_slots - lunch


def get_available_slots(rule: Rule, date: datetime, count: int = 5) -> list[datetime]:
    """Get next N available slots from a given date."""
    slots = []
    current = date
    while len(slots) < count:
        try:
            next_slot = rule.get_next(current)
            slots.append(next_slot)
            current = next_slot
        except Exception:
            break
    return slots


print("=" * 60)
print("USE CASE 1: Business Hours Calendar")
print("=" * 60)

calendar = create_business_hours_calendar()
now = datetime(2025, 1, 6, 10, 0, 0, tzinfo=UTC)  # Monday 10 AM

print(f"\nNext 5 available meeting slots after {now.strftime('%A %H:%M')}:")
for slot in get_available_slots(calendar, now, 5):
    print(f"  {slot.strftime('%A %H:%M')}")


# =============================================================================
# USE CASE 2: Recurring Billing System
# =============================================================================


class BillingSchedule:
    """Billing schedule with different frequencies."""

    def __init__(self, name: str, rule: Rule):
        self.name = name
        self.rule = rule

    def get_next_billing_date(self, after: datetime) -> datetime:
        return self.rule.get_next(after)

    def get_billing_dates_in_period(self, start: datetime, end: datetime) -> list[datetime]:
        return list(self.rule.generate(start, end))


def create_billing_schedules():
    """Create common billing schedules."""
    return {
        # Monthly on the 1st at midnight
        "monthly": BillingSchedule(
            "Monthly",
            AtomicRule(days="1", hours="0", minutes="0", seconds="0", timezone=UTC),
        ),
        # Weekly on Monday at midnight
        "weekly": BillingSchedule(
            "Weekly",
            AtomicRule(weekdays="1", hours="0", minutes="0", seconds="0", timezone=UTC),
        ),
        # Quarterly on the 1st of Jan, Apr, Jul, Oct
        "quarterly": BillingSchedule(
            "Quarterly",
            AtomicRule(
                months="1,4,7,10",
                days="1",
                hours="0",
                minutes="0",
                seconds="0",
                timezone=UTC,
            ),
        ),
        # Bi-weekly (every other Monday) - approximate with 1st and 15th
        "biweekly": BillingSchedule(
            "Bi-weekly",
            AtomicRule(days="1,15", hours="0", minutes="0", seconds="0", timezone=UTC),
        ),
        # Annual on January 1st
        "annual": BillingSchedule(
            "Annual",
            AtomicRule(
                months="1",
                days="1",
                hours="0",
                minutes="0",
                seconds="0",
                timezone=UTC,
            ),
        ),
    }


print("\n" + "=" * 60)
print("USE CASE 2: Recurring Billing System")
print("=" * 60)

schedules = create_billing_schedules()
reference = datetime(2025, 3, 15, tzinfo=UTC)

print(f"\nNext billing dates after {reference.strftime('%B %d, %Y')}:")
for _name, schedule in schedules.items():
    next_date = schedule.get_next_billing_date(reference)
    print(f"  {schedule.name}: {next_date.strftime('%B %d, %Y')}")


# =============================================================================
# USE CASE 3: Shift Scheduling
# =============================================================================


class ShiftScheduler:
    """Schedule different work shifts."""

    def __init__(self):
        self.shifts = {}

    def add_shift(self, name: str, weekdays: str, start_hour: int, end_hour: int):
        """Add a shift definition."""
        # Create entry points for each shift
        self.shifts[name] = AtomicRule(
            weekdays=weekdays,
            hours=str(start_hour),
            minutes="0",
            seconds="0",
            timezone=UTC,
        )

    def get_next_shift(self, shift_name: str, after: datetime) -> datetime:
        return self.shifts[shift_name].get_next(after)

    def get_all_shifts_today(self, date: datetime) -> dict[str, datetime | None]:
        """Get all shift start times for a given day."""
        start = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=date.tzinfo)
        end = start + timedelta(days=1) - timedelta(seconds=1)

        result = {}
        for name, rule in self.shifts.items():
            matches = list(rule.generate(start, end))
            result[name] = matches[0] if matches else None
        return result


print("\n" + "=" * 60)
print("USE CASE 3: Shift Scheduling")
print("=" * 60)

scheduler = ShiftScheduler()
scheduler.add_shift("Morning", "1..5", 6, 14)  # 6 AM - 2 PM weekdays
scheduler.add_shift("Afternoon", "1..5", 14, 22)  # 2 PM - 10 PM weekdays
scheduler.add_shift("Night", "1..7", 22, 6)  # 10 PM - 6 AM all days
scheduler.add_shift("Weekend Day", "6,7", 8, 20)  # 8 AM - 8 PM weekends

monday = datetime(2025, 1, 6, tzinfo=UTC)
print(f"\nShifts on {monday.strftime('%A, %B %d')}:")
for name, start_time in scheduler.get_all_shifts_today(monday).items():
    if start_time:
        print(f"  {name}: starts at {start_time.strftime('%H:%M')}")


# =============================================================================
# USE CASE 4: Reminder/Notification System
# =============================================================================


class Reminder:
    """A recurring reminder."""

    def __init__(self, name: str, rule: Rule, message: str):
        self.name = name
        self.rule = rule
        self.message = message

    def get_next_occurrence(self, after: datetime) -> datetime:
        return self.rule.get_next(after)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "rule": self.rule.to_json(),
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Reminder":
        return cls(
            name=data["name"],
            rule=Rule.from_json(data["rule"]),
            message=data["message"],
        )


def create_sample_reminders():
    """Create sample reminders."""
    return [
        Reminder(
            "Daily Standup",
            AtomicRule(weekdays="1..5", hours="10", minutes="0", seconds="0", timezone=UTC),
            "Time for the daily standup meeting!",
        ),
        Reminder(
            "Weekly Report",
            AtomicRule(weekdays="5", hours="16", minutes="0", seconds="0", timezone=UTC),
            "Don't forget to submit your weekly report!",
        ),
        Reminder(
            "Monthly Invoice",
            AtomicRule(days="-1", hours="9", minutes="0", seconds="0", timezone=UTC),
            "Last day of month - send invoices!",
        ),
        Reminder(
            "Quarterly Review",
            AtomicRule(
                months="3,6,9,12",
                days="-1",
                hours="14",
                minutes="0",
                seconds="0",
                timezone=UTC,
            ),
            "Quarterly performance review",
        ),
    ]


print("\n" + "=" * 60)
print("USE CASE 4: Reminder/Notification System")
print("=" * 60)

reminders = create_sample_reminders()
now = datetime(2025, 1, 15, 8, 0, 0, tzinfo=UTC)

print(f"\nUpcoming reminders after {now.strftime('%B %d, %H:%M')}:")
upcoming = sorted(
    [(r.name, r.get_next_occurrence(now), r.message) for r in reminders],
    key=lambda x: x[1],
)
for name, when, message in upcoming[:5]:
    print(f"  {when.strftime('%b %d %H:%M')} - {name}")
    print(f'    "{message}"')


# =============================================================================
# USE CASE 5: SLA/Deadline Calculator
# =============================================================================


class SLACalculator:
    """Calculate SLA deadlines considering business hours."""

    def __init__(self, business_hours: Rule):
        self.business_hours = business_hours

    def add_business_hours(self, start: datetime, hours: int) -> datetime:
        """Add N business hours to a datetime."""
        # Each business hour slot
        current = start
        hours_added = 0

        while hours_added < hours:
            try:
                next_hour = self.business_hours.get_next(current)
                hours_added += 1
                current = next_hour
            except Exception:
                break

        return current

    def count_business_hours(self, start: datetime, end: datetime) -> int:
        """Count business hours between two datetimes."""
        return len(list(self.business_hours.generate(start, end)))


print("\n" + "=" * 60)
print("USE CASE 5: SLA/Deadline Calculator")
print("=" * 60)

# Business hours: weekdays 9-17, on the hour (excluding lunch)
business_hours = AtomicRule(
    weekdays="1..5",
    hours="9..11,14..17",  # Skip lunch
    minutes="0",
    seconds="0",
    timezone=UTC,
)

sla = SLACalculator(business_hours)

# Ticket opened Friday at 4 PM
ticket_opened = datetime(2025, 1, 10, 16, 0, 0, tzinfo=UTC)  # Friday 4 PM
sla_deadline = sla.add_business_hours(ticket_opened, 8)  # 8 hour SLA

print(f"\nTicket opened: {ticket_opened.strftime('%A %B %d, %H:%M')}")
print(f"8-hour SLA deadline: {sla_deadline.strftime('%A %B %d, %H:%M')}")
print("  (Skips weekend and lunch hours)")


# =============================================================================
# USE CASE 6: Maintenance Window Scheduler
# =============================================================================


class MaintenanceWindow:
    """Define and check maintenance windows."""

    def __init__(self):
        self.windows: list[tuple[str, Rule]] = []

    def add_window(self, name: str, rule: Rule):
        self.windows.append((name, rule))

    def is_in_maintenance(self, dt: datetime) -> tuple[bool, str | None]:
        """Check if datetime falls in any maintenance window."""
        for name, rule in self.windows:
            start = dt - timedelta(hours=1)
            end = dt + timedelta(seconds=1)
            for match in rule.generate(start, end):
                if match <= dt:
                    return True, name
        return False, None

    def get_next_window(self, after: datetime) -> tuple[str, datetime] | None:
        """Get the next maintenance window."""
        next_windows = []
        for name, rule in self.windows:
            try:
                next_time = rule.get_next(after)
                next_windows.append((name, next_time))
            except Exception:
                pass

        if not next_windows:
            return None

        return min(next_windows, key=lambda x: x[1])


print("\n" + "=" * 60)
print("USE CASE 6: Maintenance Window Scheduler")
print("=" * 60)

maint = MaintenanceWindow()

# Weekly maintenance: Sunday 2-6 AM
maint.add_window(
    "Weekly Maintenance",
    AtomicRule(weekdays="7", hours="2..5", minutes="0", seconds="0", timezone=UTC),
)

# Monthly patching: First Sunday of month 1-5 AM
maint.add_window(
    "Monthly Patching",
    AtomicRule(days="1..7", weekdays="7", hours="1..4", minutes="0", seconds="0", timezone=UTC),
)

now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
print(f"\nCurrent time: {now.strftime('%A %B %d, %H:%M')}")

in_maint, window_name = maint.is_in_maintenance(now)
print(f"In maintenance window: {in_maint}")

next_window = maint.get_next_window(now)
if next_window:
    print(f"Next window: {next_window[0]} at {next_window[1].strftime('%A %B %d, %H:%M')}")


# =============================================================================
# USE CASE 7: Report Generation Schedule
# =============================================================================

print("\n" + "=" * 60)
print("USE CASE 7: Report Generation Schedule")
print("=" * 60)


class ReportSchedule:
    """Schedule for automated report generation."""

    SCHEDULES = {
        "daily_sales": AtomicRule(
            weekdays="1..5",  # Business days only
            hours="6",  # Early morning
            minutes="0",
            seconds="0",
            timezone=UTC,
        ),
        "weekly_summary": AtomicRule(
            weekdays="1",  # Monday
            hours="7",
            minutes="0",
            seconds="0",
            timezone=UTC,
        ),
        "monthly_financial": AtomicRule(
            days="1",  # First of month
            hours="8",
            minutes="0",
            seconds="0",
            timezone=UTC,
        ),
        "quarterly_board": AtomicRule(
            months="1,4,7,10",
            days="15",  # Mid-month after quarter end
            hours="9",
            minutes="0",
            seconds="0",
            timezone=UTC,
        ),
    }

    @classmethod
    def get_reports_for_day(cls, date: datetime) -> list[tuple[str, datetime]]:
        """Get all reports scheduled for a specific day."""
        start = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=date.tzinfo)
        end = start + timedelta(days=1) - timedelta(seconds=1)

        reports = []
        for name, rule in cls.SCHEDULES.items():
            for dt in rule.generate(start, end):
                reports.append((name, dt))

        return sorted(reports, key=lambda x: x[1])


# Check what reports run on a specific day
check_date = datetime(2025, 4, 1, tzinfo=UTC)  # April 1st (Tuesday, Q2 start)
print(f"\nReports scheduled for {check_date.strftime('%A, %B %d, %Y')}:")
for report_name, run_time in ReportSchedule.get_reports_for_day(check_date):
    print(f"  {run_time.strftime('%H:%M')} - {report_name}")
