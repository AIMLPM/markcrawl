.PHONY: test lint preflight smoke

PYTHON ?= .venv/bin/python

test:
	$(PYTHON) -m pytest tests/ -q

lint:
	$(PYTHON) -m ruff check markcrawl/ tests/

preflight: lint test

smoke:
	$(PYTHON) -c "from markcrawl import crawl; print('import OK')"
