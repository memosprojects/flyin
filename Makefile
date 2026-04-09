.PHONY: install run debug clean lint lint-strict

PYTHON = python3
VENV = .venv
BIN = $(VENV)/bin
FLAKE8 = $(BIN)/flake8
MYPY = $(BIN)/mypy
PIP = $(BIN)/python -m pip

install:
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools
	$(PIP) install -r requirements.txt

run: install
	$(BIN)/python -m bin.main

debug: install
	$(BIN)/python -m pdb -c continue -m bin.main

clean:
	find . -type d -name "__pycache__" -not -path "./$(VENV)/*" -exec rm -rf {} +
	rm -rf .mypy_cache

lint: install
	$(FLAKE8) . --exclude=$(VENV)
	$(MYPY) . --exclude '(^|/).venv/' --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: install
	$(FLAKE8) . --exclude=$(VENV)
	$(MYPY) . --exclude '(^|/).venv/' --strict