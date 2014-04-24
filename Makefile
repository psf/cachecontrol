VENV   = venv
VENV_BIN = $(VENV)/bin
ACTIVATE = $(VENV_BIN)/activate

virtualenv: $(VENV)
	virtualenv $(VENV)

bootstrap: $(VENV_BIN)/python $(VENV_BIN)/sphinx-build
	$(VENV_BIN)/pip install -r dev_requirements.txt

docs: $(VENV_BIN)/sphinx-build
	. $(ACTIVATE);
	cd docs && make html

release_patch:
	. $(ACTIVATE);
	bumpversion patch
	git push origin master
	git push --tags origin master
	python setup.py sdist upload

release_minor:
	. $(ACTIVATE);
	bumpversion minor
	git push origin master
	git push --tags origin master
	python setup.py sdist upload

release_major:
	. $(ACTIVATE);
	bumpversion major
	git push origin master
	git push --tags origin master
	python setup.py sdist upload
