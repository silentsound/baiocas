PYTHON ?= python3
VIRTUALENV ?= virtualenv -p $(PYTHON)
VENV = venv
VENVBIN = $(VENV)/bin

.PHONY: default
default: all

venv:
	$(VIRTUALENV) $(VENV)
	$(VENVBIN)/pip install -r ./requirements.txt

.PHONY: lint
lint: venv
	# stop the build if there are Python syntax errors or undefined names
	$(VENVBIN)/flake8 . --exclude $(VENV) --count --select=E9,F63,F7,F82 --show-source --statistics
	# exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
	$(VENVBIN)/flake8 . --exclude $(VENV) --count --exit-zero --max-line-length=127 --statistics

.PHONY: install-hooks
install-hooks: venv
	$(VENVBIN)/pre-commmit install

.PHONY: check
check: venv
	$(VENVBIN)/pre-commit run --all-files

.PHONY: test
test:
	$(VENVBIN)/pytest

.PHONY: all
all: check lint test
