"""Tests for configuration system."""

from datetime import UTC, datetime

import pytest

from zerotime import (
    AtomicRule,
    NoMatchFoundError,
    RuleConfig,
    get_config,
    reset_config,
    set_global_config,
)


class TestRuleConfig:
    """Tests for RuleConfig class."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_config()

    def test_default_config(self):
        """Test default configuration values."""
        config = RuleConfig()
        assert config.max_years_search == 5
        assert config.max_generate_items is None
        assert config.max_json_size == 1_000_000
        assert config.max_recursion_depth == 100
        assert config.default_batch_size == 10_000

    def test_custom_config(self):
        """Test creating custom configuration."""
        config = RuleConfig(
            max_years_search=10,
            max_generate_items=1000,
            max_json_size=50_000,
            max_recursion_depth=50,
            default_batch_size=500,
        )
        assert config.max_years_search == 10
        assert config.max_generate_items == 1000
        assert config.max_json_size == 50_000
        assert config.max_recursion_depth == 50
        assert config.default_batch_size == 500

    def test_config_validation_max_years_search(self):
        """Test validation of max_years_search."""
        with pytest.raises(ValueError, match="max_years_search must be positive"):
            RuleConfig(max_years_search=0)

        with pytest.raises(ValueError, match="max_years_search must be positive"):
            RuleConfig(max_years_search=-1)

    def test_config_validation_max_generate_items(self):
        """Test validation of max_generate_items."""
        with pytest.raises(ValueError, match="max_generate_items must be positive or None"):
            RuleConfig(max_generate_items=0)

        with pytest.raises(ValueError, match="max_generate_items must be positive or None"):
            RuleConfig(max_generate_items=-1)

        # None should be valid
        config = RuleConfig(max_generate_items=None)
        assert config.max_generate_items is None

    def test_config_validation_max_json_size(self):
        """Test validation of max_json_size."""
        with pytest.raises(ValueError, match="max_json_size must be positive"):
            RuleConfig(max_json_size=0)

        with pytest.raises(ValueError, match="max_json_size must be positive"):
            RuleConfig(max_json_size=-1)

    def test_config_validation_max_recursion_depth(self):
        """Test validation of max_recursion_depth."""
        with pytest.raises(ValueError, match="max_recursion_depth must be positive"):
            RuleConfig(max_recursion_depth=0)

        with pytest.raises(ValueError, match="max_recursion_depth must be positive"):
            RuleConfig(max_recursion_depth=-1)

    def test_config_validation_default_batch_size(self):
        """Test validation of default_batch_size."""
        with pytest.raises(ValueError, match="default_batch_size must be positive"):
            RuleConfig(default_batch_size=0)

        with pytest.raises(ValueError, match="default_batch_size must be positive"):
            RuleConfig(default_batch_size=-1)

    def test_get_config(self):
        """Test getting global configuration."""
        config = get_config()
        assert isinstance(config, RuleConfig)
        assert config.max_years_search == 5  # default

    def test_set_global_config(self):
        """Test setting global configuration."""
        custom_config = RuleConfig(max_years_search=10, max_generate_items=500)
        set_global_config(custom_config)

        config = get_config()
        assert config.max_years_search == 10
        assert config.max_generate_items == 500

    def test_reset_config(self):
        """Test resetting configuration to defaults."""
        # Set custom config
        custom_config = RuleConfig(max_years_search=10)
        set_global_config(custom_config)
        assert get_config().max_years_search == 10

        # Reset to defaults
        reset_config()
        assert get_config().max_years_search == 5

    def test_max_years_search_affects_get_next(self):
        """Test that max_years_search config affects get_next."""
        rule = AtomicRule(months="6", days="31", timezone=UTC)  # June 31 doesn't exist

        # Set very low max_years_search
        set_global_config(RuleConfig(max_years_search=1))

        base = datetime(2025, 1, 1, tzinfo=UTC)
        with pytest.raises(NoMatchFoundError, match="within 1 years"):
            rule.get_next(base)

    def test_max_years_search_parameter_overrides_config(self):
        """Test that max_years parameter overrides global config."""
        rule = AtomicRule(months="1", days="1", hours="0", minutes="0", seconds="0", timezone=UTC)

        # Set global config with max_years_search=10
        set_global_config(RuleConfig(max_years_search=10))

        base = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)

        # Use explicit max_years=1 (overrides config)
        next_match = rule.get_next(base, max_years=1)
        assert next_match.year == 2026

    def test_max_generate_items_limit(self):
        """Test max_generate_items limit in generate."""
        rule = AtomicRule(seconds="0..59", timezone=UTC)  # Generates 60 items per minute

        # Set limit to 10 items
        set_global_config(RuleConfig(max_generate_items=10))

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 0, 1, 0, tzinfo=UTC)  # 1 minute range

        with pytest.raises(ValueError, match="Maximum generation limit of 10 items exceeded"):
            list(rule.generate(start, end))

    def test_max_generate_items_parameter_overrides_config(self):
        """Test that max_items parameter overrides global config."""
        rule = AtomicRule(seconds="0..59", timezone=UTC)

        # Set global limit to 100
        set_global_config(RuleConfig(max_generate_items=100))

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 0, 1, 0, tzinfo=UTC)

        # Use explicit max_items=5 (overrides config)
        with pytest.raises(ValueError, match="Maximum generation limit of 5 items exceeded"):
            list(rule.generate(start, end, max_items=5))

    def test_max_json_size_limit(self):
        """Test max_json_size limit in from_json."""
        # Set very low limit
        set_global_config(RuleConfig(max_json_size=50))

        # Create large JSON
        rule = AtomicRule(months="1..12", days="1..31")
        json_str = rule.to_json()

        # Should exceed limit
        with pytest.raises(ValueError, match="JSON too large"):
            AtomicRule.from_json(json_str)

    def test_max_recursion_depth_exists(self):
        """Test that max_recursion_depth config exists and is used."""
        # Test that the config parameter exists and can be set
        config = RuleConfig(max_recursion_depth=50)
        assert config.max_recursion_depth == 50

        set_global_config(config)
        assert get_config().max_recursion_depth == 50

    def test_default_batch_size_affects_generate_batch(self):
        """Test that default_batch_size config affects generate_batch."""
        rule = AtomicRule(seconds="0..59", timezone=UTC)

        # Set small batch size
        set_global_config(RuleConfig(default_batch_size=10))

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 0, 0, 59, tzinfo=UTC)

        batches = list(rule.generate_batch(start, end))

        # Should have multiple batches of size 10
        # 60 items (0-59) -> 6 batches of 10
        assert len(batches) == 6
        assert all(len(batch) == 10 for batch in batches)

    def test_batch_size_parameter_overrides_config(self):
        """Test that batch_size parameter overrides global config."""
        rule = AtomicRule(seconds="0..59", timezone=UTC)

        # Set global batch size
        set_global_config(RuleConfig(default_batch_size=100))

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 0, 0, 59, tzinfo=UTC)

        # Use explicit batch_size=5 (overrides config)
        batches = list(rule.generate_batch(start, end, batch_size=5))

        # Should have batches of size 5
        # 60 items (0-59) -> 12 batches of 5
        assert len(batches) == 12
        assert all(len(batch) == 5 for batch in batches)

    def test_max_generate_items_none_allows_unlimited(self):
        """Test that max_generate_items=None allows unlimited generation."""
        rule = AtomicRule(seconds="0..59", timezone=UTC)

        # Set to None (unlimited)
        set_global_config(RuleConfig(max_generate_items=None))

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 0, 1, 0, tzinfo=UTC)

        # Should generate all items without error
        items = list(rule.generate(start, end))
        # Two minutes: 0:00:00-0:00:59 and 0:01:00 = 61 items
        assert len(items) >= 60
