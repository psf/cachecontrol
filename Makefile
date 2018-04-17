VENV=.venv
VENV_CMD=python3 -m venv
ACTIVATE = $(VENV)/bin/activate
CHEESE=https://pypi.python.org/pypi
BUMPTYPE=patch


$(VENV)/bin/pip:
	$(VENV_CMD) $(VENV)

bootstrap: $(VENV)/bin/pip
	$(VENV)/bin/pip install -r dev_requirements.txt

format:
	$(VENV)/bin/black .

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

release: dist
	$(VENV)/bin/twine upload dist/CacheControl-*.tar.gz

dist: clean
	python setup.py sdist
	ls -l dist

bump:
	$(VENV)/bin/bumpversion $(BUMPTYPE)
	git push && git push --tags
