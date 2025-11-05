# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

VENV=.venv
ACTIVATE = $(VENV)/bin/activate

bootstrap:
	uv sync --extra dev

lint:
	uv run ruff check
	uv run mypy cachecontrol

format:
	uv run codespell
	uv run ruff check --fix
	uv run ruff format

doc: $(VENV)/bin/sphinx-build
	. $(ACTIVATE);
	cd docs && make html

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

test-all:
	uv run tox

test:
	uv run py.test

coverage:
	uv run py.test --cov cachecontrol

dist: clean
	uv run python -m build
	ls -l dist
