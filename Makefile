# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

VENV=.venv
VENV_CMD=python3 -m venv
ACTIVATE = $(VENV)/bin/activate

$(VENV)/bin/pip:
	$(VENV_CMD) $(VENV)

bootstrap: $(VENV)/bin/pip
	$(VENV)/bin/pip install -e .[dev]

format:
	$(VENV)/bin/codespell
	$(VENV)/bin/ruff check --fix
	$(VENV)/bin/ruff format

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
	$(VENV)/bin/tox

test:
	$(VENV)/bin/py.test

coverage:
	$(VENV)/bin/py.test --cov cachecontrol

dist: clean
	$(VENV)/bin/python -m build
	ls -l dist
