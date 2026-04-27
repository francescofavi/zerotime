#!/usr/bin/env bash

set -e

echo "zerotime - Run Tests & Examples"
echo "=========================================="
echo ""

# ---- Tests ----
echo "[1/3] Running tests..."
echo "--------------------------------------"
uv run pytest tests/ -v
echo ""

# ---- Quality checks ----
echo "[2/3] Running quality checks..."
echo "--------------------------------------"
uv run ruff check src/ tests/
uv run mypy src/
echo "+ Quality checks passed"
echo ""

# ---- Examples ----
echo "[3/3] Running examples..."
echo "--------------------------------------"
for example in examples/[0-9]*.py; do
    echo ""
    echo ">>> $example"
    echo "---"
    uv run python "$example"
done

echo ""
echo "=========================================="
echo "+ All done!"
echo "=========================================="
