"""Package initialization.

Copyright (c) 2025 Francesco Favi
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

__version__ = "0.1.1"
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
