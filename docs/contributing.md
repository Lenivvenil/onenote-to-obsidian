# Contributing

Thank you for your interest in contributing!

## Getting Started

```bash
git clone https://github.com/Lenivvenil/onenote-to-obsidian.git
cd onenote-to-obsidian
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=onenote_to_obsidian --cov-report=term-missing

# Run a specific test file
pytest tests/test_exporter.py -v
```

All changes **must** include tests. Target coverage: >80%.

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check formatting
ruff format --check onenote_to_obsidian/

# Auto-format
ruff format onenote_to_obsidian/

# Lint
ruff check onenote_to_obsidian/

# Auto-fix lint issues
ruff check --fix onenote_to_obsidian/
```

## Type Hints

All public functions and methods should have type annotations.

## Submitting a Pull Request

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes with tests
3. Ensure all checks pass: `pytest && ruff check onenote_to_obsidian/ && ruff format --check onenote_to_obsidian/`
4. Push and open a PR against `main`
5. Link to the relevant GitHub Issue

## Reporting Bugs

Open an [issue](https://github.com/Lenivvenil/onenote-to-obsidian/issues) with:

- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS
- Relevant logs (`--verbose` flag)
