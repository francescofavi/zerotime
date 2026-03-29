"""
Example 07: Configuration
=========================
Using RuleConfig to control library behavior.
"""

from datetime import UTC, datetime

from zerotime import (
    AtomicRule,
    NoMatchFoundError,
    RuleConfig,
    get_config,
    reset_config,
    set_global_config,
)

# -----------------------------------------------------------------------------
# Default configuration
# -----------------------------------------------------------------------------

# View current configuration
config = get_config()
print("Default configuration:")
print(f"  max_years_search: {config.max_years_search}")
print(f"  max_generate_items: {config.max_generate_items}")
print(f"  max_json_size: {config.max_json_size}")
print(f"  max_recursion_depth: {config.max_recursion_depth}")
print(f"  default_batch_size: {config.default_batch_size}")

# -----------------------------------------------------------------------------
# Creating custom configuration
# -----------------------------------------------------------------------------

# All parameters have validation
try:
    RuleConfig(max_years_search=0)  # Must be positive
except ValueError as e:
    print(f"\nValidation error: {e}")

try:
    RuleConfig(max_generate_items=-1)  # Must be positive or None
except ValueError as e:
    print(f"Validation error: {e}")

# Valid configuration
custom = RuleConfig(
    max_years_search=10,
    max_generate_items=50000,
    max_json_size=500000,
    max_recursion_depth=50,
    default_batch_size=1000,
)
print(f"\nCustom config created: max_years_search={custom.max_years_search}")

# -----------------------------------------------------------------------------
# Setting global configuration
# -----------------------------------------------------------------------------

# Apply configuration globally
set_global_config(RuleConfig(max_years_search=2))
print(f"\nAfter set_global_config: max_years_search={get_config().max_years_search}")

# Now all operations use this configuration
rule = AtomicRule(months="2", days="29", hours="0", minutes="0", seconds="0", timezone=UTC)

now = datetime(2025, 1, 1, tzinfo=UTC)
try:
    # With max_years_search=2, this will fail (next Feb 29 is in 2028)
    rule.get_next(now)
except NoMatchFoundError as e:
    print(f"Search failed with 2-year limit: {e}")

# Extend the search range
set_global_config(RuleConfig(max_years_search=5))
next_leap = rule.get_next(now)
print(f"With 5-year limit, found: {next_leap.strftime('%Y-%m-%d')}")

# -----------------------------------------------------------------------------
# Resetting configuration
# -----------------------------------------------------------------------------

reset_config()
print(f"\nAfter reset: max_years_search={get_config().max_years_search}")  # Back to 5

# -----------------------------------------------------------------------------
# Overriding config per-operation
# -----------------------------------------------------------------------------

# Configuration can be overridden at call time
set_global_config(RuleConfig(max_years_search=1))

# Global config says 1 year, but we override to 5
next_leap = rule.get_next(now, max_years=5)
print(f"\nGlobal=1 year, override=5 years: {next_leap.strftime('%Y-%m-%d')}")

reset_config()

# -----------------------------------------------------------------------------
# max_generate_items - preventing runaway generation
# -----------------------------------------------------------------------------

# Rule that matches every second
every_second = AtomicRule(timezone=UTC)

start = datetime(2025, 1, 1, tzinfo=UTC)
end = datetime(2025, 1, 1, 0, 1, 0, tzinfo=UTC)  # 1 minute = 61 items

# Set a limit
set_global_config(RuleConfig(max_generate_items=10))

try:
    # This will fail after generating 10 items
    list(every_second.generate(start, end))
except ValueError as e:
    print(f"\nGeneration limit exceeded: {e}")

# Override limit per-call
items = list(every_second.generate(start, end, max_items=100))
print(f"With max_items=100: generated {len(items)} items")

# None means unlimited (be careful!)
set_global_config(RuleConfig(max_generate_items=None))
items = list(every_second.generate(start, end))
print(f"With unlimited: generated {len(items)} items")

reset_config()

# -----------------------------------------------------------------------------
# default_batch_size - batch processing
# -----------------------------------------------------------------------------

set_global_config(RuleConfig(default_batch_size=20))

rule = AtomicRule(minutes="0", seconds="0", timezone=UTC)  # Every hour

start = datetime(2025, 1, 1, tzinfo=UTC)
end = datetime(2025, 1, 2, 23, 59, 59, tzinfo=UTC)  # 2 days = 48 hours

print("\nBatch generation with default_batch_size=20:")
for i, batch in enumerate(rule.generate_batch(start, end)):
    print(f"  Batch {i + 1}: {len(batch)} items")

# Override per-call
print("\nWith batch_size=10 override:")
for i, batch in enumerate(rule.generate_batch(start, end, batch_size=10)):
    print(f"  Batch {i + 1}: {len(batch)} items")

reset_config()

# -----------------------------------------------------------------------------
# max_json_size - security limit
# -----------------------------------------------------------------------------

set_global_config(RuleConfig(max_json_size=100))

rule = AtomicRule(
    months="1..12",
    days="1..31",
    weekdays="1..7",
    hours="0..23",
    minutes="0..59",
    seconds="0..59",
)
json_str = rule.to_json()
print(f"\nJSON size: {len(json_str)} bytes")

try:
    # Deserialization fails if JSON exceeds limit
    AtomicRule.from_json(json_str)
except ValueError as e:
    print(f"JSON size limit error: {e}")

reset_config()

# Now it works
restored = AtomicRule.from_json(json_str)
print("JSON restored successfully with default limit")

# -----------------------------------------------------------------------------
# Configuration for different environments
# -----------------------------------------------------------------------------


def configure_for_production():
    """Restrictive configuration for production."""
    set_global_config(
        RuleConfig(
            max_years_search=5,
            max_generate_items=10000,  # Prevent accidental large generations
            max_json_size=100000,  # 100 KB limit
            max_recursion_depth=20,  # Limit nested rules
            default_batch_size=1000,
        )
    )


def configure_for_batch_processing():
    """Configuration for batch/ETL jobs."""
    set_global_config(
        RuleConfig(
            max_years_search=50,  # Historical data
            max_generate_items=None,  # Unlimited
            max_json_size=10_000_000,  # 10 MB
            default_batch_size=50000,  # Large batches
        )
    )


def configure_for_testing():
    """Configuration for unit tests."""
    set_global_config(
        RuleConfig(
            max_years_search=2,  # Fast tests
            max_generate_items=1000,
            default_batch_size=100,
        )
    )


# Example usage
print("\nProduction config:")
configure_for_production()
print(f"  max_generate_items: {get_config().max_generate_items}")

print("\nBatch processing config:")
configure_for_batch_processing()
print(f"  max_generate_items: {get_config().max_generate_items}")

reset_config()
