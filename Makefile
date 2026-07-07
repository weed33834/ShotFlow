.PHONY: help check setup docker test lint lint-backend lint-frontend lint-automation format sync clean

help:
	@echo "ShotFlow — Common commands"
	@echo "  make check           Verify project structure (project health check)"
	@echo "  make setup           Install all deps (backend + automation + frontend)"
	@echo "  make docker          Start Docker containers"
	@echo "  make test            Run health check, linters, backend pytest, preflight"
	@echo "  make lint            Run all linters (ruff, black, isort, eslint)"
	@echo "  make lint-backend    Run backend Python linters"
	@echo "  make lint-frontend   Run frontend eslint + typecheck"
	@echo "  make lint-automation Run 08_Automation/tests Python linters"
	@echo "  make format          Auto-format Python code"
	@echo "  make sync            Push to GitHub and GitCode"
	@echo "  make clean           Remove temp files"

check:
	python 08_Automation/project_health_check.py

setup:
	pip install -r backend/requirements.txt
	pip install -r backend/requirements-dev.txt
	pip install -r 08_Automation/requirements-dev.txt
	cd frontend && npm install

docker:
	docker compose up -d

test: check lint-backend lint-automation lint-frontend
	cd backend && python -m pytest tests/ -q
	python 08_Automation/preflight_check.py --dry-run
	python 08_Automation/check_doc_links.py

lint: lint-backend lint-automation lint-frontend

lint-backend:
	ruff check backend
	black --check backend
	isort --check-only backend

lint-automation:
	ruff check 08_Automation tests
	black --check 08_Automation tests
	isort --check-only 08_Automation tests

lint-frontend:
	cd frontend && npm run lint && npx tsc --noEmit

format:
	black backend 08_Automation tests
	isort backend 08_Automation tests

sync:
	bash 08_Automation/sync_repos.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.log" -delete
	rm -rf frontend/dist
