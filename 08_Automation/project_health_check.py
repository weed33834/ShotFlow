#!/usr/bin/env python3
"""Project health check script."""

import argparse
import sys

from common import PROJECT_ROOT

REQUIRED_FILES = [
    "README.md",
    "README.zh.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "docs/AIGC_Experience_Chain.md",
    "docs/AIGC_Experience_Chain.zh.md",
    "docs/COST_ANALYSIS.md",
    "docs/TROUBLESHOOTING.md",
    "SECURITY.md",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
    "pyproject.toml",
    ".editorconfig",
    ".gitattributes",
    ".dockerignore",
    ".pre-commit-config.yaml",
    ".env.example",
    ".github/workflows/ci.yml",
    "08_Automation/sync_repos.sh",
    "08_Automation/preflight_check.py",
    "08_Automation/project_health_check.py",
    "docs/index.html",
    "docs/assets/style.css",
    "docs/assets/script.js",
    ".github/workflows/pages.yml",
    "examples/echo-of-singularity/README.md",
    "examples/echo-of-singularity/production_plan.md",
    "examples/echo-of-singularity/production_log.md",
    "examples/echo-of-singularity/character_bible_ava.md",
    "examples/echo-of-singularity/character_bible_ava.zh.md",
    "examples/echo-of-singularity/shot_tracker.md",
    "examples/echo-of-singularity/shot_tracker.zh.md",
]

REQUIRED_DIRS = [
    "01_Assets",
    "02_Scripts",
    "03_Workflows",
    "04_SOP",
    "05_Output",
    "06_Research",
    "07_Team",
    "08_Automation",
    "09_Release",
    "examples",
    ".github/ISSUE_TEMPLATE",
]


def check():
    errors = []
    for f in REQUIRED_FILES:
        path = PROJECT_ROOT / f
        if not path.exists():
            errors.append(f"Missing file: {f}")

    for d in REQUIRED_DIRS:
        path = PROJECT_ROOT / d
        if not path.exists():
            errors.append(f"Missing directory: {d}")

    if errors:
        print("Project health check failed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("Project health check passed.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — 项目结构健康检查",
    )
    parser.parse_args()
    sys.exit(check())


if __name__ == "__main__":
    main()
