# Repository-owned implementation of the make-v2 execution phases.
#
# CI parity:
#   setup     -> the "Set up Python" and install steps of l9-lint-test.yml
#   validate  -> byte-compile and import the package
#   check     -> ruff check, ruff format --check, mypy (advisory, as in CI)
#   test-fast -> the bounded pull-request selection
#   test      -> the full pytest suite
#
# Core runs each phase as its own make process, so every recipe resolves the
# environment it needs rather than relying on state a previous phase exported.

PYTHON ?= python3
VENV := $(CURDIR)/.venv
BIN := $(VENV)/bin
PY := $(BIN)/python

.PHONY: repo-setup repo-validate repo-check repo-test-fast repo-test

repo-setup: ## Create .venv and install the project with dev extras
	@test -x "$(PY)" || $(PYTHON) -m venv "$(VENV)"
	@"$(BIN)/pip" install --quiet --upgrade pip
	@"$(BIN)/pip" install --quiet -e ".[dev]"

repo-validate: ## Byte-compile and import the package
	@$(PY) -m compileall -q src
	@$(PY) -c "import l9_debt_resolver"

repo-check: ## Ruff lint, format check, advisory strict mypy
	@"$(BIN)/ruff" check .
	@"$(BIN)/ruff" format --check .
	-@"$(BIN)/mypy" src --show-error-codes --pretty --install-types --non-interactive

repo-test-fast: ## Bounded pull-request selection
	@$(PY) -m pytest tests/contracts tests/classification tests/feedback tests/resilience -q

repo-test: ## Full pytest suite
	@$(PY) -m pytest tests -q
