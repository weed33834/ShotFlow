"""Basic health tests."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_health_check_passes():
    result = subprocess.run(
        [sys.executable, "08_Automation/project_health_check.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_readme_exists():
    assert (ROOT / "README.md").exists()
    assert (ROOT / "README.zh.md").exists()


def test_docs_site_exists():
    assert (ROOT / "docs" / "index.html").exists()
    assert (ROOT / "docs" / "assets" / "style.css").exists()
    assert (ROOT / "docs" / "assets" / "script.js").exists()


def test_case_study_exists():
    case = ROOT / "examples" / "echo-of-singularity"
    assert (case / "README.md").exists()
    assert (case / "production_plan.md").exists()
    assert (case / "production_log.md").exists()
    assert (case / "character_bible_ava.md").exists()
    assert (case / "character_bible_ava.zh.md").exists()
    assert (case / "shot_tracker.md").exists()
    assert (case / "shot_tracker.zh.md").exists()


def test_dev_requirements_exist():
    assert (ROOT / "08_Automation" / "requirements-dev.txt").exists()
