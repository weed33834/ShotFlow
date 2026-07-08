# Developer Checklist

This checklist must be reviewed before every commit and pull request.
It ensures consistent quality and prevents common issues.

## Before You Start

- [ ] Pull the latest `main` branch
- [ ] Create a properly named branch (`feat/`, `fix/`, `docs/`, etc.)
- [ ] Open an issue for non-trivial changes to align on the approach

## Before Every Commit

- [ ] Code compiles/builds without errors
- [ ] Linter passes (run `make lint` or equivalent)
- [ ] Formatter applied (run `make format` or equivalent)
- [ ] No `console.log`, `print()`, or debug statements in production code
- [ ] No commented-out code blocks
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] No `any` types in TypeScript (without justification)
- [ ] No unused imports or variables
- [ ] No trailing whitespace
- [ ] Files end with a newline
- [ ] Commit message follows Conventional Commits format
- [ ] One logical change per commit

## Before Every Pull Request

- [ ] All CI checks are green
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] PR description filled out completely
- [ ] Related issue referenced (`Closes #N`)
- [ ] PR is under 400 lines of diff (split if larger)
- [ ] No merge conflicts with `main`
- [ ] Branch is up to date with `main`
- [ ] Self-reviewed your own code
- [ ] Documentation updated if needed

## Open Issues and PRs

Check regularly and address:

- [ ] Any open issues assigned to you
- [ ] Any PRs awaiting your review
- [ ] Any failing CI pipelines
- [ ] Any Dependabot/dependency update PRs to review and merge
- [ ] Any stale branches that should be deleted

## Redundant File Check

Before pushing, verify no junk files are included:

- [ ] No `.DS_Store`, `Thumbs.db`, or OS-specific files
- [ ] No `node_modules/`, `__pycache__/`, or build output
- [ ] No `.env` files (only `.env.example`)
- [ ] No `*.log`, `*.bak`, `*.orig`, `*.swp` files
- [ ] No large binary files unless necessary
- [ ] No IDE-specific config files (`.idea/`, `.vscode/` should be gitignored)

## Update Check

Periodically verify:

- [ ] Dependencies are up to date
- [ ] Security vulnerabilities addressed
- [ ] README and documentation reflect current state
- [ ] CHANGELOG updated for releases
- [ ] License information is current

## Warning and Alert Check

Before merging:

- [ ] No new TypeScript/ESLint warnings introduced
- [ ] No new Python linter (ruff/flake8) warnings
- [ ] No deprecation warnings from dependencies
- [ ] No security scan warnings (CodeQL, gitleaks)
- [ ] CI pipeline is fully green (not just passing with warnings)

## Codebase Cleanup Check

Periodically (at least once per sprint), perform a thorough cleanup:

### File Cleanup
- [ ] Remove empty directories
- [ ] Delete unused configuration files (e.g., old `.env.example` variants)
- [ ] Remove duplicate version files (keep only one: `VERSION` or `pyproject.toml`)
- [ ] Delete orphaned modules/scripts that are not imported or referenced
- [ ] Remove unused template files (e.g., `*.template.json` if not referenced)

### Configuration Cleanup
- [ ] Remove irrelevant language configs from `.editorconfig` (e.g., Go in a Python project)
- [ ] Remove unused package ecosystems from `dependabot.yml`
- [ ] Verify all config files match the actual tech stack (Python + TypeScript/React + Docker)

### Documentation Cleanup
- [ ] Merge duplicate docs (e.g., same content in different files)
- [ ] Delete outdated development plans (keep only one: `PROJECT_PLAN.md` or `ROADMAP.md`)
- [ ] Ensure README Quick Start doesn't duplicate `QUICKSTART.md`
- [ ] Update version numbers in all docs to match `VERSION` file
- [ ] Verify license references in all docs match the actual LICENSE file (CNCL v1.0, not MIT)
- [ ] Remove references to non-existent files or broken links

### Test Cleanup
- [ ] Identify and merge duplicate test files
- [ ] Delete tests for removed features
- [ ] Ensure all test files have actual test cases (no empty files)
- [ ] Verify test counts mentioned in docs match actual test counts

### Code Quality
- [ ] Remove dead code (unreachable functions, unused imports)
- [ ] Verify all API endpoints have corresponding tests
- [ ] Check for hardcoded secrets or credentials
