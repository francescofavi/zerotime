"""Tests for edge cases and error paths to improve coverage."""

from datetime import UTC, datetime

import pytest

from zerotime import AtomicRule, CombinedRule, InvalidExpressionError, Rule


class TestDSLParserEdgeCases:
    """Test edge cases in DSL parser."""

    def test_invalid_range_non_numeric_start(self):
        """Test range with non-numeric start value."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(non-numeric values|Invalid)"
        ):
            _rule = AtomicRule(months="abc..12")

    def test_invalid_range_non_numeric_end(self):
        """Test range with non-numeric end value."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(non-numeric values|Invalid)"
        ):
            _rule = AtomicRule(months="1..xyz")

    def test_invalid_range_with_step_non_numeric(self):
        """Test range with step containing non-numeric values."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(Invalid range with step|Invalid)"
        ):
            _rule = AtomicRule(minutes="0..59/abc")

    def test_invalid_range_with_step_malformed(self):
        """Test malformed range with step."""
        with pytest.raises((InvalidExpressionError, Exception)):
            _rule = AtomicRule(minutes="0/10/20")  # Too many slashes

    def test_negative_step_in_range(self):
        """Test negative step value."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(Step .* must be positive|Invalid)"
        ):
            _rule = AtomicRule(minutes="0..59/-5")

    def test_zero_step_in_range(self):
        """Test zero step value."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(Step .* must be positive|Invalid)"
        ):
            _rule = AtomicRule(minutes="0..59/0")

    def test_negative_step_in_global(self):
        """Test negative step in global step."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(Step .* must be positive|Invalid)"
        ):
            _rule = AtomicRule(minutes="/-5")

    def test_zero_step_in_global(self):
        """Test zero step in global step."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(Step .* must be positive|Invalid)"
        ):
            _rule = AtomicRule(minutes="/0")

    def test_invalid_global_step_non_numeric(self):
        """Test global step with non-numeric value."""
        with pytest.raises((InvalidExpressionError, Exception), match="(Invalid step|Invalid)"):
            _rule = AtomicRule(minutes="/abc")

    def test_negative_day_too_large(self):
        """Test negative day offset exceeding -31."""
        with pytest.raises(
            (InvalidExpressionError, Exception),
            match="(no month has more than|Valid range is|Invalid)",
        ):
            _rule = AtomicRule(days="-32")

    def test_negative_day_too_large_offset_50(self):
        """Test negative day offset of -50."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(Valid range is -1 to -31|Invalid)"
        ):
            _rule = AtomicRule(days="-50")

    def test_negative_day_invalid_for_month(self):
        """Test negative day that's too large for specific month."""
        rule = AtomicRule(months="2", days="-30", timezone=UTC)  # Feb only has 28-29 days
        start = datetime(2025, 2, 1, tzinfo=UTC)
        end = datetime(2025, 2, 28, tzinfo=UTC)

        # Should raise error since -30 is too large for February
        with pytest.raises(InvalidExpressionError, match="too large for February"):
            list(rule.generate(start, end))

    def test_invalid_integer_value(self):
        """Test completely invalid integer value."""
        with pytest.raises(
            (InvalidExpressionError, Exception), match="(Invalid integer value|Invalid)"
        ):
            _rule = AtomicRule(hours="not_a_number")


class TestAtomicRuleWithMethods:
    """Test AtomicRule with_* methods for full coverage."""

    def test_with_weekdays(self):
        """Test with_weekdays method."""
        rule = AtomicRule(months="1", days="1", hours="0", minutes="0", timezone=UTC)
        new_rule = rule.with_weekdays("1,2,3")  # Mon-Wed

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)  # Wednesday
        end = datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC)

        results = list(new_rule.generate(start, end))
        # Should only match Wednesdays at midnight
        assert all(dt.weekday() in [0, 1, 2] for dt in results)

    def test_with_hours(self):
        """Test with_hours method."""
        rule = AtomicRule(months="1", days="1", minutes="0", seconds="0", timezone=UTC)
        new_rule = rule.with_hours("9,10,11")

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 23, 59, 59, tzinfo=UTC)

        results = list(new_rule.generate(start, end))
        assert len(results) == 3  # 9:00, 10:00, 11:00
        assert all(dt.hour in [9, 10, 11] for dt in results)

    def test_with_minutes(self):
        """Test with_minutes method."""
        rule = AtomicRule(months="1", days="1", hours="0", seconds="0", timezone=UTC)
        new_rule = rule.with_minutes("0,15,30,45")

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 0, 59, 59, tzinfo=UTC)

        results = list(new_rule.generate(start, end))
        assert len(results) == 4
        assert all(dt.minute in [0, 15, 30, 45] for dt in results)

    def test_with_seconds(self):
        """Test with_seconds method."""
        rule = AtomicRule(months="1", days="1", hours="0", minutes="0", timezone=UTC)
        new_rule = rule.with_seconds("0,30")

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 0, 0, 59, tzinfo=UTC)

        results = list(new_rule.generate(start, end))
        assert len(results) == 2
        assert all(dt.second in [0, 30] for dt in results)


class TestJSONEdgeCases:
    """Test JSON serialization edge cases."""

    def test_json_not_dict(self):
        """Test JSON that's not a dict."""
        with pytest.raises(ValueError, match="JSON must be an object/dict"):
            Rule.from_json('["not", "a", "dict"]')

    def test_json_unknown_type(self):
        """Test JSON with unknown rule type."""
        with pytest.raises(ValueError, match="Unknown rule type"):
            Rule.from_json('{"type": "unknown"}')

    def test_atomic_rule_json_wrong_type_value(self):
        """Test AtomicRule from_json with wrong type."""
        with pytest.raises(ValueError, match="Expected atomic rule"):
            AtomicRule.from_json('{"type": "combined"}')

    def test_atomic_rule_json_wrong_field_type(self):
        """Test AtomicRule with wrong field type (not string)."""
        json_str = """{
            "type": "atomic",
            "months": 123,
            "days": "1..31",
            "weekdays": "1..7",
            "hours": "0..23",
            "minutes": "0..59",
            "seconds": "0..59"
        }"""
        with pytest.raises(ValueError, match="must be a string"):
            AtomicRule.from_json(json_str)

    def test_atomic_rule_json_timezone_wrong_type(self):
        """Test AtomicRule with timezone that's not a string."""
        json_str = """{
            "type": "atomic",
            "months": "1..12",
            "days": "1..31",
            "weekdays": "1..7",
            "hours": "0..23",
            "minutes": "0..59",
            "seconds": "0..59",
            "timezone": 123
        }"""
        with pytest.raises(ValueError, match="Timezone must be a string"):
            AtomicRule.from_json(json_str)

    def test_atomic_rule_json_invalid_timezone_format(self):
        """Test AtomicRule with invalid timezone format."""
        json_str = """{
            "type": "atomic",
            "months": "1..12",
            "days": "1..31",
            "weekdays": "1..7",
            "hours": "0..23",
            "minutes": "0..59",
            "seconds": "0..59",
            "timezone": "INVALID"
        }"""
        with pytest.raises(ValueError, match="Timezone must start with 'UTC'"):
            AtomicRule.from_json(json_str)

    def test_atomic_rule_json_timezone_no_offset(self):
        """Test AtomicRule with UTC but no offset after."""
        json_str = """{
            "type": "atomic",
            "months": "1..12",
            "days": "1..31",
            "weekdays": "1..7",
            "hours": "0..23",
            "minutes": "0..59",
            "seconds": "0..59",
            "timezone": "UTC"
        }"""
        # This should work - UTC without offset
        rule = AtomicRule.from_json(json_str)
        assert rule._timezone == UTC

    def test_atomic_rule_json_timezone_invalid_offset_format(self):
        """Test AtomicRule with invalid offset format."""
        json_str = """{
            "type": "atomic",
            "months": "1..12",
            "days": "1..31",
            "weekdays": "1..7",
            "hours": "0..23",
            "minutes": "0..59",
            "seconds": "0..59",
            "timezone": "UTC+5"
        }"""
        with pytest.raises(ValueError, match="Offset must be in HH:MM format"):
            AtomicRule.from_json(json_str)

    def test_atomic_rule_json_timezone_hours_out_of_range(self):
        """Test AtomicRule with timezone hours out of range."""
        json_str = """{
            "type": "atomic",
            "months": "1..12",
            "days": "1..31",
            "weekdays": "1..7",
            "hours": "0..23",
            "minutes": "0..59",
            "seconds": "0..59",
            "timezone": "UTC+25:00"
        }"""
        with pytest.raises(ValueError, match="Hours must be 0-23"):
            AtomicRule.from_json(json_str)

    def test_atomic_rule_json_timezone_minutes_out_of_range(self):
        """Test AtomicRule with timezone minutes out of range."""
        json_str = """{
            "type": "atomic",
            "months": "1..12",
            "days": "1..31",
            "weekdays": "1..7",
            "hours": "0..23",
            "minutes": "0..59",
            "seconds": "0..59",
            "timezone": "UTC+05:65"
        }"""
        with pytest.raises(ValueError, match="Minutes must be 0-59"):
            AtomicRule.from_json(json_str)

    def test_combined_rule_json_wrong_type(self):
        """Test CombinedRule from_json with wrong type."""
        with pytest.raises(ValueError, match="Expected combined rule"):
            CombinedRule.from_json('{"type": "atomic"}')

    def test_combined_rule_json_missing_operator(self):
        """Test CombinedRule with missing operator."""
        with pytest.raises(ValueError, match="Missing required field: operator"):
            CombinedRule.from_json('{"type": "combined"}')

    def test_combined_rule_json_missing_left_or_right(self):
        """Test CombinedRule with missing left/right."""
        with pytest.raises(ValueError, match="Missing required fields: left and/or right"):
            CombinedRule.from_json('{"type": "combined", "operator": "union"}')

    def test_combined_rule_json_operator_not_string(self):
        """Test CombinedRule with operator that's not a string."""
        json_str = """{
            "type": "combined",
            "operator": 123,
            "left": {"type": "atomic", "months": "1..12", "days": "1..31", "weekdays": "1..7", "hours": "0..23", "minutes": "0..59", "seconds": "0..59"},
            "right": {"type": "atomic", "months": "1..12", "days": "1..31", "weekdays": "1..7", "hours": "0..23", "minutes": "0..59", "seconds": "0..59"}
        }"""
        with pytest.raises(ValueError, match="Operator must be string"):
            CombinedRule.from_json(json_str)

    def test_combined_rule_json_unknown_subrule_type(self):
        """Test CombinedRule with unknown subrule type."""
        json_str = """{
            "type": "combined",
            "operator": "union",
            "left": {"type": "unknown"},
            "right": {"type": "atomic", "months": "1..12", "days": "1..31", "weekdays": "1..7", "hours": "0..23", "minutes": "0..59", "seconds": "0..59"}
        }"""
        with pytest.raises(ValueError, match="Unknown rule type"):
            CombinedRule.from_json(json_str)


class TestCombinedRuleEdgeCases:
    """Test CombinedRule edge cases."""

    def test_invalid_operator(self):
        """Test CombinedRule with invalid operator."""
        r1 = AtomicRule(months="1")
        r2 = AtomicRule(months="2")

        with pytest.raises(ValueError, match="Invalid operator"):
            CombinedRule(r1, r2, "invalid")

    def test_combined_rule_not_equal_to_non_combined(self):
        """Test CombinedRule equality with non-CombinedRule."""
        r1 = AtomicRule(months="1")
        r2 = AtomicRule(months="2")
        combined = r1 + r2

        assert combined != r1
        assert combined != "not a rule"
        assert combined.__eq__("not a rule") == NotImplemented


class TestAtomicRuleEquality:
    """Test AtomicRule equality edge cases."""

    def test_atomic_rule_not_equal_to_non_atomic(self):
        """Test AtomicRule equality with non-AtomicRule."""
        rule = AtomicRule(months="1")

        assert rule != "not a rule"
        assert rule.__eq__("not a rule") == NotImplemented


class TestDSTHandling:
    """Test Daylight Saving Time handling with ZoneInfo."""

    def test_dst_spring_forward_skips_nonexistent_time(self):
        """Test that non-existent times during DST spring forward are skipped.

        In Europe/Rome, on 2024-03-31, clocks jump from 02:00 to 03:00.
        Times between 02:00 and 02:59 do not exist.
        """
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            pytest.skip("zoneinfo not available")

        try:
            tz_rome = ZoneInfo("Europe/Rome")
        except KeyError:
            pytest.skip("timezone data not available")
        # Rule that would match 02:30 every day
        rule = AtomicRule(
            months="3",
            days="31",
            hours="2",
            minutes="30",
            seconds="0",
            timezone=tz_rome,
        )

        start = datetime(2024, 3, 31, 0, 0, 0, tzinfo=tz_rome)
        end = datetime(2024, 3, 31, 23, 59, 59, tzinfo=tz_rome)

        results = list(rule.generate(start, end))
        # 02:30 doesn't exist on this day, so no results
        assert len(results) == 0

    def test_dst_spring_forward_adjacent_times_exist(self):
        """Test that times before and after the DST gap exist."""
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            pytest.skip("zoneinfo not available")

        try:
            tz_rome = ZoneInfo("Europe/Rome")
        except KeyError:
            pytest.skip("timezone data not available")
        # Rule that matches 01:30 and 03:30
        rule = AtomicRule(
            months="3",
            days="31",
            hours="1,3",
            minutes="30",
            seconds="0",
            timezone=tz_rome,
        )

        start = datetime(2024, 3, 31, 0, 0, 0, tzinfo=tz_rome)
        end = datetime(2024, 3, 31, 23, 59, 59, tzinfo=tz_rome)

        results = list(rule.generate(start, end))
        # Both 01:30 and 03:30 exist
        assert len(results) == 2
        assert results[0].hour == 1
        assert results[1].hour == 3

    def test_dst_fall_back_ambiguous_time(self):
        """Test ambiguous times during DST fall back use fold=0.

        In Europe/Rome, on 2024-10-27, clocks go back from 03:00 to 02:00.
        Times between 02:00 and 02:59 exist twice.
        """
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            pytest.skip("zoneinfo not available")

        try:
            tz_rome = ZoneInfo("Europe/Rome")
        except KeyError:
            pytest.skip("timezone data not available")
        # Rule that matches 02:30 on the fall back day
        rule = AtomicRule(
            months="10",
            days="27",
            hours="2",
            minutes="30",
            seconds="0",
            timezone=tz_rome,
        )

        start = datetime(2024, 10, 27, 0, 0, 0, tzinfo=tz_rome)
        end = datetime(2024, 10, 27, 23, 59, 59, tzinfo=tz_rome)

        results = list(rule.generate(start, end))
        # We get one result (fold=0, the first occurrence)
        assert len(results) == 1
        assert results[0].hour == 2
        assert results[0].minute == 30
        # fold=0 means CEST (summer time, UTC+2)
        assert results[0].fold == 0

    def test_zoneinfo_normal_day(self):
        """Test ZoneInfo works correctly on normal days (no DST transition)."""
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            pytest.skip("zoneinfo not available")

        try:
            tz_rome = ZoneInfo("Europe/Rome")
        except KeyError:
            pytest.skip("timezone data not available")
        rule = AtomicRule(
            months="6",
            days="15",
            hours="12",
            minutes="0",
            seconds="0",
            timezone=tz_rome,
        )

        start = datetime(2024, 6, 15, 0, 0, 0, tzinfo=tz_rome)
        end = datetime(2024, 6, 15, 23, 59, 59, tzinfo=tz_rome)

        results = list(rule.generate(start, end))
        assert len(results) == 1
        assert results[0].hour == 12
        assert results[0].minute == 0

    def test_generate_reverse_dst_spring_forward(self):
        """Test generate_reverse also skips non-existent DST times."""
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            pytest.skip("zoneinfo not available")

        try:
            tz_rome = ZoneInfo("Europe/Rome")
        except KeyError:
            pytest.skip("timezone data not available")
        rule = AtomicRule(
            months="3",
            days="31",
            hours="2",
            minutes="30",
            seconds="0",
            timezone=tz_rome,
        )

        start = datetime(2024, 3, 31, 0, 0, 0, tzinfo=tz_rome)
        end = datetime(2024, 3, 31, 23, 59, 59, tzinfo=tz_rome)

        results = list(rule.generate_reverse(start, end))
        # 02:30 doesn't exist, so no results
        assert len(results) == 0
