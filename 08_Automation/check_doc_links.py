#!/usr/bin/env python3
"""Check markdown documentation links.

Scans all ``.md`` files in the repository (excluding ``.git``, ``node_modules``,
``backend``, ``frontend``) for markdown inline links ``[text](url)`` and validates
internal relative links. External URLs, anchor-only links (``#xxx``), and
``mailto:`` links are skipped to keep CI stable.

- Internal relative link: resolved against the current markdown file's directory;
  the target must exist (files and directories both count as valid).
- External URL (``http://`` / ``https://``): skipped (counted only).
- Anchor link (``#xxx``): skipped.
- ``mailto:``: skipped.

Exit code 0 if every internal link resolves; 1 if any broken link is found.

Usage:
    python 08_Automation/check_doc_links.py
"""

import re
import sys
from pathlib import Path

from common import PROJECT_ROOT

# Directories to skip when scanning for markdown files. Any path component
# matching one of these names causes the file to be excluded.
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "backend",
    "frontend",
    ".venv",
    "venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    "dist",
}

# Match inline markdown links [text](url) and image links ![alt](url).
# The URL is the first non-space, non-`)` run after `(`; an optional title
# such as [text](url "title") is ignored.
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")

# Fenced code block delimiter: a line starting with ``` (optionally indented
# or followed by a language tag). Toggles the in-code-block state.
FENCE_RE = re.compile(r"^\s*```")


def is_external(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def is_anchor(url: str) -> bool:
    return url.startswith("#")


def is_mailto(url: str) -> bool:
    return url.lower().startswith("mailto:")


def find_markdown_files(root: Path):
    """Return all .md files under root, excluding EXCLUDE_DIRS."""
    files = []
    for path in sorted(root.rglob("*.md")):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def check_file(md_path: Path):
    """Check a single markdown file.

    Returns (broken, internal, external, anchor, mailto) where ``broken`` is a
    list of (line_no, url, reason) tuples.
    """
    broken = []
    internal = 0
    external = 0
    anchor = 0
    mailto = 0
    in_fence = False

    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        broken.append((0, "", f"cannot read file: {exc}"))
        return broken, internal, external, anchor, mailto

    for line_no, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            # Skip links inside fenced code blocks.
            continue
        for match in LINK_RE.finditer(line):
            url = match.group(2).strip()
            if is_mailto(url):
                mailto += 1
            elif is_anchor(url):
                anchor += 1
            elif is_external(url):
                external += 1
            else:
                internal += 1
                target = (md_path.parent / url).resolve()
                if not target.exists():
                    broken.append((line_no, url, f"target does not exist: {target}"))
    return broken, internal, external, anchor, mailto


def main() -> int:
    files = find_markdown_files(PROJECT_ROOT)
    total_broken = []
    total_internal = 0
    total_external = 0
    total_anchor = 0
    total_mailto = 0

    for md_path in files:
        broken, internal, external, anchor, mailto = check_file(md_path)
        total_internal += internal
        total_external += external
        total_anchor += anchor
        total_mailto += mailto
        rel = md_path.relative_to(PROJECT_ROOT)
        for line_no, url, reason in broken:
            total_broken.append((rel, line_no, url, reason))

    if total_broken:
        print(f"Broken links found: {len(total_broken)}\n")
        for rel, line_no, url, reason in total_broken:
            print(f"  {rel}:{line_no}: {url}  ({reason})")
        print(
            f"\nScanned {len(files)} md files, checked {total_internal} internal "
            f"links, skipped {total_external} external + {total_anchor} anchor + "
            f"{total_mailto} mailto."
        )
        return 1

    print(
        f"OK: scanned {len(files)} md files, checked {total_internal} internal "
        f"links, skipped {total_external} external + {total_anchor} anchor + "
        f"{total_mailto} mailto."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
