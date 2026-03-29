# Datetime rule engine with a unified Rule concept.
# A Rule represents any recurring set of instants in time. It can be atomic
# (based on months, days, hours, etc.) or combined (using +, &, - operators).

import calendar
import json
import threading
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, timedelta, timezone
from datetime import datetime as _dt

# =====================================
# CONSTANTS
# =====================================

# Field Range Constants - valid ranges for datetime components
_MIN_MONTH = 1
_MAX_MONTH = 12
_MIN_DAY = 1
_MAX_DAY = 31
_MIN_WEEKDAY = 1
_MAX_WEEKDAY = 7  # 1=Monday, 7=Sunday
_MIN_HOUR = 0
_MAX_HOUR = 23
_MIN_MINUTE = 0
_MAX_MINUTE = 59
_MIN_SECOND = 0
_MAX_SECOND = 59
_MAX_NEGATIVE_DAY_OFFSET = -31  # Maximum negative offset for days

# Year Bounds Constants
_MIN_YEAR = 1
_MAX_YEAR = 9999

# Default Values
_DEFAULT_MONTHS_EXPR = "1..12"
_DEFAULT_DAYS_EXPR = "1..31"
_DEFAULT_WEEKDAYS_EXPR = "1..7"
_DEFAULT_HOURS_EXPR = "0..23"
_DEFAULT_MINUTES_EXPR = "0..59"
_DEFAULT_SECONDS_EXPR = "0..59"

# Configuration/Limits Constants
_DEFAULT_MAX_YEARS_SEARCH = 5  # Maximum years to search in get_next/get_prev
_MAX_JSON_SIZE = 1_000_000  # 1 MB - limit JSON size to prevent DOS
_MAX_RECURSION_DEPTH = 100  # Maximum nesting depth for combined rules
_DEFAULT_BATCH_SIZE = 10_000  # Default batch size for memory-efficient operations
_DEFAULT_MAX_GENERATE_ITEMS = None  # None = unlimited, set to prevent excessive generation

# Zeller's Congruence Constants (Algorithm-specific, do not modify)
_ZELLER_MONTH_ADJUSTMENT = 3  # January and February are treated as months 13-14 of previous year
_ZELLER_MONTHS_IN_YEAR = 12
_ZELLER_SATURDAY = 0  # Zeller's output: 0=Saturday
_ZELLER_WEEKDAY_OFFSET = 5  # Offset to convert Zeller to Python weekday
_ZELLER_WEEKDAY_MODULO = 7
_ZELLER_CENTURY_DIVISOR = 100

# Validation dummy year - must be a leap year to validate negative days against Feb 29
_VALIDATION_YEAR = 2024


# =====================================
# EXCEPTIONS
# =====================================


class RecurrentError(Exception):
    pass


class InvalidExpressionError(RecurrentError):
    pass


class InvalidRuleError(RecurrentError):
    pass


class NoMatchFoundError(RecurrentError):
    pass


# =====================================
# GENERAL UTILITIES
# =====================================


def _validate_datetime_bounds(dt: _dt) -> None:
    if not (_MIN_YEAR <= dt.year <= _MAX_YEAR):
        raise ValueError(f"Year {dt.year} outside supported range [{_MIN_YEAR}-{_MAX_YEAR}]")


# Normalize datetime to target timezone. Raises ValueError if target_tz is set but dt is naive.
def _normalize_timezone(dt: _dt, target_tz: timezone | None) -> _dt:
    if target_tz is None:
        return dt
    if dt.tzinfo is None:
        raise ValueError(
            f"Rule has timezone {target_tz} but received naive datetime {dt}. "
            "Please provide timezone-aware datetime or use a rule without timezone."
        )
    return dt.astimezone(target_tz)


def _get_days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


# Create datetime with timezone, handling DST transitions.
# Returns None for non-existent times (spring forward gap). Uses fold for ambiguous times.
def _create_datetime_with_tz(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
    tz: timezone | None,
    fold: int = 0,
) -> _dt | None:
    if tz is None:
        return _dt(year, month, day, hour, minute, second)

    dt = _dt(year, month, day, hour, minute, second, tzinfo=tz, fold=fold)

    # Detect non-existent times via UTC round-trip
    dt_utc = dt.utctimetuple()
    dt_from_utc = _dt(
        dt_utc.tm_year,
        dt_utc.tm_mon,
        dt_utc.tm_mday,
        dt_utc.tm_hour,
        dt_utc.tm_min,
        dt_utc.tm_sec,
        tzinfo=UTC,
    ).astimezone(tz)

    if dt_from_utc.hour != hour or dt_from_utc.minute != minute or dt_from_utc.second != second:
        return None

    return dt


# Calculate weekday using Zeller's congruence (without creating datetime object).
# Returns: 0=Monday, 1=Tuesday, ..., 6=Sunday (same as datetime.weekday()).
def _get_weekday(year: int, month: int, day: int) -> int:
    # For edge cases near minimum year, fall back to datetime to avoid year going to 0
    if year <= 1 and month < _ZELLER_MONTH_ADJUSTMENT:
        return _dt(year, month, day).weekday()

    if month < _ZELLER_MONTH_ADJUSTMENT:
        month += _ZELLER_MONTHS_IN_YEAR
        year -= 1
    k = year % _ZELLER_CENTURY_DIVISOR
    j = year // _ZELLER_CENTURY_DIVISOR
    h = (
        day + ((13 * (month + 1)) // 5) + k + (k // 4) + (j // 4) - (2 * j)
    ) % _ZELLER_WEEKDAY_MODULO
    return (h + _ZELLER_WEEKDAY_OFFSET) % _ZELLER_WEEKDAY_MODULO


# Calculate search boundary, handling leap year edge cases (Feb 29 -> Mar 1).
def _calculate_search_boundary(base: _dt, target_year: int) -> _dt:
    try:
        return base.replace(year=target_year)
    except ValueError:
        # Handle Feb 29 -> extend to Mar 1 to include all Feb 29s in search range
        return base.replace(year=target_year, month=3, day=1, hour=0, minute=0, second=0)


# =====================================
# DATA STRUCTURES
# =====================================


@dataclass
class ParsedFields:
    months: set[int]
    days: set[int]
    weekdays: set[int]
    hours: set[int]
    minutes: set[int]
    seconds: set[int]
    has_negative_days: bool = False


# =====================================
# CONFIGURATION
# =====================================


@dataclass
class RuleConfig:
    max_years_search: int = _DEFAULT_MAX_YEARS_SEARCH
    max_generate_items: int | None = _DEFAULT_MAX_GENERATE_ITEMS
    max_json_size: int = _MAX_JSON_SIZE
    max_recursion_depth: int = _MAX_RECURSION_DEPTH
    default_batch_size: int = _DEFAULT_BATCH_SIZE

    def __post_init__(self) -> None:
        if self.max_years_search <= 0:
            raise ValueError("max_years_search must be positive")
        if self.max_generate_items is not None and self.max_generate_items <= 0:
            raise ValueError("max_generate_items must be positive or None")
        if self.max_json_size <= 0:
            raise ValueError("max_json_size must be positive")
        if self.max_recursion_depth <= 0:
            raise ValueError("max_recursion_depth must be positive")
        if self.default_batch_size <= 0:
            raise ValueError("default_batch_size must be positive")


# Context variable for configuration (inherits to child threads and async tasks)
_CONFIG: ContextVar[RuleConfig] = ContextVar("rule_config")


def get_config() -> RuleConfig:
    try:
        return _CONFIG.get()
    except LookupError:
        return RuleConfig()


def set_global_config(config: RuleConfig) -> None:
    _CONFIG.set(config)


def reset_config() -> None:
    _CONFIG.set(RuleConfig())


# =====================================
# DSL PARSER (DOMAIN LOGIC)
# =====================================


# Parses DSL expressions into sets of integers.
# Supported: "3", "1..12", "0..59/5", "/5", "1,15,31", "1..12,!7", "-1" (negative days).
class DSLParser:
    @staticmethod
    def parse(
        expression: str,
        field_name: str,
        min_val: int,
        max_val: int,
        allow_negative: bool = False,
        year: int | None = None,
        month: int | None = None,
    ) -> set[int]:
        if not expression or not expression.strip():
            raise InvalidExpressionError(f"Empty expression in {field_name}")

        expression = expression.strip()
        parts = [p.strip() for p in expression.split(",")]
        included: set[int] = set()
        excluded: set[int] = set()

        for part in parts:
            if not part:
                continue
            target = excluded if part.startswith("!") else included
            parse_part = part[1:] if part.startswith("!") else part
            target.update(
                DSLParser._parse_part(
                    part=parse_part,
                    field_name=field_name,
                    min_val=min_val,
                    max_val=max_val,
                    allow_negative=allow_negative,
                    year=year,
                    month=month,
                )
            )

        if not included:
            included = set(range(min_val, max_val + 1))
        result = included - excluded

        if not result:
            if excluded and not included:
                raise InvalidExpressionError(
                    f"Expression '{expression}' in {field_name} has only exclusions with no inclusions. "
                    f"Specify values to include, e.g., '1..{max_val},!7' instead of just '!7'"
                )
            elif excluded == included:
                raise InvalidExpressionError(
                    f"Expression '{expression}' in {field_name} excludes all included values, "
                    f"resulting in empty set"
                )
            else:
                raise InvalidExpressionError(
                    f"Expression '{expression}' in {field_name} results in empty set"
                )

        return result

    @staticmethod
    def _parse_part(
        part: str,
        field_name: str,
        min_val: int,
        max_val: int,
        allow_negative: bool,
        year: int | None,
        month: int | None,
    ) -> set[int]:
        if part.startswith("/"):
            return DSLParser._parse_global_step(
                part=part, field_name=field_name, min_val=min_val, max_val=max_val
            )
        if ".." in part and "/" in part:
            return DSLParser._parse_range_with_step(
                part=part, field_name=field_name, min_val=min_val, max_val=max_val
            )
        if ".." in part:
            return DSLParser._parse_range(
                part=part, field_name=field_name, min_val=min_val, max_val=max_val
            )
        if allow_negative and part.startswith("-"):
            return DSLParser._parse_negative_day(
                part=part, field_name=field_name, year=year, month=month
            )
        return DSLParser._parse_value(
            part=part, field_name=field_name, min_val=min_val, max_val=max_val
        )

    @staticmethod
    def _parse_value(part: str, field_name: str, min_val: int, max_val: int) -> set[int]:
        try:
            val = int(part)
            if val < min_val or val > max_val:
                raise InvalidExpressionError(
                    f"Value {val} in {field_name} outside valid range [{min_val}..{max_val}]"
                )
            return {val}
        except ValueError as e:
            raise InvalidExpressionError(f"Invalid integer value '{part}' in {field_name}") from e

    @staticmethod
    def _parse_range(part: str, field_name: str, min_val: int, max_val: int) -> set[int]:
        try:
            start_str, end_str = part.split("..")
            start, end = int(start_str.strip()), int(end_str.strip())
            if start > end:
                raise InvalidExpressionError(f"Invalid range '{part}' in {field_name}: start > end")
            if start < min_val or end > max_val:
                raise InvalidExpressionError(
                    f"Range '{part}' in {field_name} outside valid bounds [{min_val}..{max_val}]"
                )
            return set(range(start, end + 1))
        except ValueError as e:
            if "invalid literal" in str(e):
                raise InvalidExpressionError(
                    f"Invalid range '{part}' in {field_name}: non-numeric values"
                ) from e
            raise

    @staticmethod
    def _parse_range_with_step(part: str, field_name: str, min_val: int, max_val: int) -> set[int]:
        try:
            range_part, step_str = part.split("/")
            start_str, end_str = range_part.split("..")
            start, end, step = int(start_str.strip()), int(end_str.strip()), int(step_str.strip())
            if step <= 0:
                raise InvalidExpressionError(f"Step in '{part}' must be positive in {field_name}")
            if start > end:
                raise InvalidExpressionError(f"Invalid range '{part}' in {field_name}: start > end")
            if start < min_val or end > max_val:
                raise InvalidExpressionError(
                    f"Range '{part}' in {field_name} outside valid bounds [{min_val}..{max_val}]"
                )
            return set(range(start, end + 1, step))
        except ValueError as e:
            if "invalid literal" in str(e) or "not enough values to unpack" in str(e):
                raise InvalidExpressionError(
                    f"Invalid range with step '{part}' in {field_name}"
                ) from e
            raise

    # Global step "/5" starts from first multiple of step >= min_val.
    @staticmethod
    def _parse_global_step(part: str, field_name: str, min_val: int, max_val: int) -> set[int]:
        try:
            step = int(part[1:].strip())
            if step <= 0:
                raise InvalidExpressionError(f"Step in '{part}' must be positive in {field_name}")
            # Calculate first multiple of step >= min_val
            first_value = 0 if min_val <= 0 else ((min_val + step - 1) // step) * step
            result: set[int] = set()
            i = first_value
            while i <= max_val:
                result.add(i)
                i += step
            return result
        except ValueError as e:
            raise InvalidExpressionError(f"Invalid step '{part}' in {field_name}") from e

    # Parse negative day: '-1' (last day), '-2' (second-to-last), etc.
    @staticmethod
    def _parse_negative_day(
        part: str, field_name: str, year: int | None, month: int | None
    ) -> set[int]:
        try:
            offset = int(part)
            if offset >= 0:
                raise InvalidExpressionError(f"Value '{part}' should be negative in {field_name}")
            if offset < _MAX_NEGATIVE_DAY_OFFSET:
                raise InvalidExpressionError(
                    f"Negative day offset '{part}' is invalid: no month has more than {_MAX_DAY} days. "
                    f"Valid range is -1 to {_MAX_NEGATIVE_DAY_OFFSET}"
                )
            if year is None or month is None:
                return {offset}
            last_day = calendar.monthrange(year, month)[1]
            actual_day = last_day + offset + 1
            if actual_day < 1:
                raise InvalidExpressionError(
                    f"Negative day offset '{part}' (={actual_day}) is too large for "
                    f"{calendar.month_name[month]} which has only {last_day} days"
                )
            return {actual_day}
        except ValueError as e:
            raise InvalidExpressionError(f"Invalid negative day '{part}' in {field_name}") from e


# =====================================
# CORE LIBRARY / PUBLIC API
# =====================================


class Rule(ABC):
    # Abstract base class for all rules. A Rule represents any recurring set of instants in time.

    __slots__ = ()

    # Get next datetime matching this rule after base. Raises NoMatchFoundError if not found.
    def get_next(self, base: _dt, max_years: int | None = None) -> _dt:
        _validate_datetime_bounds(dt=base)
        if max_years is None:
            max_years = get_config().max_years_search

        search_start = base + timedelta(seconds=1)
        target_year = min(base.year + max_years, _MAX_YEAR)
        search_end = _calculate_search_boundary(base, target_year)

        for dt in self.generate(search_start, search_end):
            return dt
        raise NoMatchFoundError(f"No next match found within {max_years} years from {base}")

    # Get previous datetime matching this rule before base. Raises NoMatchFoundError if not found.
    def get_prev(self, base: _dt, max_years: int | None = None) -> _dt:
        _validate_datetime_bounds(dt=base)
        if max_years is None:
            max_years = get_config().max_years_search

        target_year = max(base.year - max_years, _MIN_YEAR)
        search_start = _calculate_search_boundary(base, target_year)
        search_end = base - timedelta(seconds=1)

        for dt in self.generate_reverse(search_start, search_end):
            return dt
        raise NoMatchFoundError(f"No previous match found within {max_years} years from {base}")

    @abstractmethod
    def generate(self, start: _dt, end: _dt) -> Generator[_dt, None, None]:
        # Generate all datetimes matching this rule between start and end (inclusive).
        pass

    @abstractmethod
    def generate_reverse(self, start: _dt, end: _dt) -> Generator[_dt, None, None]:
        # Generate all datetimes matching this rule between start and end in reverse order.
        pass

    # Generate datetimes in batches for memory-efficient processing.
    def generate_batch(
        self, start: _dt, end: _dt, batch_size: int | None = None
    ) -> Generator[list[_dt], None, None]:
        if batch_size is None:
            batch_size = get_config().default_batch_size
        batch: list[_dt] = []
        for dt in self.generate(start, end):
            batch.append(dt)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    @abstractmethod
    def to_json(self) -> str:
        # Serialize rule to JSON string.
        pass

    # Deserialize rule from JSON string. Detects type and delegates to appropriate method.
    @staticmethod
    def from_json(json_str: str) -> "Rule":
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("JSON must be an object/dict")

        rule_type = data.get("type")

        if rule_type == "atomic":
            return AtomicRule.from_json(json_str)
        if rule_type == "combined":
            return CombinedRule.from_json(json_str, _depth=0)
        raise ValueError(f"Unknown rule type: {rule_type}")

    # Union operator: r1 + r2 matches when either r1 OR r2 matches.
    def __add__(self, other: "Rule") -> "Rule":
        return CombinedRule(self, other, "union")

    # Intersection operator: r1 & r2 matches when both r1 AND r2 match.
    def __and__(self, other: "Rule") -> "Rule":
        return CombinedRule(self, other, "intersection")

    # Difference operator: r1 - r2 matches when r1 matches but r2 doesn't.
    def __sub__(self, other: "Rule") -> "Rule":
        return CombinedRule(self, other, "difference")


class AtomicRule(Rule):
    # Atomic rule based on temporal constraints using DSL syntax.
    # DSL: "3", "1..12", "0..59/5", "/15", "1,15,31", "1..12,!7,!8", "-1" (last day).
    # Semantic: ALL constraints must be satisfied (AND logic).

    __slots__ = (
        "_months_expr",
        "_days_expr",
        "_weekdays_expr",
        "_hours_expr",
        "_minutes_expr",
        "_seconds_expr",
        "_timezone",
        "_parsed_cache",
        "_has_negative_days",
        "_cache_lock",
    )

    def __init__(
        self,
        months: str = _DEFAULT_MONTHS_EXPR,
        days: str = _DEFAULT_DAYS_EXPR,
        weekdays: str = _DEFAULT_WEEKDAYS_EXPR,  # 1=Monday, 7=Sunday
        hours: str = _DEFAULT_HOURS_EXPR,
        minutes: str = _DEFAULT_MINUTES_EXPR,
        seconds: str = _DEFAULT_SECONDS_EXPR,
        timezone: timezone | None = None,
    ):
        self._months_expr = months
        self._days_expr = days
        self._weekdays_expr = weekdays
        self._hours_expr = hours
        self._minutes_expr = minutes
        self._seconds_expr = seconds
        self._timezone = timezone

        self._parsed_cache: ParsedFields | None = None
        self._has_negative_days = "-" in days
        self._cache_lock = threading.Lock()

        self._validate()

    def _validate(self) -> None:
        # Note: Negative day validation (e.g., "-30") is done against January (31 days)
        # at construction time. For shorter months (e.g., February with 28/29 days),
        # validation happens at generate time and may raise InvalidExpressionError.
        try:
            DSLParser.parse(
                expression=self._months_expr,
                field_name="months",
                min_val=_MIN_MONTH,
                max_val=_MAX_MONTH,
            )
            # Days might have negative values - validate syntax with dummy year/month (January)
            self._parse_days_expr(year=_VALIDATION_YEAR, month=_MIN_MONTH)
            DSLParser.parse(
                expression=self._weekdays_expr,
                field_name="weekdays",
                min_val=_MIN_WEEKDAY,
                max_val=_MAX_WEEKDAY,
            )
            DSLParser.parse(
                expression=self._hours_expr,
                field_name="hours",
                min_val=_MIN_HOUR,
                max_val=_MAX_HOUR,
            )
            DSLParser.parse(
                expression=self._minutes_expr,
                field_name="minutes",
                min_val=_MIN_MINUTE,
                max_val=_MAX_MINUTE,
            )
            DSLParser.parse(
                expression=self._seconds_expr,
                field_name="seconds",
                min_val=_MIN_SECOND,
                max_val=_MAX_SECOND,
            )
        except InvalidExpressionError as e:
            raise InvalidRuleError(f"Invalid rule expression: {e}") from e

    def _parse_days_expr(self, year: int, month: int) -> set[int]:
        return DSLParser.parse(
            expression=self._days_expr,
            field_name="days",
            min_val=_MIN_DAY,
            max_val=_MAX_DAY,
            allow_negative=True,
            year=year,
            month=month,
        )

    def _parse_fields(self, year: int, month: int) -> ParsedFields:
        # Fast path: return cached result without lock
        if not self._has_negative_days and self._parsed_cache is not None:
            return self._parsed_cache

        # Double-checked locking for thread-safe caching
        with self._cache_lock:
            # Check again inside lock (another thread may have populated cache)
            if not self._has_negative_days and self._parsed_cache is not None:
                return self._parsed_cache

            return self._parse_fields_impl(year, month)

    # Internal implementation of field parsing. Called within lock.
    def _parse_fields_impl(self, year: int, month: int) -> ParsedFields:
        months = DSLParser.parse(
            expression=self._months_expr,
            field_name="months",
            min_val=_MIN_MONTH,
            max_val=_MAX_MONTH,
        )
        days_raw = self._parse_days_expr(year=year, month=month)

        # Check if we have negative days
        has_negative = any(d < _MIN_DAY for d in days_raw)

        # Resolve negative days
        days = set()
        for d in days_raw:
            if d < _MIN_DAY:
                last_day = _get_days_in_month(year=year, month=month)
                actual_day = last_day + d + 1
                if actual_day >= _MIN_DAY:
                    days.add(actual_day)
            else:
                days.add(d)

        weekdays_user = DSLParser.parse(
            expression=self._weekdays_expr,
            field_name="weekdays",
            min_val=_MIN_WEEKDAY,
            max_val=_MAX_WEEKDAY,
        )
        # Convert from 1-7 (Mon-Sun) to 0-6 (Mon-Sun) for datetime.weekday()
        weekdays = {(w - 1) % _ZELLER_WEEKDAY_MODULO for w in weekdays_user}

        hours = DSLParser.parse(
            expression=self._hours_expr, field_name="hours", min_val=_MIN_HOUR, max_val=_MAX_HOUR
        )
        minutes = DSLParser.parse(
            expression=self._minutes_expr,
            field_name="minutes",
            min_val=_MIN_MINUTE,
            max_val=_MAX_MINUTE,
        )
        seconds = DSLParser.parse(
            expression=self._seconds_expr,
            field_name="seconds",
            min_val=_MIN_SECOND,
            max_val=_MAX_SECOND,
        )

        result = ParsedFields(
            months=months,
            days=days,
            weekdays=weekdays,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            has_negative_days=has_negative,
        )

        # Cache result if no negative days
        if not self._has_negative_days and self._parsed_cache is None:
            self._parsed_cache = result

        return result

    def generate(
        self, start: _dt, end: _dt, max_items: int | None = None
    ) -> Generator[_dt, None, None]:
        if start > end:
            raise ValueError(f"Start {start} must be <= end {end}")

        _validate_datetime_bounds(dt=start)
        _validate_datetime_bounds(dt=end)

        # Get max_items from config if not specified
        if max_items is None:
            max_items = get_config().max_generate_items

        # Normalize to rule timezone if specified
        start = _normalize_timezone(dt=start, target_tz=self._timezone)
        end = _normalize_timezone(dt=end, target_tz=self._timezone)

        generated_count = 0

        # Iterate through years and months
        for year in range(start.year, end.year + 1):
            month_start = start.month if year == start.year else 1
            month_end = end.month if year == end.year else 12

            for month in range(month_start, month_end + 1):
                # Parse fields with current year/month context
                fields = self._parse_fields(year=year, month=month)

                # Skip month if not in constraint
                if month not in fields.months:
                    continue

                # Get valid days for this month
                days_in_month = _get_days_in_month(year=year, month=month)
                valid_days = [d for d in fields.days if 1 <= d <= days_in_month]

                # Pre-compute time combinations
                time_combos = [
                    (h, m, s)
                    for h in sorted(fields.hours)
                    for m in sorted(fields.minutes)
                    for s in sorted(fields.seconds)
                ]

                for day in sorted(valid_days):
                    # Check weekday constraint (using fast algorithm)
                    weekday = _get_weekday(year=year, month=month, day=day)
                    if weekday not in fields.weekdays:
                        continue

                    for hour, minute, second in time_combos:
                        # Create datetime with DST handling
                        dt = _create_datetime_with_tz(
                            year, month, day, hour, minute, second, self._timezone
                        )

                        # Skip non-existent times (DST spring forward gap)
                        if dt is None:
                            continue

                        if start <= dt <= end:
                            # Check max_items limit before yielding
                            generated_count += 1
                            if max_items is not None and generated_count > max_items:
                                raise ValueError(
                                    f"Maximum generation limit of {max_items} items exceeded. "
                                    f"Adjust max_generate_items in RuleConfig or pass max_items parameter."
                                )
                            yield dt

    def generate_reverse(
        self, start: _dt, end: _dt, max_items: int | None = None
    ) -> Generator[_dt, None, None]:
        if start > end:
            raise ValueError(f"Start {start} must be <= end {end}")

        _validate_datetime_bounds(dt=start)
        _validate_datetime_bounds(dt=end)

        if max_items is None:
            max_items = get_config().max_generate_items

        start = _normalize_timezone(dt=start, target_tz=self._timezone)
        end = _normalize_timezone(dt=end, target_tz=self._timezone)

        generated_count = 0

        # Iterate through years and months in reverse
        for year in range(end.year, start.year - 1, -1):
            month_start = start.month if year == start.year else 1
            month_end = end.month if year == end.year else 12

            for month in range(month_end, month_start - 1, -1):
                fields = self._parse_fields(year=year, month=month)

                if month not in fields.months:
                    continue

                days_in_month = _get_days_in_month(year=year, month=month)
                valid_days = [d for d in fields.days if 1 <= d <= days_in_month]

                # Pre-compute time combinations in reverse order
                time_combos = [
                    (h, m, s)
                    for h in sorted(fields.hours, reverse=True)
                    for m in sorted(fields.minutes, reverse=True)
                    for s in sorted(fields.seconds, reverse=True)
                ]

                for day in sorted(valid_days, reverse=True):
                    weekday = _get_weekday(year=year, month=month, day=day)
                    if weekday not in fields.weekdays:
                        continue

                    for hour, minute, second in time_combos:
                        # Create datetime with DST handling
                        dt = _create_datetime_with_tz(
                            year, month, day, hour, minute, second, self._timezone
                        )

                        # Skip non-existent times (DST spring forward gap)
                        if dt is None:
                            continue

                        if start <= dt <= end:
                            generated_count += 1
                            if max_items is not None and generated_count > max_items:
                                raise ValueError(
                                    f"Maximum generation limit of {max_items} items exceeded. "
                                    f"Adjust max_generate_items in RuleConfig or pass max_items parameter."
                                )
                            yield dt

    def with_months(self, months: str) -> "AtomicRule":
        return AtomicRule(
            months=months,
            days=self._days_expr,
            weekdays=self._weekdays_expr,
            hours=self._hours_expr,
            minutes=self._minutes_expr,
            seconds=self._seconds_expr,
            timezone=self._timezone,
        )

    def with_days(self, days: str) -> "AtomicRule":
        return AtomicRule(
            months=self._months_expr,
            days=days,
            weekdays=self._weekdays_expr,
            hours=self._hours_expr,
            minutes=self._minutes_expr,
            seconds=self._seconds_expr,
            timezone=self._timezone,
        )

    def with_weekdays(self, weekdays: str) -> "AtomicRule":
        return AtomicRule(
            months=self._months_expr,
            days=self._days_expr,
            weekdays=weekdays,
            hours=self._hours_expr,
            minutes=self._minutes_expr,
            seconds=self._seconds_expr,
            timezone=self._timezone,
        )

    def with_hours(self, hours: str) -> "AtomicRule":
        return AtomicRule(
            months=self._months_expr,
            days=self._days_expr,
            weekdays=self._weekdays_expr,
            hours=hours,
            minutes=self._minutes_expr,
            seconds=self._seconds_expr,
            timezone=self._timezone,
        )

    def with_minutes(self, minutes: str) -> "AtomicRule":
        return AtomicRule(
            months=self._months_expr,
            days=self._days_expr,
            weekdays=self._weekdays_expr,
            hours=self._hours_expr,
            minutes=minutes,
            seconds=self._seconds_expr,
            timezone=self._timezone,
        )

    def with_seconds(self, seconds: str) -> "AtomicRule":
        return AtomicRule(
            months=self._months_expr,
            days=self._days_expr,
            weekdays=self._weekdays_expr,
            hours=self._hours_expr,
            minutes=self._minutes_expr,
            seconds=seconds,
            timezone=self._timezone,
        )

    def with_timezone(self, tz: timezone | None) -> "AtomicRule":
        return AtomicRule(
            months=self._months_expr,
            days=self._days_expr,
            weekdays=self._weekdays_expr,
            hours=self._hours_expr,
            minutes=self._minutes_expr,
            seconds=self._seconds_expr,
            timezone=tz,
        )

    def to_json(self) -> str:
        data = {
            "type": "atomic",
            "months": self._months_expr,
            "days": self._days_expr,
            "weekdays": self._weekdays_expr,
            "hours": self._hours_expr,
            "minutes": self._minutes_expr,
            "seconds": self._seconds_expr,
            "timezone": str(self._timezone) if self._timezone else None,
        }
        return json.dumps(data)

    @staticmethod
    def from_json(json_str: str) -> "AtomicRule":
        max_json_size = get_config().max_json_size
        if len(json_str) > max_json_size:
            raise ValueError(f"JSON too large: {len(json_str)} bytes (max {max_json_size})")

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        # Validate structure
        if not isinstance(data, dict):
            raise ValueError("JSON must be an object/dict")

        if data.get("type") != "atomic":
            raise ValueError(f"Expected atomic rule, got {data.get('type')}")

        # Validate required fields with type checking
        required_fields = ["months", "days", "weekdays", "hours", "minutes", "seconds"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
            if not isinstance(data[field], str):
                raise ValueError(
                    f"Field '{field}' must be a string, got {type(data[field]).__name__}"
                )

        tz = None
        if data.get("timezone"):
            # Parse timezone string (e.g., "UTC+01:00")
            tz_str = data["timezone"]
            if not isinstance(tz_str, str):
                raise ValueError(f"Timezone must be a string, got {type(tz_str).__name__}")

            # Special case for UTC
            if tz_str == "UTC":
                tz = UTC
            else:
                # Parse offset-based timezone (e.g., "UTC+01:00", "UTC-05:30")
                try:
                    if not tz_str.startswith("UTC"):
                        raise ValueError(f"Timezone must start with 'UTC', got '{tz_str}'")

                    offset_str = tz_str[3:]  # Remove "UTC" prefix
                    if not offset_str:
                        raise ValueError("Missing offset after 'UTC'")

                    # Parse sign
                    sign = 1
                    if offset_str[0] == "+":
                        sign = 1
                        offset_str = offset_str[1:]
                    elif offset_str[0] == "-":
                        sign = -1
                        offset_str = offset_str[1:]
                    else:
                        raise ValueError(
                            f"Invalid offset format: '{tz_str}'. "
                            f"Expected format 'UTC+HH:MM' or 'UTC-HH:MM', got no sign character."
                        )

                    # Parse HH:MM
                    parts = offset_str.split(":")
                    if len(parts) != 2:
                        raise ValueError(f"Offset must be in HH:MM format, got '{offset_str}'")

                    hours = int(parts[0])
                    minutes = int(parts[1])

                    # Validate ranges
                    if not (0 <= hours <= 23):
                        raise ValueError(f"Hours must be 0-23, got {hours}")
                    if not (0 <= minutes <= 59):
                        raise ValueError(f"Minutes must be 0-59, got {minutes}")

                    # Create timezone with offset
                    total_offset = timedelta(hours=sign * hours, minutes=sign * minutes)
                    tz = timezone(total_offset)

                except (ValueError, IndexError) as e:
                    raise ValueError(f"Invalid timezone string '{tz_str}': {e}") from e

        return AtomicRule(
            months=data["months"],
            days=data["days"],
            weekdays=data["weekdays"],
            hours=data["hours"],
            minutes=data["minutes"],
            seconds=data["seconds"],
            timezone=tz,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AtomicRule):
            return NotImplemented
        return (
            self._months_expr == other._months_expr
            and self._days_expr == other._days_expr
            and self._weekdays_expr == other._weekdays_expr
            and self._hours_expr == other._hours_expr
            and self._minutes_expr == other._minutes_expr
            and self._seconds_expr == other._seconds_expr
            and self._timezone == other._timezone
        )

    def __hash__(self) -> int:
        return hash(
            (
                self._months_expr,
                self._days_expr,
                self._weekdays_expr,
                self._hours_expr,
                self._minutes_expr,
                self._seconds_expr,
                str(self._timezone) if self._timezone else None,
            )
        )


class CombinedRule(Rule):
    # Rule combining two rules: union (+), intersection (&), difference (-).

    __slots__ = ("_left", "_right", "_operator")

    def __init__(self, left: Rule, right: Rule, operator: str):
        if operator not in ("union", "intersection", "difference"):
            raise ValueError(f"Invalid operator: {operator}")

        # Validate timezone consistency to prevent TypeError when comparing datetimes
        left_tz = self._get_rule_timezone(left)
        right_tz = self._get_rule_timezone(right)

        # Check if one rule is tz-aware and the other is tz-naive
        if (
            left_tz != "unknown"
            and right_tz != "unknown"
            and (left_tz is None) != (right_tz is None)
        ):
            raise InvalidRuleError(
                "Cannot combine timezone-aware and timezone-naive rules. "
                f"Left rule has timezone={left_tz}, right rule has timezone={right_tz}"
            )

        self._left = left
        self._right = right
        self._operator = operator

    # Get timezone from a rule. Returns 'unknown' for nested CombinedRules.
    @staticmethod
    def _get_rule_timezone(rule: Rule) -> timezone | None | str:
        if isinstance(rule, AtomicRule):
            return rule._timezone
        if isinstance(rule, CombinedRule):
            # For combined rules, recursively check both sides
            left_tz = CombinedRule._get_rule_timezone(rule._left)
            right_tz = CombinedRule._get_rule_timezone(rule._right)
            # If both are the same (including both None or both same tz), return that
            if left_tz == right_tz:
                return left_tz
            # If one is unknown, return the other
            if left_tz == "unknown":
                return right_tz
            if right_tz == "unknown":
                return left_tz
            # Mixed - return unknown to allow the validation to pass
            # (it was already validated when the nested CombinedRule was created)
            return "unknown"
        return "unknown"

    def generate(self, start: _dt, end: _dt) -> Generator[_dt, None, None]:
        if start > end:
            raise ValueError(f"Start {start} must be <= end {end}")

        if self._operator == "union":
            # Merge two sorted streams chronologically with O(1) memory
            left_gen = self._left.generate(start, end)
            right_gen = self._right.generate(start, end)
            left_val = next(left_gen, None)
            right_val = next(right_gen, None)

            while left_val is not None or right_val is not None:
                if left_val is None:
                    assert right_val is not None  # Guaranteed by while condition
                    yield right_val
                    right_val = next(right_gen, None)
                elif right_val is None or left_val < right_val:
                    yield left_val
                    left_val = next(left_gen, None)
                elif right_val < left_val:
                    yield right_val
                    right_val = next(right_gen, None)
                else:  # left_val == right_val (duplicate)
                    yield left_val
                    left_val = next(left_gen, None)
                    right_val = next(right_gen, None)

        elif self._operator == "intersection":
            for left_batch in self._left.generate_batch(start, end):
                if left_batch:
                    batch_start = left_batch[0]
                    batch_end = left_batch[-1]
                    right_matches = set(self._right.generate(batch_start, batch_end))
                    for dt in left_batch:
                        if dt in right_matches:
                            yield dt

        elif self._operator == "difference":
            for left_batch in self._left.generate_batch(start, end):
                if left_batch:
                    batch_start = left_batch[0]
                    batch_end = left_batch[-1]
                    right_matches = set(self._right.generate(batch_start, batch_end))
                    for dt in left_batch:
                        if dt not in right_matches:
                            yield dt

    def generate_reverse(self, start: _dt, end: _dt) -> Generator[_dt, None, None]:
        if start > end:
            raise ValueError(f"Start {start} must be <= end {end}")

        if self._operator == "union":
            # Merge two reverse-sorted streams with O(1) memory
            left_gen = self._left.generate_reverse(start, end)
            right_gen = self._right.generate_reverse(start, end)
            left_val = next(left_gen, None)
            right_val = next(right_gen, None)

            while left_val is not None or right_val is not None:
                if left_val is None:
                    assert right_val is not None  # Guaranteed by while condition
                    yield right_val
                    right_val = next(right_gen, None)
                elif right_val is None or left_val > right_val:
                    yield left_val
                    left_val = next(left_gen, None)
                elif right_val > left_val:
                    yield right_val
                    right_val = next(right_gen, None)
                else:  # left_val == right_val (duplicate)
                    yield left_val
                    left_val = next(left_gen, None)
                    right_val = next(right_gen, None)

        elif self._operator == "intersection":
            # Collect results and yield in reverse
            # For efficiency, we iterate left in reverse and check against right
            for dt in self._left.generate_reverse(start, end):
                # Check if dt is in right rule (single point check)
                for right_dt in self._right.generate(dt, dt):
                    if right_dt == dt:
                        yield dt
                        break

        elif self._operator == "difference":
            # Iterate left in reverse, exclude if in right
            for dt in self._left.generate_reverse(start, end):
                # Check if dt is NOT in right rule
                found_in_right = False
                for right_dt in self._right.generate(dt, dt):
                    if right_dt == dt:
                        found_in_right = True
                        break
                if not found_in_right:
                    yield dt

    def to_json(self) -> str:
        data = {
            "type": "combined",
            "operator": self._operator,
            "left": json.loads(self._left.to_json()),
            "right": json.loads(self._right.to_json()),
        }
        return json.dumps(data)

    # Parse a subrule from JSON data.
    @staticmethod
    def _parse_subrule(rule_data: dict, depth: int) -> Rule:
        json_str = json.dumps(rule_data)
        rule_type = rule_data.get("type")
        if rule_type == "atomic":
            return AtomicRule.from_json(json_str)
        if rule_type == "combined":
            return CombinedRule.from_json(json_str, depth + 1)
        raise ValueError(f"Unknown rule type: {rule_type}")

    @staticmethod
    def from_json(json_str: str, _depth: int = 0) -> "CombinedRule":
        max_recursion = get_config().max_recursion_depth
        if _depth > max_recursion:
            raise ValueError(f"JSON nesting too deep: exceeds {max_recursion} levels")

        max_json_size = get_config().max_json_size
        if _depth == 0 and len(json_str) > max_json_size:
            raise ValueError(f"JSON too large: {len(json_str)} bytes (max {max_json_size})")

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("JSON must be an object/dict")

        if data.get("type") != "combined":
            raise ValueError(f"Expected combined rule, got {data.get('type')}")

        if "operator" not in data:
            raise ValueError("Missing required field: operator")
        if "left" not in data or "right" not in data:
            raise ValueError("Missing required fields: left and/or right")

        if not isinstance(data["operator"], str):
            raise ValueError(f"Operator must be string, got {type(data['operator']).__name__}")

        left = CombinedRule._parse_subrule(data["left"], _depth)
        right = CombinedRule._parse_subrule(data["right"], _depth)

        return CombinedRule(left, right, data["operator"])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CombinedRule):
            return NotImplemented
        return (
            self._operator == other._operator
            and self._left == other._left
            and self._right == other._right
        )

    def __hash__(self) -> int:
        return hash((self._operator, self._left, self._right))
