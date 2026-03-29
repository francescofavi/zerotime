# Architecture - Zerotime

## Purpose

Describes the internal architecture of Zerotime: components, responsibilities, boundaries, and data flow.

## Scope

Covers the structural design of the library. Does not cover API usage (see [API Reference](API_REFERENCE.md)).

---

## Components

Zerotime is implemented as a single module (`core.py`) with clearly separated internal sections.

### DSLParser

**Responsibility**: Parse DSL string expressions into sets of integers.

**Boundary**: Stateless, pure parsing logic. No knowledge of rules or datetimes.

**Input**: DSL expression string, field metadata (name, valid range, allow negatives, optional year/month for negative day resolution).

**Output**: `set[int]` of matching values.

**Supported syntax**: single values, ranges (`..`), ranges with step (`../S`), global step (`/S`), lists (`,`), exclusions (`!`), negative days (`-N`).

### RuleConfig

**Responsibility**: Global configuration controlling search limits, generation caps, JSON size limits, and batch sizes.

**Boundary**: Dataclass with validation. Stored in a `ContextVar` for thread/async safety.

**Access**: Via `get_config()`, `set_global_config()`, `reset_config()`.

### Rule (Abstract Base)

**Responsibility**: Define the interface for all rules. Provides concrete implementations for `get_next()`, `get_prev()`, `generate_batch()`, `from_json()`, and operators (`+`, `&`, `-`).

**Boundary**: Cannot be instantiated directly. Subclasses must implement `generate()`, `generate_reverse()`, and `to_json()`.

### AtomicRule

**Responsibility**: Fundamental rule type. Defines temporal constraints using DSL expressions for each datetime field (months, days, weekdays, hours, minutes, seconds). All constraints must match (AND logic).

**Boundary**: Owns expression storage, parsed field caching (with thread-safe double-checked locking), and the core generation algorithm that iterates over year/month/day/time combinations.

**Key behaviors**:
- Lazy parsing: expressions are parsed on first use, then cached
- Negative day resolution: deferred to generation time (month-dependent)
- Timezone handling: converts input datetimes to rule timezone, validates tz-aware vs naive
- DST gap detection: skips non-existent times via UTC round-trip

### CombinedRule

**Responsibility**: Composite rule created by combining two rules with a set operator (union, intersection, difference).

**Boundary**: Delegates generation to child rules. Applies the operator logic during generation.

**Combination strategies**:
- **Union**: sorted merge of two generation streams with deduplication
- **Intersection**: batch-based — generates left rule in batches, filters against right rule matches
- **Difference**: batch-based — generates left rule in batches, excludes right rule matches

### Utility Functions

**Responsibility**: Internal helpers for datetime bounds validation, timezone normalization, weekday calculation (Zeller's congruence), DST-safe datetime creation, and search boundary calculation.

**Boundary**: Private (`_`-prefixed), used only by rule classes.

---

## Data Flow

### Rule Evaluation (get_next / generate)

```
Input datetime
    │
    ▼
Timezone normalization (_normalize_timezone)
    │
    ▼
Datetime bounds validation (_validate_datetime_bounds)
    │
    ▼
AtomicRule.generate() iterates:
    Year → Month → Day → Hour → Minute → Second
    │
    ├─ DSLParser.parse() for each field (cached after first call)
    ├─ _get_weekday() for weekday constraint check
    ├─ _create_datetime_with_tz() for DST-safe construction
    │
    ▼
Yield matching datetimes
```

### Combined Rule Evaluation

```
CombinedRule.generate()
    │
    ├─ left.generate()  ──┐
    ├─ right.generate() ──┤
    │                     ▼
    │              Operator logic (merge / filter / exclude)
    │                     │
    ▼                     ▼
               Yield combined matches
```

### JSON Serialization / Deserialization

```
Rule.to_json()                    Rule.from_json()
    │                                 │
    ▼                                 ▼
AtomicRule: field expressions    Detect type from "type" field
CombinedRule: recursive tree     AtomicRule: reconstruct from fields
    │                            CombinedRule: recursive reconstruction
    ▼                                 │
JSON string                          ▼
                                 Rule instance
```

---

## Thread Safety Model

- **Rule instances**: effectively immutable after construction
- **Parsed field caches**: protected by `threading.Lock` with double-checked locking pattern
- **Configuration**: stored in `contextvars.ContextVar`, inherits to child threads and async tasks
- **DSLParser**: stateless, no shared mutable state

---

## File Structure

```
src/zerotime/
├── __init__.py    # Public API exports, version
├── core.py        # All implementation (single module)
└── py.typed       # PEP 561 marker
```

The library follows a single-module design. All logic resides in `core.py`, organized by internal sections (constants, exceptions, utilities, DSL parser, configuration, rule classes).
