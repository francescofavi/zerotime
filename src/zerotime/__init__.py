"""Zerotime — datetime rule engine for recurring time patterns.

Features:
- Declarative DSL for each datetime field — values, ranges, steps, lists, exclusions, last-day-of-month negatives.
- Composable rules via Python operators — `+` union, `&` intersection, `-` difference, with arbitrary nesting.
- Lazy generation — `generate()` yields one match at a time; `generate_batch()` for memory-efficient bulk runs.
- Temporal navigation — `get_next()` / `get_prev()` find the nearest match in either direction.
- Immutable builders — `with_*` methods return a new rule; originals are never mutated.
- Timezone awareness — optional timezone binding, DST gap handling, naive/aware mismatch detection.
- JSON round-trip — `to_json()` / `from_json()` for persistence, with size and depth caps.
- Thread-safe parsed-field cache and `ContextVar`-based configuration.
- Zero runtime dependencies — standard library only; PEP 561 typed.

Copyright (c) 2025-present Francesco Favi
License: MIT
"""

from zerotime.core import (
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

__version__ = "0.1.0"
__author__ = "Francesco Favi"
__email__ = "14098835+francescofavi@users.noreply.github.com"

__all__ = [
    "Rule",
    "AtomicRule",
    "CombinedRule",
    "RecurrentError",
    "InvalidExpressionError",
    "InvalidRuleError",
    "NoMatchFoundError",
    "RuleConfig",
    "get_config",
    "set_global_config",
    "reset_config",
]
