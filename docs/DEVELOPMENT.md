# Development - Zerotime

## Purpose

Setup instructions for contributors: environment, testing, quality pipeline, pre-commit hooks, commit conventions, examples, and release process.

## Scope

Covers the local development workflow. Does not cover API usage (see [API_REFERENCE.md](API_REFERENCE.md)) or internal architecture (see [ARCHITECTURE.md](ARCHITECTURE.md)).

---

## Prerequisites

- Python 3.12 or later.
- [`uv`](https://docs.astral.sh/uv/) — the project uses `uv` for environment, dependency, and run management. `pip` is not used.
- `git`.

The repo declares `requires-python = ">=3.12"`. CI runs the suite on 3.12, 3.13 and 3.14.

---

## Clone and setup

```bash
git clone https://github.com/francescofavi/zerotime.git
cd zerotime
uv sync --group dev
```

`uv sync --group dev` installs the runtime package (editable) plus every dev tool declared in `[dependency-groups].dev` in `pyproject.toml` (pytest, pytest-cov, pytest-mock, ruff, mypy, bandit, vulture, pre-commit).

---

## Running tests

```bash
uv run pytest
```

With branch coverage and a per-line miss report:

```bash
uv run pytest --cov=zerotime --cov-report=term-missing
```

The test suite lives in `tests/` (`test_config.py`, `test_core.py`, `test_edge_cases.py`, `test_coverage.py`, `test_examples.py`). Configuration is read from the `[tool.pytest.ini_options]` section of `pyproject.toml` (`testpaths = ["tests"]`, `addopts = "-v"`). Coverage settings live in `[tool.coverage.run]` and `[tool.coverage.report]`. The suite is expected to stay at 100 % line and branch coverage; `tests/test_examples.py` runs every `examples/NN_*.py` script via `subprocess` and asserts a clean exit.

---

## Quality pipeline

The project enforces four quality tools. CI runs all of them; running them locally before pushing avoids round trips.

```bash
# Lint
uv run ruff check src/ tests/

# Format check (does not rewrite)
uv run ruff format --check src/ tests/

# Static type check
uv run mypy src/

# Security audit
uv run bandit -r src/ -c pyproject.toml

# Dead code detection
uv run vulture src/
```

Tool configuration:

- **ruff** — `[tool.ruff]` and `[tool.ruff.lint]` in `pyproject.toml`. Selected rule families: `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `C4`, `SIM`. Line length 100. Target Python 3.12.
- **mypy** — `[tool.mypy]` in `pyproject.toml`. Strict-optional, warn-return-any, warn-unreachable. `ignore_missing_imports = true` (project has no third-party runtime deps).
- **bandit** — `[tool.bandit]` in `pyproject.toml`. Skips `B101`, `B403`, `B110`. Excludes `tests/`, `examples/`, `scripts/`.
- **vulture** — `[tool.vulture]` in `pyproject.toml`. `min_confidence = 80`.

---

## Pre-commit hooks

Install the hooks once after cloning:

```bash
uv run pre-commit install
```

The hook configuration lives in `.pre-commit-config.yaml`. Hooks run on every `git commit` and reject commits when any hook fails. To run them on the whole repo (without committing):

```bash
uv run pre-commit run --all-files
```

If a hook auto-fixes a file (e.g. ruff format), re-stage and re-commit.

---

## Commit conventions

The repo follows [Conventional Commits](https://www.conventionalcommits.org/). The release pipeline (`release-please`) parses these prefixes to derive the next version and to assemble `CHANGELOG.md`. Common prefixes:

- `feat:` — new user-visible capability (minor bump).
- `fix:` — bug fix (patch bump).
- `docs:` — documentation only (no version bump).
- `chore:` — repository hygiene, build files, dependencies (no version bump).
- `test:` — tests added or updated.
- `refactor:` — internal restructuring without behavior change.

CI validates the format on pull requests. Use the imperative mood in the subject line and keep it under ~70 characters.

---

## Running examples

Each script in `examples/` is self-contained and prints its inputs, intermediate results, and outputs. Run any of them directly:

```bash
uv run python examples/01_basic_usage.py
uv run python examples/06_timezones.py
```

See [`examples/README.md`](../examples/README.md) for the full index.

---

## Project structure

```
src/zerotime/
├── __init__.py    # Public API exports, version
├── core.py        # All implementation (single module)
└── py.typed       # PEP 561 marker
```

The library is intentionally a single implementation module. Internal sections inside `core.py` are separated by comment banners (constants, exceptions, utilities, DSL parser, configuration, rule classes).

---

## Build system

- Build backend: `hatchling`.
- Version source: `src/zerotime/__init__.py` — `[tool.hatch.version].path` reads `__version__` from there.
- Package layout: `src/zerotime/` — declared in `[tool.hatch.build.targets.wheel].packages`.
- Sdist exclusions: `[tool.hatch.build.targets.sdist].exclude` filters out IDE caches, internal docs, scripts, pre-commit config, GitHub workflows, and other repo-only files.

Build locally:

```bash
uv build
```

Output lands in `dist/` (sdist + wheel).

---

## Release process

Releases are automated through [`release-please`](https://github.com/googleapis/release-please) and a manual `publish.yml` GitHub Actions workflow.

1. Land Conventional Commits on `main`.
2. `release-please` opens (or updates) a release PR that bumps the version in `src/zerotime/__init__.py`, updates `CHANGELOG.md`, and updates `.release-please-manifest.json`.
3. Merging the release PR creates a Git tag and a GitHub Release.
4. The `publish.yml` workflow (Trusted Publishing, OIDC) is dispatched manually from the Actions UI to push the built artifacts to PyPI.

Files that participate in the release pipeline:

- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — lint, type-check, test on PR and on `main`.
- [`.github/workflows/release.yml`](../.github/workflows/release.yml) — runs `release-please` on `main`.
- [`.github/workflows/publish.yml`](../.github/workflows/publish.yml) — builds and publishes to PyPI via Trusted Publishing.
- [`release-please-config.json`](../release-please-config.json) — release-please configuration (release-type, extra-files, changelog path).
- [`.release-please-manifest.json`](../.release-please-manifest.json) — current released version (do not hand-edit).

PyPI Trusted Publishing means the workflow exchanges an OIDC token for a short-lived PyPI credential; there is no long-lived API token in repository secrets.
