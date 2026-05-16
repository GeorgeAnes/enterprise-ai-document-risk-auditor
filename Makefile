PYTHON ?= python
NPM ?= npm.cmd

.PHONY: install-backend test-backend test-all install-frontend test-frontend build-frontend run-backend run-frontend

install-backend:
	$(PYTHON) -m pip install -r backend/requirements.txt

test-backend:
	$(PYTHON) -m pytest backend/tests

test-all:
	$(PYTHON) -m pytest

run-backend:
	$(PYTHON) -m uvicorn backend.app.main:app --reload --port 8010

install-frontend:
	cd frontend && $(NPM) install

test-frontend:
	cd frontend && $(NPM) test

build-frontend:
	cd frontend && $(NPM) run build

run-frontend:
	cd frontend && $(NPM) run dev
