SHELL := /bin/sh

.PHONY: setup dev test uninstall clean

setup:
	uv tool install --editable --reinstall ".[experimental]"

dev:
	uv sync

test:
	uv run pytest

uninstall:
	-uv tool uninstall moneno

clean:
	rm -rf .venv dist build .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +
