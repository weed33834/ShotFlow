# Tests

Repo-root integration and health-check tests. Backend unit/integration tests live in
[`backend/tests/`](../backend/tests/) (179 tests, in-memory SQLite).

## Files

- [`test_health.py`](./test_health.py) — project structure health check (mirrors
  `08_Automation/project_health_check.py`), asserts key files and directories exist.
- [`test_video_quality.py`](./test_video_quality.py) — video QA checks (resolution,
  duration, codec) for generated clips under `05_Output/`.

## Run

```bash
# from repo root
python -m pytest tests/ -q

# or via Makefile
make test
```

These tests have no external dependencies and run on CPU. For the full backend suite
(API, models, services, queue, render dispatch), run:

```bash
cd backend && python -m pytest tests/ -q
```
