from datetime import UTC, datetime, timedelta, timezone

import pytest

from zerotime import (
    AtomicRule,
    InvalidRuleError,
    NoMatchFoundError,
)

# ---- Basic AtomicRule Tests ----


def test_single_match():
    """Test matching a single specific datetime."""
    rule = AtomicRule(
        months="11",
        days="11",
        weekdays="2",  # Tuesday
        hours="14",
        minutes="30",
        seconds="0",
    )
    start = datetime(2025, 11, 11, 14, 30, 0)
    end = datetime(2025, 11, 11, 14, 30, 0)

    results = list(rule.generate(start, end))

    assert len(results) == 1
    assert results[0] == start


def test_step_minutes_seconds():
    """Test step expressions in minutes and seconds."""
    rule = AtomicRule(
        months="11",
        days="11",
        weekdays="2",
        hours="14",
        minutes="/15",  # Every 15 minutes
        seconds="/30",  # Every 30 seconds
    )
    start = datetime(2025, 11, 11, 14, 0, 0)
    end = datetime(2025, 11, 11, 14, 59, 59)

    results = list(rule.generate(start, end))

    assert len(results) == 8
    for dt in results:
        assert dt.minute in (0, 15, 30, 45)
        assert dt.second in (0, 30)


def test_range_with_step():
    """Test range with step expression."""
    rule = AtomicRule(
        months="11",
        days="11",
        weekdays="2",
        hours="14",
        minutes="0..30/10",  # 0, 10, 20, 30
        seconds="0",
    )
    start = datetime(2025, 11, 11, 14, 0, 0)
    end = datetime(2025, 11, 11, 14, 59, 59)

    results = list(rule.generate(start, end))

    assert len(results) == 4
    assert [dt.minute for dt in results] == [0, 10, 20, 30]


def test_list_expression():
    """Test comma-separated list expression."""
    rule = AtomicRule(
        months="11",
        days="11",
        weekdays="2",
        hours="14",
        minutes="0,15,30,45",
        seconds="0",
    )
    start = datetime(2025, 11, 11, 14, 0, 0)
    end = datetime(2025, 11, 11, 14, 59, 59)

    results = list(rule.generate(start, end))

    assert len(results) == 4
    assert [dt.minute for dt in results] == [0, 15, 30, 45]


def test_exclusion_expression():
    """Test exclusion with ! operator."""
    rule = AtomicRule(
        months="1..12,!7,!8",  # All months except July and August
        days="1",
        hours="12",
        minutes="0",
        seconds="0",
    )
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 12, 31, 23, 59, 59)

    results = list(rule.generate(start, end))

    # Should have 10 matches (12 months - 2 excluded)
    assert len(results) == 10
    months_matched = {dt.month for dt in results}
    assert 7 not in months_matched
    assert 8 not in months_matched


def test_negative_days():
    """Test negative day values for last day of month."""
    rule = AtomicRule(
        months="1,2,3",  # January, February, March
        days="-1",  # Last day of month
        hours="12",
        minutes="0",
        seconds="0",
    )
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 3, 31, 23, 59, 59)

    results = list(rule.generate(start, end))

    assert len(results) == 3
    assert results[0].day == 31  # Jan 31
    assert results[1].day == 28  # Feb 28 (2025 is not a leap year)
    assert results[2].day == 31  # Mar 31


def test_negative_days_leap_year():
    """Test negative day values in a leap year."""
    rule = AtomicRule(
        months="2",
        days="-1",  # Last day of February
        hours="12",
        minutes="0",
        seconds="0",
    )
    start = datetime(2024, 2, 1, 0, 0, 0)
    end = datetime(2024, 2, 29, 23, 59, 59)

    results = list(rule.generate(start, end))

    assert len(results) == 1
    assert results[0].day == 29  # Feb 29 in leap year


def test_invalid_day_skipped():
    """Test that invalid days (e.g., day 31 in month with 30 days) are skipped."""
    rule = AtomicRule(
        months="11",  # November has 30 days
        days="31",
        hours="14",
        minutes="0",
        seconds="0",
    )
    start = datetime(2025, 11, 1, 0, 0, 0)
    end = datetime(2025, 11, 30, 23, 59, 59)

    results = list(rule.generate(start, end))
    assert len(results) == 0


@pytest.mark.parametrize(
    "weekdays, expected_weekdays",
    [
        ("1", [0]),  # Monday
        ("7", [6]),  # Sunday
        ("1..5", [0, 1, 2, 3, 4]),  # Weekdays
        ("6,7", [5, 6]),  # Weekend
    ],
)
def test_weekday_expressions(weekdays, expected_weekdays):
    """Test various weekday expressions."""
    rule = AtomicRule(
        months="11",
        days="10..16",  # Week of Nov 10-16, 2025
        weekdays=weekdays,
        hours="12",
        minutes="0",
        seconds="0",
    )
    start = datetime(2025, 11, 10, 0, 0, 0)
    end = datetime(2025, 11, 16, 23, 59, 59)

    results = list(rule.generate(start, end))

    actual_weekdays = {dt.weekday() for dt in results}
    assert actual_weekdays == set(expected_weekdays)


# ---- Temporal Methods Tests ----


def test_get_next():
    """Test get_next method."""
    rule = AtomicRule(
        months="11",
        days="11",
        weekdays="2",
        hours="14",
        minutes="0,30",
        seconds="0",
    )
    base = datetime(2025, 11, 11, 13, 45, 0)
    expected = datetime(2025, 11, 11, 14, 0, 0)

    assert rule.get_next(base) == expected


def test_get_prev():
    """Test get_prev method."""
    rule = AtomicRule(
        months="11",
        days="11",
        weekdays="2",
        hours="14",
        minutes="0,30",
        seconds="0",
    )
    base = datetime(2025, 11, 11, 14, 15, 0)
    expected = datetime(2025, 11, 11, 14, 0, 0)

    assert rule.get_prev(base) == expected


def test_get_next_across_days():
    """Test get_next across day boundaries."""
    rule = AtomicRule(
        months="11",
        days="11,12",
        weekdays="2,3",
        hours="0",
        minutes="0",
        seconds="0",
    )
    base = datetime(2025, 11, 11, 23, 59, 59)
    expected = datetime(2025, 11, 12, 0, 0, 0)

    assert rule.get_next(base) == expected


def test_get_prev_across_days():
    """Test get_prev across day boundaries."""
    rule = AtomicRule(
        months="11",
        days="11,12",
        weekdays="2,3",
        hours="23",
        minutes="0",
        seconds="0",
    )
    base = datetime(2025, 11, 12, 0, 0, 0)
    expected = datetime(2025, 11, 11, 23, 0, 0)

    assert rule.get_prev(base) == expected


def test_get_next_not_found():
    """Test get_next raises exception when no match found."""
    rule = AtomicRule(
        months="1",
        days="1",
        weekdays="3",  # Wednesday
        hours="0",
        minutes="0",
        seconds="0",
    )
    base = datetime(2090, 1, 2)  # Far in future

    with pytest.raises(NoMatchFoundError):
        rule.get_next(base)


def test_get_prev_not_found():
    """Test get_prev raises exception when no match found."""
    rule = AtomicRule(
        months="2",
        days="30",  # Invalid day for February
        hours="0",
        minutes="0",
        seconds="0",
    )
    base = datetime(1900, 1, 1)

    with pytest.raises(NoMatchFoundError):
        rule.get_prev(base)


def test_generate_batch():
    """Test generate_batch method."""
    rule = AtomicRule(
        months="11",
        days="11",
        weekdays="2",
        hours="14",
        minutes="/1",  # Every minute
        seconds="0",
    )
    start = datetime(2025, 11, 11, 14, 0, 0)
    end = datetime(2025, 11, 11, 14, 59, 59)

    batches = list(rule.generate_batch(start, end, batch_size=10))

    assert len(batches) == 6  # 60 minutes / 10 per batch
    assert len(batches[0]) == 10
    assert len(batches[-1]) == 10


# ---- Immutable with_* Methods Tests ----


def test_with_months():
    """Test with_months returns new rule."""
    rule = AtomicRule(months="1")
    new_rule = rule.with_months("12")

    assert rule._months_expr == "1"
    assert new_rule._months_expr == "12"


def test_with_days():
    """Test with_days returns new rule."""
    rule = AtomicRule(days="1")
    new_rule = rule.with_days("-1")

    assert rule._days_expr == "1"
    assert new_rule._days_expr == "-1"


def test_with_timezone():
    """Test with_timezone returns new rule."""
    tz1 = UTC
    rule = AtomicRule(timezone=tz1)
    new_rule = rule.with_timezone(None)

    assert rule._timezone == tz1
    assert new_rule._timezone is None


# ---- Combination Operators Tests ----


def test_union_operator():
    """Test + (union) operator."""
    rule1 = AtomicRule(months="1", days="1", hours="12", minutes="0", seconds="0")
    rule2 = AtomicRule(months="1", days="2", hours="12", minutes="0", seconds="0")

    combined = rule1 + rule2

    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 1, 2, 23, 59, 59)

    results = list(combined.generate(start, end))

    assert len(results) == 2
    assert results[0].day == 1
    assert results[1].day == 2


def test_intersection_operator():
    """Test & (intersection) operator."""
    rule1 = AtomicRule(months="1", days="1..31", hours="12", minutes="0", seconds="0")
    rule2 = AtomicRule(months="1", days="15", hours="12", minutes="0", seconds="0")

    combined = rule1 & rule2

    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 1, 31, 23, 59, 59)

    results = list(combined.generate(start, end))

    assert len(results) == 1
    assert results[0].day == 15


def test_difference_operator():
    """Test - (difference) operator."""
    rule1 = AtomicRule(months="1", days="1..5", hours="12", minutes="0", seconds="0")
    rule2 = AtomicRule(months="1", days="3", hours="12", minutes="0", seconds="0")

    combined = rule1 - rule2

    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 1, 5, 23, 59, 59)

    results = list(combined.generate(start, end))

    assert len(results) == 4
    days = {dt.day for dt in results}
    assert days == {1, 2, 4, 5}
    assert 3 not in days


def test_complex_combination():
    """Test complex combination of operators."""
    # Business hours on weekdays
    weekdays = AtomicRule(weekdays="1..5", hours="9..17", minutes="0", seconds="0")
    # Lunch break
    lunch = AtomicRule(weekdays="1..5", hours="12..13", minutes="0", seconds="0")

    # Business hours except lunch
    working_hours = weekdays - lunch

    start = datetime(2025, 11, 10, 0, 0, 0)  # Monday
    end = datetime(2025, 11, 10, 23, 59, 59)

    results = list(working_hours.generate(start, end))

    hours = {dt.hour for dt in results}
    # Should have hours 9-11 and 14-17 (12-13 excluded)
    assert 12 not in hours
    assert 13 not in hours
    assert 9 in hours
    assert 17 in hours


# ---- JSON Serialization Tests ----


def test_atomic_rule_json_serialization():
    """Test AtomicRule to_json and from_json."""
    rule = AtomicRule(
        months="1,4,7,10",
        days="-1",
        weekdays="1..5",
        hours="9..17",
        minutes="/15",
        seconds="0",
    )

    json_str = rule.to_json()
    restored_rule = AtomicRule.from_json(json_str)

    # Test that both rules produce same results
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 12, 31, 23, 59, 59)

    original_results = list(rule.generate(start, end))
    restored_results = list(restored_rule.generate(start, end))

    assert original_results == restored_results


def test_combined_rule_json_serialization():
    """Test CombinedRule to_json and from_json."""
    rule1 = AtomicRule(months="1", days="1", hours="12", minutes="0", seconds="0")
    rule2 = AtomicRule(months="1", days="2", hours="12", minutes="0", seconds="0")

    combined = rule1 + rule2

    json_str = combined.to_json()

    # Import here to avoid circular import in test
    from zerotime import Rule

    restored_rule = Rule.from_json(json_str)

    # Test that both rules produce same results
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 1, 2, 23, 59, 59)

    original_results = list(combined.generate(start, end))
    restored_results = list(restored_rule.generate(start, end))

    assert original_results == restored_results


def test_timezone_serialization():
    """Test timezone serialization."""
    tz = UTC
    rule = AtomicRule(
        months="1",
        days="1",
        hours="12",
        minutes="0",
        seconds="0",
        timezone=tz,
    )

    json_str = rule.to_json()
    restored_rule = AtomicRule.from_json(json_str)

    assert restored_rule._timezone == tz


def test_custom_timezone_serialization():
    """Test serialization with custom timezone offsets."""
    # Test positive offset
    tz_plus = timezone(timedelta(hours=5, minutes=30))  # UTC+05:30 (India)
    rule_plus = AtomicRule(
        months="1",
        days="1",
        hours="12",
        minutes="0",
        seconds="0",
        timezone=tz_plus,
    )

    json_str = rule_plus.to_json()
    restored_plus = AtomicRule.from_json(json_str)
    assert restored_plus._timezone == tz_plus

    # Test negative offset
    tz_minus = timezone(timedelta(hours=-8))  # UTC-08:00 (PST)
    rule_minus = AtomicRule(
        months="1",
        days="1",
        hours="12",
        minutes="0",
        seconds="0",
        timezone=tz_minus,
    )

    json_str = rule_minus.to_json()
    restored_minus = AtomicRule.from_json(json_str)
    assert restored_minus._timezone == tz_minus

    # Test that both rules produce same results in their timezones
    start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz_plus)
    end = datetime(2025, 1, 1, 12, 0, 0, tzinfo=tz_plus)

    original_results = list(rule_plus.generate(start, end))
    restored_results = list(restored_plus.generate(start, end))

    assert original_results == restored_results


# ---- Error Handling Tests ----


def test_invalid_expression():
    """Test invalid DSL expression raises error."""
    with pytest.raises(InvalidRuleError):
        AtomicRule(months="invalid")


def test_invalid_range():
    """Test invalid range raises error."""
    with pytest.raises(InvalidRuleError):
        AtomicRule(months="12..1")  # Start > end


def test_empty_expression():
    """Test empty expression raises error."""
    with pytest.raises(InvalidRuleError):
        AtomicRule(months="")


def test_exclusion_all():
    """Test excluding all values raises error."""
    with pytest.raises(InvalidRuleError):
        AtomicRule(months="!1,!2,!3,!4,!5,!6,!7,!8,!9,!10,!11,!12")


# ---- Edge Cases ----


def test_february_leap_year():
    """Test February handling in leap year."""
    rule = AtomicRule(
        months="2",
        days="29",
        hours="12",
        minutes="0",
        seconds="0",
    )

    # Leap year
    start = datetime(2024, 2, 1, 0, 0, 0)
    end = datetime(2024, 2, 29, 23, 59, 59)
    results = list(rule.generate(start, end))
    assert len(results) == 1

    # Non-leap year
    start = datetime(2025, 2, 1, 0, 0, 0)
    end = datetime(2025, 2, 28, 23, 59, 59)
    results = list(rule.generate(start, end))
    assert len(results) == 0


def test_start_greater_than_end():
    """Test that generate raises error if start > end."""
    rule = AtomicRule()

    start = datetime(2025, 12, 31)
    end = datetime(2025, 1, 1)

    with pytest.raises(ValueError, match="Start .* must be <= end"):
        list(rule.generate(start, end))


# ---- Tests for Critical Fixes ----


def test_timezone_naive_datetime_raises_error():
    """Test that using naive datetime with timezone rule raises error."""
    rule = AtomicRule(hours="12", minutes="0", seconds="0", timezone=UTC)

    naive_dt = datetime(2025, 1, 1, 10, 0, 0)  # Naive datetime

    with pytest.raises(ValueError, match="naive datetime"):
        rule.get_next(naive_dt)

    with pytest.raises(ValueError, match="naive datetime"):
        rule.get_prev(naive_dt)

    with pytest.raises(ValueError, match="naive datetime"):
        list(rule.generate(naive_dt, datetime(2025, 1, 2)))


def test_atomic_rule_equality():
    """Test that identical atomic rules are equal."""
    rule1 = AtomicRule(months="1", days="15", hours="12", minutes="0", seconds="0")
    rule2 = AtomicRule(months="1", days="15", hours="12", minutes="0", seconds="0")
    rule3 = AtomicRule(months="2", days="15", hours="12", minutes="0", seconds="0")

    assert rule1 == rule2
    assert rule1 != rule3
    assert hash(rule1) == hash(rule2)
    assert hash(rule1) != hash(rule3)


def test_combined_rule_equality():
    """Test that identical combined rules are equal."""
    rule1 = AtomicRule(months="1", hours="12", minutes="0", seconds="0")
    rule2 = AtomicRule(months="2", hours="12", minutes="0", seconds="0")

    combined1 = rule1 + rule2
    combined2 = rule1 + rule2
    combined3 = rule1 & rule2

    assert combined1 == combined2
    assert combined1 != combined3
    assert hash(combined1) == hash(combined2)


def test_negative_day_validation():
    """Test that invalid negative days are rejected."""
    # -32 is always invalid (no month has 32 days)
    with pytest.raises(InvalidRuleError, match="-32.*invalid"):
        AtomicRule(days="-32")

    # -100 is definitely invalid
    with pytest.raises(InvalidRuleError, match="-100.*invalid"):
        AtomicRule(days="-100")


def test_improved_error_messages():
    """Test that error messages are more descriptive."""
    # All values excluded (this should raise InvalidRuleError wrapping the descriptive message)
    with pytest.raises(InvalidRuleError, match="excludes all"):
        AtomicRule(months="1..3,!1,!2,!3")

    # Note: "!7" alone is actually valid - it means "all except 7" (which is 1-6,8-12)


def test_json_size_limit():
    """Test that oversized JSON is rejected."""
    # Create a huge JSON string
    huge_json = '{"type": "atomic", ' + '"months": "1", ' * 1000000 + '"days": "1"}'

    with pytest.raises(ValueError, match="JSON too large"):
        AtomicRule.from_json(huge_json)


def test_json_invalid_format():
    """Test that invalid JSON is rejected."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        AtomicRule.from_json("not valid json")

    with pytest.raises(ValueError, match="must be an object"):
        AtomicRule.from_json('["not", "an", "object"]')


def test_json_missing_fields():
    """Test that JSON with missing fields is rejected."""
    incomplete_json = '{"type": "atomic", "months": "1"}'

    with pytest.raises(ValueError, match="Missing required field"):
        AtomicRule.from_json(incomplete_json)


def test_json_wrong_types():
    """Test that JSON with wrong field types is rejected."""
    bad_json = '{"type": "atomic", "months": 123, "days": "1", "weekdays": "1", "hours": "1", "minutes": "1", "seconds": "1"}'

    with pytest.raises(ValueError, match="must be a string"):
        AtomicRule.from_json(bad_json)


def test_json_recursion_depth_limit():
    """Test that deeply nested JSON is handled correctly."""
    # Create modestly nested combined rule JSON (5 levels)
    json_str = '{"type": "atomic", "months": "1", "days": "1", "weekdays": "1", "hours": "1", "minutes": "1", "seconds": "1", "timezone": null}'

    # Wrap it in 5 layers (depth tracking mechanism is tested)
    for _ in range(5):
        json_str = (
            f'{{"type": "combined", "operator": "union", "left": {json_str}, "right": {json_str}}}'
        )

    # This should work (depth 5 < MAX_DEPTH 100)
    from zerotime import Rule

    rule = Rule.from_json(json_str)
    assert rule is not None


def test_slots_immutability():
    """Test that __slots__ prevents adding new attributes."""
    rule = AtomicRule(months="1")

    # Should not be able to add new attributes
    with pytest.raises(AttributeError):
        rule.new_attribute = "value"


def test_weekday_calculation_optimization():
    """Test that weekday calculation is correct (via algorithm)."""
    # Test a few known dates
    rule = AtomicRule(weekdays="1", hours="12", minutes="0", seconds="0")  # Monday

    # January 1, 2025 is a Wednesday (weekday 2)
    # January 6, 2025 is a Monday (weekday 0)
    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 1, 10, 23, 59, 59)

    results = list(rule.generate(start, end))

    # Should match Mondays: Jan 6
    assert len(results) == 1
    assert results[0].day == 6
    assert results[0].weekday() == 0  # Monday


def test_global_step_always_from_zero():
    """Test that global step /N always includes multiples from 0."""
    rule = AtomicRule(
        months="1",
        days="1",
        hours="12",
        minutes="/15",  # Should be 0, 15, 30, 45
        seconds="0",
    )

    start = datetime(2025, 1, 1, 12, 0, 0)
    end = datetime(2025, 1, 1, 12, 59, 59)

    results = list(rule.generate(start, end))

    minutes = {dt.minute for dt in results}
    assert minutes == {0, 15, 30, 45}


def test_combined_rule_memory_efficiency():
    """Test that intersection doesn't load everything in memory at once."""
    # This is more of a smoke test - hard to test memory directly
    # But we can verify it works with large ranges
    rule1 = AtomicRule(minutes="/1", seconds="0")  # Every minute
    rule2 = AtomicRule(minutes="0,15,30,45", seconds="0")  # Every 15 minutes

    combined = rule1 & rule2

    start = datetime(2025, 1, 1, 0, 0, 0)
    end = datetime(2025, 1, 1, 23, 59, 59)

    results = list(combined.generate(start, end))

    # Should only match every 15 minutes (intersection)
    assert len(results) == 24 * 4  # 24 hours * 4 times per hour
    minutes = {dt.minute for dt in results}
    assert minutes == {0, 15, 30, 45}


def test_parsing_cache_performance():
    """Test that parsing is cached for rules without negative days."""
    rule = AtomicRule(months="1..12", days="1", hours="9", minutes="0", seconds="0")

    # Generate across many months - parsing should be cached
    start = datetime(2025, 1, 1)
    end = datetime(2025, 12, 31)

    results = list(rule.generate(start, end))

    # Should have 12 results (first of each month)
    assert len(results) == 12

    # Verify cache was used (rule should have _parsed_cache set)
    assert rule._parsed_cache is not None
