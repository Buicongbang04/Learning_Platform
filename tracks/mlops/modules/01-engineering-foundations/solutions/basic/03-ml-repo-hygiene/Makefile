.DEFAULT_GOAL := help
PYTHON ?= uv run python
DATA ?= data/yellow_tripdata_2019-01.parquet
SEED ?= 0

.PHONY: help setup test lint train clean

help: ## Liệt kê các lệnh
	@grep -E '^[a-z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "%-8s %s\n", $$1, $$2}'

setup: ## Cài dependency đúng theo uv.lock
	uv sync --frozen

test: ## Chạy test
	uv run pytest -q

lint: ## Kiểm tra style
	uv run ruff check src tests
	uv run ruff format --check src tests

train: ## Train ETA mini
	mkdir -p models
	$(PYTHON) -m eta_mini --data $(DATA) --out models/model.joblib --seed $(SEED)

clean: ## Xoá model, cache; giữ nguyên data
	rm -rf models .pytest_cache .ruff_cache
	find . -path ./.venv -prune -o -name __pycache__ -type d -prune -exec rm -rf {} +
