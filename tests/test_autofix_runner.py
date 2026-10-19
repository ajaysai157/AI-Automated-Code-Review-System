
import os
from pathlib import Path

import django

# Configure Django before importing application models.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import sys
sys.path.insert(0, str(BACKEND_DIR))

django.setup()

from app.agents.autofix import run_project_tests


def test_runner_detects_passing_tests(tmp_path: Path):
    (tmp_path / "test_sample.py").write_text(
        "def test_example():\n    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )

    result = run_project_tests(str(tmp_path))

    assert result["passed"] is True, result
    assert result["status"] == "tests_passed"


def test_runner_detects_failing_tests(tmp_path: Path):
    (tmp_path / "test_sample.py").write_text(
        "def test_example():\n    assert 2 + 2 == 5\n",
        encoding="utf-8",
    )

    result = run_project_tests(str(tmp_path))

    assert result["passed"] is False
    assert result["status"] == "tests_failed"
