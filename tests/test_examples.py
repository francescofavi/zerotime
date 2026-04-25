"""Smoke tests for the runnable scripts under examples/.

Each example must exit 0 within the timeout, with no traceback in stderr.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE_TIMEOUT_S = 30
EXAMPLE_SCRIPTS = sorted(EXAMPLES_DIR.glob("[0-9][0-9]_*.py"))


def test_examples_directory_exists():
    assert EXAMPLES_DIR.is_dir()


def test_examples_readme_present():
    assert (EXAMPLES_DIR / "README.md").is_file()


def test_examples_discovered():
    # Sanity check: catch accidental example deletions.
    assert len(EXAMPLE_SCRIPTS) >= 1


@pytest.mark.parametrize("script", EXAMPLE_SCRIPTS, ids=lambda p: p.name)
def test_example_runs_successfully(script: Path):
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=EXAMPLE_TIMEOUT_S,
        check=False,
    )
    assert result.returncode == 0, (
        f"{script.name} exited with code {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "Traceback" not in result.stderr, f"{script.name} produced a traceback:\n{result.stderr}"
