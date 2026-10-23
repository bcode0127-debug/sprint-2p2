PY = PYTHONPATH=src .venv/bin/python

.PHONY: reproduce test lint

reproduce:
	$(PY) -m scripts.reproduce_row

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check
