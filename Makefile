.PHONY: install run debug clean lint lint-strict

install:
	pip install arcade pydantic flake8 mypy

run:
	python3 bin/main.py

debug:
	python3 -m pdb bin/main.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache

lint:
	flake8 bin
	mypy bin --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 bin
	mypy bin --strict