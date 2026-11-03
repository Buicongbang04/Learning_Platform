REPO := $(abspath ../../../../..)
PY := cd $(CURDIR) && PYTHONPATH=src uv run --project $(REPO) python
PORT ?= 28080

.PHONY: test train register serve images repro

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
