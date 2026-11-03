REPO := $(abspath ../../../../..)
PY := cd $(CURDIR) && PYTHONPATH=src uv run --project $(REPO) python
PORT ?= 28080

.PHONY: test train register serve images repro replay-data replay experiments act-ci monitoring

test:
	cd $(REPO) && SOLUTION=1 uv run pytest tracks/mlops/capstone/project/tests -q -rs

train:
	$(PY) -m eta.cli train --config params.yaml --model-out models/model.joblib --metrics-out metrics.json

register:
	$(PY) -m eta.cli train --config params.yaml --register

serve:
	cd $(CURDIR) && ETA_MODEL_PATH=models/model.joblib PYTHONPATH=src uv run --project $(REPO) uvicorn eta.serve:app --port $(PORT)

images:
	docker build -f Dockerfile.train --build-arg GIT_COMMIT=$$(git rev-parse HEAD) -t eta-train:dev .
	docker build -f Dockerfile.serve -t eta-api:dev .

repro:
	cd $(CURDIR) && uv run --project $(REPO) dvc repro

replay-data:
	mkdir -p data/replay
	for f in $(REPO)/data/raw/nyc-tlc/yellow_tripdata_2019-*.parquet $(REPO)/data/raw/nyc-tlc-2020/yellow_tripdata_2020-*.parquet; do \
		ln -sf "$$f" data/replay/; \
	done

replay: replay-data
	cd $(CURDIR) && PYTHONPATH=src uv run --project $(REPO) python -m eta.cli replay --config params.replay.yaml --start 2019-07 --end 2020-06 --out reports/replay

experiments:
	$(PY) -m eta.cli experiment late-slice --config params.replay.yaml --month 2020-03 --as-of 2020-04
	$(PY) -m eta.cli experiment retrain --config params.replay.yaml --train-month 2019-11 --month 2019-12 --as-of 2020-01
	$(PY) -m eta.cli experiment retrain --config params.replay.yaml --train-month 2020-03 --month 2020-04,2020-05 --as-of 2020-06

act-ci:
	cd $(CURDIR) && act push -W .github/workflows/ci.yml -P ubuntu-latest=mlops-act-runner:1 --pull=false --bind

monitoring:
	cd $(CURDIR) && docker compose --profile monitoring up -d --wait
