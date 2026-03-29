# Development - Zerotime

## Purpose

Setup instructions for contributors: environment, testing, linting, and running examples.

## Scope

Covers local development workflow. Does not cover API usage (see [API Reference](API_REFERENCE.md)) or architecture (see [ARCHITECTURE.md](ARCHITECTURE.md)).

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

---

## Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/francescofavi/zerotime.git
cd zerotime
uv sync
```

---

## Running Tests

```bash
uv run pytest
```

With coverage report:

```bash
uv run pytest --cov=zerotime --cov-report=term-missing
```

---

## Linting and Type Checking

```bash
# Ruff (linting + formatting check)
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Mypy (type checking)
uv run mypy src/

# Bandit (security analysis)
uv run bandit -r src/ -c pyproject.toml

# Vulture (dead code detection)
uv run vulture src/
```

---

## Running Examples

All examples are standalone scripts in the `examples/` directory:

```bash
uv run python examples/01_basic_usage.py
uv run python examples/02_dsl_syntax.py
# ... etc.
```

See [examples/README.md](../examples/README.md) for a description of each example.

---

## Project Structure

```
src/zerotime/
├── __init__.py    # Public API exports, version
├── core.py        # All implementation (single module)
└── py.typed       # PEP 561 marker
```

---

## Build System

- Build backend: `hatchling`
- Package manager: `uv`
- Version source: `src/zerotime/__init__.py`
