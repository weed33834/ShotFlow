# Contributing to ShotFlow

Thank you for your interest in contributing to ShotFlow. This document outlines the guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

By participating in this project, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md). Please report unacceptable behavior to the maintainers.

## Getting Started

1. Fork the repository.
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ShotFlow.git
   cd ShotFlow
   ```
3. Set up the development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   pip install -r backend/requirements.txt
   ```
4. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
5. Initialize the database:
   ```bash
   PYTHONPATH=backend python backend/init_db.py
   ```

## Development Workflow

### Branching Strategy

- `main`: Stable release branch. All PRs merge into `main`.
- Feature branches: Create from `main` with a descriptive name:
  ```bash
  git checkout -b feat/my-feature
  ```

### Running Locally

Start the backend server:
```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Start the frontend dev server:
```bash
cd frontend
npm install
npm run dev
```

Run MCP server in stdio mode:
```bash
PYTHONPATH=backend python -m app.services.mcp_server
```

### Testing

Run the simulation test:
```bash
PYTHONPATH=backend python backend/tests/test_simulate_sync.py
```

## Pull Request Process

1. Ensure your code passes the existing tests.
2. Update documentation if you introduce new features or change existing behavior.
3. Keep PRs focused — one feature or fix per pull request.
4. Write a clear PR title and description explaining what and why.
5. All PRs require at least one maintainer review before merging.
6. Squash commits into logical units before merging.

## Coding Standards

### Python

- Target Python 3.12+.
- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Use type hints for function signatures.
- Prefer `pathlib` over `os.path`.
- Use `async`/`await` for I/O-bound operations.

### Frontend (TypeScript)

- Target TypeScript 5.x.
- Use functional components with hooks.
- Follow the existing project structure conventions.

### Commit Messages

Use conventional commit format:

```
<type>: <brief description>

<optional body>
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`.

Example:
```
feat: add Runway video generation provider

Implements Runway Gen-3 Alpha API integration with
retry logic and error handling.
```

## Reporting Issues

- Check existing issues before filing a duplicate.
- Use the issue template when available.
- Include reproduction steps, expected behavior, and actual behavior.
- Include relevant logs, screenshots, or error messages.
- Tag with appropriate labels (bug, enhancement, question).

---

Thank you for contributing. Every issue filed, comment written, and PR opened makes ShotFlow better for everyone.
