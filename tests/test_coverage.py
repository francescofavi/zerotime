"""Targeted tests filling coverage gaps in src/zerotime/core.py.

Each test pins a specific line or branch that the broader test suite does not
exercise. Tests are grouped by code section so failures point at a single area.
"""

from __future__ import annotations

import contextvars
import json
import threading
from datetime import UTC, datetime, timezone

import pytest

from zerotime import (
    AtomicRule,
    CombinedRule,
    InvalidExpressionError,
    InvalidRuleError,
    NoMatchFoundError,
    RecurrentError,
    Rule,
    RuleConfig,
    get_config,
    reset_config,
    set_global_config,
)
from zerotime import core as _core

# ---------------------------------------------------------------------------
# Public exception hierarchy
# ---------------------------------------------------------------------------


def test_recurrent_error_is_exception_base():
    assert issubclass(RecurrentError, Exception)


def test_invalid_expression_error_inherits_from_recurrent_error():
    assert issubclass(InvalidExpressionError, RecurrentError)


def test_invalid_rule_error_inherits_from_recurrent_error():
    assert issubclass(InvalidRuleError, RecurrentError)


def test_no_match_found_error_inherits_from_recurrent_error():
    assert issubclass(NoMatchFoundError, RecurrentError)


# ---------------------------------------------------------------------------
# Low-level utility helpers
# ---------------------------------------------------------------------------


def test_validate_datetime_bounds_rejects_year_below_min():
    class _FakeDt:
        year = 0

    with pytest.raises(ValueError, match="outside supported range"):
        _core._validate_datetime_bounds(_FakeDt())  # type: ignore[arg-type]


def test_validate_datetime_bounds_rejects_year_above_max():
    class _FakeDt:
        year = 10_000

    with pytest.raises(ValueError, match="outside supported range"):
        _core._validate_datetime_bounds(_FakeDt())  # type: ignore[arg-type]


def test_get_weekday_falls_back_for_year_one_january():
    # Zeller's adjusted formula would underflow to year 0 for Jan/Feb of year 1.
    # The fallback uses datetime.weekday(); the function must agree on a known date.
    expected = datetime(1, 1, 1).weekday()
    assert _core._get_weekday(year=1, month=1, day=1) == expected


def test_get_weekday_falls_back_for_year_one_february():
    expected = datetime(1, 2, 28).weekday()
    assert _core._get_weekday(year=1, month=2, day=28) == expected


def test_calculate_search_boundary_handles_feb_29_target():
    # Base is Feb 29 of a leap year; target year is non-leap so .replace() raises.
    base = datetime(2024, 2, 29, 12, 0, 0)
    out = _core._calculate_search_boundary(base, target_year=2025)
    assert out == datetime(2025, 3, 1, 0, 0, 0)


# ---------------------------------------------------------------------------
# Configuration: ContextVar fallback
# ---------------------------------------------------------------------------


def test_get_config_returns_default_when_unset():
    # In a fresh context the ContextVar has no value -> fallback to RuleConfig().
    ctx = contextvars.Context()
    config = ctx.run(get_config)
    assert isinstance(config, RuleConfig)
    assert config.max_years_search == RuleConfig().max_years_search


# ---------------------------------------------------------------------------
# DSL parser: error and edge paths
# ---------------------------------------------------------------------------


def test_parse_skips_empty_part_in_comma_list():
    # "1,,2" must be accepted; the empty piece is silently skipped.
    rule = AtomicRule(months="1,,2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    out = list(rule.generate(datetime(2025, 1, 1), datetime(2025, 12, 31)))
    months_seen = {dt.month for dt in out}
    assert months_seen == {1, 2}


def test_parse_value_out_of_range_raises():
    with pytest.raises(InvalidRuleError, match="outside valid range"):
        AtomicRule(months="13")


def test_parse_range_start_greater_than_end_raises():
    with pytest.raises(InvalidRuleError, match="start > end"):
        AtomicRule(months="5..3")


def test_parse_range_extra_dots_propagates_value_error():
    # "1..2..3" splits to three pieces; unpacking to (start, end) raises a
    # ValueError that does NOT contain "invalid literal", so the bare re-raise
    # at the end of _parse_range fires.
    with pytest.raises(ValueError):
        AtomicRule(months="1..2..3")


def test_parse_range_out_of_bounds_raises():
    # "0..15" parses fine but 0 < min_month=1 and 15 > max_month=12.
    with pytest.raises(InvalidRuleError, match="outside valid bounds"):
        AtomicRule(months="0..15")


def test_parse_negative_day_without_context_returns_offset():
    # When DSLParser.parse is called with allow_negative=True but year/month
    # are unspecified, the negative offset is returned verbatim instead of
    # being resolved to a positive day.
    out = _core.DSLParser.parse(
        expression="-1",
        field_name="days",
        min_val=1,
        max_val=31,
        allow_negative=True,
    )
    assert out == {-1}


def test_parse_range_with_step_start_greater_than_end_raises():
    with pytest.raises(InvalidRuleError, match="start > end"):
        AtomicRule(minutes="30..10/5")


def test_parse_range_with_step_out_of_bounds_raises():
    with pytest.raises(InvalidRuleError, match="outside valid bounds"):
        AtomicRule(minutes="0..70/5")


def test_parse_range_with_step_extra_dots_propagates_value_error():
    # "1..2..3/5" -> range_part = "1..2..3" -> split("..") gives 3 pieces;
    # the resulting ValueError doesn't match the known substrings -> bare raise.
    with pytest.raises(ValueError):
        AtomicRule(minutes="1..2..3/5")


def test_parse_excludes_only_subset_yields_empty_set():
    # "1..3,!1..5" -> included = {1,2,3}, excluded = {1..5}; result empty
    # but excluded != included, taking the final else-branch error.
    with pytest.raises(InvalidRuleError, match="empty set"):
        AtomicRule(months="1..3,!1..5")


def test_parse_negative_day_zero_raises():
    # "-0" is parsed but offset >= 0, triggering the "should be negative" branch.
    with pytest.raises(InvalidRuleError, match="should be negative"):
        AtomicRule(days="-0")


def test_parse_negative_day_non_numeric_raises():
    with pytest.raises(InvalidRuleError, match="Invalid negative day"):
        AtomicRule(days="-abc")


def test_parse_negative_day_too_large_at_runtime():
    # Construction validates against January (31 days). At generate-time, -30
    # in February (28 days) resolves to actual_day = -1, which is invalid.
    rule = AtomicRule(months="2", days="-30")
    with pytest.raises(InvalidExpressionError, match="too large"):
        list(rule.generate(datetime(2025, 1, 1), datetime(2025, 12, 31)))


# ---------------------------------------------------------------------------
# Rule.from_json (top-level dispatcher)
# ---------------------------------------------------------------------------


def test_rule_from_json_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid JSON"):
        Rule.from_json("{not valid json")


def test_rule_from_json_non_object_raises():
    with pytest.raises(ValueError, match="object/dict"):
        Rule.from_json("[]")


def test_rule_from_json_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown rule type"):
        Rule.from_json('{"type": "weird"}')


def test_rule_from_json_dispatches_to_atomic():
    rule = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    out = Rule.from_json(rule.to_json())
    assert isinstance(out, AtomicRule)
    assert out == rule


def test_rule_from_json_dispatches_to_combined():
    a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    b = AtomicRule(months="2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    combined = a + b
    out = Rule.from_json(combined.to_json())
    assert isinstance(out, CombinedRule)


# ---------------------------------------------------------------------------
# AtomicRule: get_prev default max_years, generate_reverse paths
# ---------------------------------------------------------------------------


class TestAtomicReversePaths:
    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_get_prev_uses_config_default_when_max_years_none(self):
        rule = AtomicRule(
            months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        # No max_years argument -> falls back to RuleConfig().max_years_search.
        result = rule.get_prev(datetime(2025, 6, 15))
        assert result == datetime(2025, 1, 1, 0, 0, 0)

    def test_get_prev_with_explicit_max_years(self):
        rule = AtomicRule(
            months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        result = rule.get_prev(datetime(2025, 6, 15), max_years=10)
        assert result == datetime(2025, 1, 1, 0, 0, 0)

    def test_generate_reverse_with_explicit_max_items(self):
        rule = AtomicRule(
            months="1", days="1..3", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        # Explicit max_items so the "is None" fallback branch is bypassed.
        out = list(rule.generate_reverse(datetime(2025, 1, 1), datetime(2025, 1, 31), max_items=5))
        assert len(out) == 3

    def test_generate_reverse_rejects_start_after_end(self):
        rule = AtomicRule(
            months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        gen = rule.generate_reverse(datetime(2025, 12, 31), datetime(2025, 1, 1))
        with pytest.raises(ValueError, match="must be <="):
            next(gen)

    def test_generate_reverse_uses_config_default_max_items(self):
        rule = AtomicRule(
            months="1", days="1..3", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        results = list(rule.generate_reverse(datetime(2025, 1, 1), datetime(2025, 1, 31)))
        assert len(results) == 3
        # Reverse order
        assert results[0] > results[-1]

    def test_generate_reverse_skips_non_matching_weekday(self):
        # weekdays="1" (Monday). Range 2025-01-01 (Wed) ... 2025-01-07 (Tue).
        # Only Monday Jan 6 matches.
        rule = AtomicRule(
            months="1", days="1..31", weekdays="1", hours="0", minutes="0", seconds="0"
        )
        out = list(rule.generate_reverse(datetime(2025, 1, 1), datetime(2025, 1, 7)))
        assert out == [datetime(2025, 1, 6)]

    def test_generate_reverse_raises_when_max_items_exceeded(self):
        set_global_config(RuleConfig(max_generate_items=2))
        rule = AtomicRule(
            months="1", days="1..5", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        gen = rule.generate_reverse(datetime(2025, 1, 1), datetime(2025, 1, 31))
        next(gen)
        next(gen)
        with pytest.raises(ValueError, match="generation limit"):
            next(gen)


# ---------------------------------------------------------------------------
# AtomicRule.from_json: timezone parsing edge cases
# ---------------------------------------------------------------------------


def _make_atomic_payload(timezone_str: str | None) -> str:
    payload = {
        "type": "atomic",
        "months": "1",
        "days": "1",
        "weekdays": "1..7",
        "hours": "0",
        "minutes": "0",
        "seconds": "0",
        "timezone": timezone_str,
    }
    return json.dumps(payload)


def test_atomic_from_json_rejects_offset_without_sign():
    payload = _make_atomic_payload("UTC1:00")
    with pytest.raises(ValueError, match="no sign character|Invalid timezone"):
        AtomicRule.from_json(payload)


def test_atomic_from_json_accepts_negative_offset():
    payload = _make_atomic_payload("UTC-05:30")
    rule = AtomicRule.from_json(payload)
    assert rule._timezone is not None
    assert rule._timezone.utcoffset(None) is not None


# ---------------------------------------------------------------------------
# CombinedRule timezone validation
# ---------------------------------------------------------------------------


def test_combined_rule_rejects_mixed_aware_and_naive():
    aware = AtomicRule(
        months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=UTC
    )
    naive = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    with pytest.raises(InvalidRuleError, match="timezone-aware and timezone-naive"):
        _ = aware + naive


def test_combined_get_rule_timezone_unwraps_nested_unknown_left():
    # Build a nested CombinedRule whose left child has unknown tz at the
    # outer level (because it is itself a CombinedRule with mixed children
    # both resolving to None — i.e. the inner left/right both share tz=None).
    a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    b = AtomicRule(months="2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    nested = a + b  # _get_rule_timezone(nested) returns None (both naive)
    outer = nested + a
    assert outer._operator == "union"


def test_combined_get_rule_timezone_handles_mixed_nested():
    # Two nested CombinedRules with same overall tz — left/right None each side.
    a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    b = AtomicRule(months="2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    c = AtomicRule(months="3", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    d = AtomicRule(months="4", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
    left_nested = a + b
    right_nested = c + d
    # Both nested resolve to None; combine should succeed.
    outer = left_nested + right_nested
    assert isinstance(outer, CombinedRule)


def test_get_rule_timezone_returns_unknown_for_non_rule():
    # Direct call with an unrelated object exercises the final fallback branch.
    class _NotARule:
        pass

    assert CombinedRule._get_rule_timezone(_NotARule()) == "unknown"  # type: ignore[arg-type]


def test_get_rule_timezone_resolves_when_left_unknown():
    # left child is a CombinedRule with mixed-aware tzs -> "unknown";
    # right child has a known tz; resolver returns the known right tz.
    from datetime import timedelta

    east = timezone(timedelta(hours=5))
    mixed = AtomicRule(
        months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=UTC
    ) + AtomicRule(
        months="2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=east
    )
    clean_utc = AtomicRule(
        months="3", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=UTC
    )
    outer = mixed + clean_utc
    assert CombinedRule._get_rule_timezone(outer) == UTC


def test_get_rule_timezone_resolves_when_right_unknown():
    from datetime import timedelta

    east = timezone(timedelta(hours=5))
    mixed = AtomicRule(
        months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=UTC
    ) + AtomicRule(
        months="2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=east
    )
    clean_utc = AtomicRule(
        months="3", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=UTC
    )
    outer = clean_utc + mixed
    assert CombinedRule._get_rule_timezone(outer) == UTC


def test_get_rule_timezone_returns_unknown_when_children_disagree():
    from datetime import timedelta

    east = timezone(timedelta(hours=5))
    # Both children resolve to a definite tz, but they differ -> "unknown".
    left_utc = AtomicRule(
        months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=UTC
    ) + AtomicRule(
        months="2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=UTC
    )
    right_east = AtomicRule(
        months="3", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=east
    ) + AtomicRule(
        months="4", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0", timezone=east
    )
    outer = left_utc + right_east
    assert CombinedRule._get_rule_timezone(outer) == "unknown"


# ---------------------------------------------------------------------------
# CombinedRule.generate (forward) — boundary branches
# ---------------------------------------------------------------------------


class TestCombinedForwardEdges:
    def test_generate_rejects_start_after_end(self):
        a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        b = AtomicRule(months="2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        gen = (a + b).generate(datetime(2025, 12, 31), datetime(2025, 1, 1))
        with pytest.raises(ValueError, match="must be <="):
            next(gen)

    def test_union_yields_right_when_only_right_has_matches(self):
        # Left rule has zero matches in range; right has one. Forces the
        # "left exhausted, drain right" branch.
        left = AtomicRule(
            months="6", days="15", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )  # only Jun 15
        right = AtomicRule(
            months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )  # only Jan 1
        combined = left + right
        out = list(combined.generate(datetime(2025, 1, 1), datetime(2025, 3, 31)))
        assert out == [datetime(2025, 1, 1)]

    def test_union_dedupes_identical_values_from_both_sides(self):
        # Both rules match the same instant; union must yield it once.
        a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        b = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        out = list((a + b).generate(datetime(2025, 1, 1), datetime(2025, 1, 1)))
        assert out == [datetime(2025, 1, 1)]

    def test_union_interleaves_when_right_precedes_left(self):
        # Right's first match comes before left's first match; covers the
        # "right_val < left_val" branch.
        left = AtomicRule(
            months="3", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        right = AtomicRule(
            months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        out = list((left + right).generate(datetime(2025, 1, 1), datetime(2025, 12, 31)))
        assert out == [datetime(2025, 1, 1), datetime(2025, 3, 1)]


# ---------------------------------------------------------------------------
# CombinedRule.generate_reverse — full coverage of all three operators
# ---------------------------------------------------------------------------


class TestCombinedReverse:
    def test_reverse_rejects_start_after_end(self):
        a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        b = AtomicRule(months="2", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        gen = (a + b).generate_reverse(datetime(2025, 12, 31), datetime(2025, 1, 1))
        with pytest.raises(ValueError, match="must be <="):
            next(gen)

    def test_reverse_union_yields_in_descending_order(self):
        a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        b = AtomicRule(months="3", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        out = list((a + b).generate_reverse(datetime(2025, 1, 1), datetime(2025, 12, 31)))
        assert out == [datetime(2025, 3, 1), datetime(2025, 1, 1)]

    def test_reverse_union_drains_right_when_left_exhausted(self):
        left = AtomicRule(
            months="6", days="15", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        right = AtomicRule(
            months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        out = list((left + right).generate_reverse(datetime(2025, 1, 1), datetime(2025, 3, 31)))
        assert out == [datetime(2025, 1, 1)]

    def test_reverse_union_dedupes_equal_values(self):
        a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        b = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        out = list((a + b).generate_reverse(datetime(2025, 1, 1), datetime(2025, 1, 1)))
        assert out == [datetime(2025, 1, 1)]

    def test_reverse_union_when_left_smaller_than_right(self):
        # left's first reverse-match (Jan) < right's first (Mar); covers
        # the "right_val > left_val" branch in generate_reverse.
        left = AtomicRule(
            months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        right = AtomicRule(
            months="3", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        out = list((left + right).generate_reverse(datetime(2025, 1, 1), datetime(2025, 12, 31)))
        assert out == [datetime(2025, 3, 1), datetime(2025, 1, 1)]

    def test_reverse_intersection(self):
        # Mondays in January 2025: 6, 13, 20, 27. In reverse: 27, 20, 13, 6.
        days = AtomicRule(
            months="1", days="1..31", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        mondays = AtomicRule(
            months="1..12", days="1..31", weekdays="1", hours="0", minutes="0", seconds="0"
        )
        out = list((days & mondays).generate_reverse(datetime(2025, 1, 1), datetime(2025, 1, 31)))
        assert out == [
            datetime(2025, 1, 27),
            datetime(2025, 1, 20),
            datetime(2025, 1, 13),
            datetime(2025, 1, 6),
        ]

    def test_reverse_difference(self):
        # First 3 days of Jan 2025 minus Jan 2.
        all_days = AtomicRule(
            months="1", days="1..3", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        skip_two = AtomicRule(
            months="1", days="2", weekdays="1..7", hours="0", minutes="0", seconds="0"
        )
        out = list(
            (all_days - skip_two).generate_reverse(datetime(2025, 1, 1), datetime(2025, 1, 31))
        )
        assert out == [datetime(2025, 1, 3), datetime(2025, 1, 1)]


# ---------------------------------------------------------------------------
# CombinedRule.from_json: validation and limits
# ---------------------------------------------------------------------------


class TestCombinedFromJson:
    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            CombinedRule.from_json("not json {")

    def test_non_object_raises(self):
        with pytest.raises(ValueError, match="object/dict"):
            CombinedRule.from_json("[]")

    def test_size_limit_enforced(self):
        set_global_config(RuleConfig(max_json_size=200))
        # Build a valid combined-rule envelope just over the size limit.
        a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        big_payload = (a + a).to_json() + " " * 500
        with pytest.raises(ValueError, match="JSON too large"):
            CombinedRule.from_json(big_payload)

    def test_recursion_depth_enforced(self):
        set_global_config(RuleConfig(max_recursion_depth=1))
        a = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")
        # Tree path root -> left -> left -> left walks _depth 0,1,2;
        # at _depth=2 the check (2 > 1) triggers.
        deep = ((a + a) + a) + a
        with pytest.raises(ValueError, match="nesting too deep"):
            CombinedRule.from_json(deep.to_json())


# ---------------------------------------------------------------------------
# Cache: double-checked locking second hit
# ---------------------------------------------------------------------------


def test_parse_fields_double_checked_lock_second_hit():
    """Force the path where a second thread takes the lock and finds the cache
    already populated. We do this by acquiring the cache lock first, kicking
    off a worker thread that will block on it, then populating the cache and
    releasing — the worker then enters the locked region and hits the
    inner cache check."""
    rule = AtomicRule(months="1", days="1", weekdays="1..7", hours="0", minutes="0", seconds="0")

    captured: list[object] = []

    def worker():
        captured.append(rule._parse_fields(year=2025, month=1))

    rule._cache_lock.acquire()
    try:
        t = threading.Thread(target=worker)
        t.start()
        # Give the worker time to reach the lock.
        threading.Event().wait(0.05)
        # Populate the cache before releasing.
        rule._parsed_cache = rule._parse_fields_impl(year=2025, month=1)
    finally:
        rule._cache_lock.release()

    t.join(timeout=2.0)
    assert not t.is_alive()
    assert len(captured) == 1
    assert captured[0] is rule._parsed_cache
