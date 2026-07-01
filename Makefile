UV := uv

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Setup"
	@echo "  setup         Install deps (dev group) into .venv via uv"
	@echo ""
	@echo "Quality gate"
	@echo "  check         lint + format-check + typecheck + test"
	@echo "  lint          ruff check"
	@echo "  format        ruff format (writes)"
	@echo "  format-check  ruff format --check"
	@echo "  typecheck     ty check"
	@echo "  test          pytest"
	@echo ""
	@echo "Run"
	@echo "  render FILE=graph.gnode OUT=out.png   Render a .gnode to PNG"

.PHONY: setup
setup:
	$(UV) sync

.PHONY: check
check: lint format-check typecheck test

.PHONY: lint
lint:
	$(UV) run ruff check .

.PHONY: format
format:
	$(UV) run ruff format .

.PHONY: format-check
format-check:
	$(UV) run ruff format --check .

.PHONY: typecheck
typecheck:
	$(UV) run ty check src tests

.PHONY: test
test:
	$(UV) run pytest

.PHONY: render
render:
	$(UV) run gnode render $(FILE) -o $(OUT)
