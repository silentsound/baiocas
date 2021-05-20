PYTHON ?= python3
VIRTUAL_ENV_CMD ?= virtualenv -p $(PYTHON)
VIRTUAL_ENV ?= venv
VENVBIN = $(VIRTUAL_ENV)/bin
DEVBUILD ?= dev

.PHONY: default
default: all

$(VIRTUAL_ENV):
	$(VIRTUAL_ENV_CMD) $(VIRTUAL_ENV)
	$(VENVBIN)/pip install -r ./requirements.txt

.PHONY: lint
lint: $(VIRTUAL_ENV)
	# stop the build if there are Python syntax errors or undefined names
	$(VENVBIN)/flake8 . --exclude venv --count --select=E9,F63,F7,F82 --show-source --statistics
	# exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
	$(VENVBIN)/flake8 . --exclude venv --count --exit-zero --max-line-length=127 --statistics

.PHONY: install-hooks
install-hooks: $(VIRTUAL_ENV)
	$(VENVBIN)/pre-commmit install

.PHONY: check
check: $(VIRTUAL_ENV)
	$(VENVBIN)/pre-commit run --all-files

.PHONY: test
test: $(VIRTUAL_ENV)
	$(VENVBIN)/pytest

.PHONY: all
all: check lint test

.PHONY: release
release: $(VIRTUAL_ENV)
	$(VENVBIN)/pip install setuptools wheel twine
	$(VENVBIN)/python setup.py $(DEVBUILD) sdist bdist_wheel
	$(VENVBIN)/twine upload dist/*
