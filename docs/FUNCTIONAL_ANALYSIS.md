# Functional Analysis - Zerotime

## Purpose

Describes the functional behavior and business logic of Zerotime: what the library does, how its features compose, and the data flows users interact with.

## Scope

Covers user-facing functional behavior and logic flows. Does not cover internal implementation details (see [ARCHITECTURE.md](ARCHITECTURE.md)) or API signatures (see [API_REFERENCE.md](API_REFERENCE.md)).

---

## Core Concept

Zerotime models **recurring instants in time** as composable rules. A rule answers one question: "does this datetime match?" From that single predicate, all operations derive: finding the next/previous match, generating sequences, combining rules with set operations.

---

## Functional Flows

### 1. Rule Definition

A user defines temporal constraints using DSL string expressions. Each field (months, days, weekdays, hours, minutes, seconds) specifies which values are valid. A datetime matches an `AtomicRule` only when ALL fields match simultaneously (AND logic).

```
User input: AtomicRule(months="3,6,9,12", days="-1", hours="17", minutes="0", seconds="0")
                │
                ▼
Validation: each DSL expression is parsed and checked for valid syntax and range
                │
                ▼
Result: immutable rule object ready for querying
```

**Key behaviors:**
- Validation happens at construction time (fail-fast)
- Negative days (`-1` = last day) are validated against January (31 days) at construction; month-specific validation happens at generation time
- Rules are immutable: `with_*` methods return new instances

### 2. Temporal Navigation

`get_next()` and `get_prev()` find the nearest matching datetime in a given direction.

```
User input: rule.get_next(base_datetime)
                │
                ▼
Search range: base + 1 second  →  base + max_years
                │
                ▼
Generate forward from search start
                │
                ▼
First match found → return it
No match found   → raise NoMatchFoundError
```

**Key behaviors:**
- Search range defaults to 5 years (configurable via `RuleConfig.max_years_search`)
- `get_next()` starts 1 second after `base` (never returns `base` itself)
- `get_prev()` ends 1 second before `base` (never returns `base` itself)
- Leap year edge case: when `base` is Feb 29, the search boundary extends to Mar 1 of the target year

### 3. Sequence Generation

`generate()` yields all matching datetimes in a range, in chronological order.

```
User input: rule.generate(start, end)
                │
                ▼
Iterate: year → month → day → hour → minute → second
                │
                ├─ Skip months not in constraint
                ├─ Resolve negative days for current month
                ├─ Check weekday constraint
                ├─ Skip non-existent times (DST gaps)
                │
                ▼
Yield each matching datetime in order
```

**Key behaviors:**
- Lazy evaluation: datetimes are yielded one at a time (generator)
- `start` and `end` are inclusive
- `start > end` raises `ValueError`
- Optional `max_items` limit prevents runaway generation
- `generate_reverse()` yields in reverse chronological order (latest first)
- `generate_batch()` collects results into lists of configurable size for bulk processing

### 4. Rule Combination

Rules combine via Python operators to create `CombinedRule` instances.

| Operator | Meaning | Behavior |
|----------|---------|----------|
| `+` (union) | Either matches | Sorted merge of two generation streams with deduplication |
| `&` (intersection) | Both match | Left rule generates in batches, filtered against right rule matches |
| `-` (difference) | First matches, second does not | Left rule generates in batches, excluding right rule matches |

```
User input: working_hours = business_hours - lunch_break
                │
                ▼
CombinedRule created with operator="difference"
                │
                ▼
On generate(): business_hours generates in batches
               lunch_break generates for each batch range
               Datetimes in lunch_break are excluded from output
```

**Key behaviors:**
- Combinations can be nested: `(rule1 + rule2) & rule3` works
- Both operands must have matching timezone awareness (both tz-aware or both tz-naive); mismatches raise `InvalidRuleError`
- Union uses O(1) memory merge of two sorted streams
- Intersection and difference use batch-based filtering

### 5. JSON Serialization

Rules serialize to/from JSON for persistence. The format is self-describing: the `"type"` field determines the reconstruction path.

```
rule.to_json()                         Rule.from_json(json_str)
    │                                       │
    ▼                                       ▼
AtomicRule → field expressions         Read "type" field
CombinedRule → recursive tree              │
    │                                  ├─ "atomic"  → AtomicRule.from_json()
    ▼                                  ├─ "combined" → CombinedRule.from_json() (recursive)
JSON string                            │
                                       ▼
                                   Rule instance
```

**Key behaviors:**
- Atomic rules serialize as: `{"type": "atomic", "months": "...", "days": "...", ...}`
- Combined rules serialize as: `{"type": "combined", "operator": "...", "left": {...}, "right": {...}}`
- Size limit: `max_json_size` (default 1 MB) prevents denial-of-service
- Depth limit: `max_recursion_depth` (default 100) prevents stack overflow on deeply nested rules
- Timezone round-trip: only UTC offsets are preserved, not IANA zone names

### 6. Timezone Handling

Rules optionally bind to a timezone. When bound, all input datetimes must be timezone-aware.

```
Timezone-bound rule: AtomicRule(hours="12", timezone=UTC)
                          │
                          ▼
Input datetime is converted to rule's timezone
                          │
                          ▼
Matching and generation happen in the rule's timezone
                          │
                          ▼
Output datetimes carry the rule's timezone
```

**Key behaviors:**
- Naive datetime + tz-bound rule = `ValueError`
- Tz-aware datetime + tz-free rule = works (datetime used as-is)
- DST spring forward gaps: non-existent local times are silently skipped
- DST fall back ambiguity: the first occurrence (fold=0) is used

---

## DSL Expression Resolution

The DSL is resolved in two stages:

**Stage 1 - Construction time**: expressions are validated for syntax and range. Negative days are validated against January (31 days) as a permissive check.

**Stage 2 - Generation time**: expressions are parsed into concrete integer sets for the specific year/month context. Negative days are resolved to actual day numbers (e.g., `-1` in February 2024 = day 29). Results are cached for rules without negative days.

---

## Configuration Impact

`RuleConfig` affects behavior globally (via `ContextVar`, inherited by child threads and async tasks):

| Setting | Affects | Default |
|---------|---------|---------|
| `max_years_search` | `get_next()`, `get_prev()` search range | 5 |
| `max_generate_items` | `generate()`, `generate_reverse()` item cap | None (unlimited) |
| `max_json_size` | `from_json()` input size limit | 1,000,000 bytes |
| `max_recursion_depth` | `from_json()` nesting depth limit | 100 |
| `default_batch_size` | `generate_batch()` items per batch | 10,000 |

---

## Constraints and Limitations

- **Second-level resolution**: microseconds in input datetimes are ignored during matching
- **Year range**: 1 to 9999
- **Negative days**: only in the `days` field
- **Timezone serialization**: IANA zone names are not preserved in JSON (only UTC offsets)
- **No sub-second scheduling**: the minimum interval between matches is 1 second
