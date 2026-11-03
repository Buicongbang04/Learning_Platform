---
title: Argo Workflow prepare → train → evaluate với parameter và artifact
level: intermediate
services: []
files:
  - path: starter/workflow.yaml
    note: Workflow eta-train, bước train và evaluate còn TODO
  - path: tests/test_workflow.py
    note: Không sửa
run:
  - bash setup/mlops/kind/up.sh
  - nice -n 15 uv run pytest tracks/mlops/modules/13-kubernetes-for-ml/exercises/intermediate/04-argo-training-workflow -q
---

## Mục tiêu

Viết pipeline training thành Argo Workflow: DAG ba bước, truyền dữ liệu và model giữa các pod bằng artifact, cấu hình bằng parameter, retry bước dễ lỗi; kiểm kết quả từ chính output của Workflow.

## Đề bài

Cluster có Argo Workflows; kho artifact mặc định là MinIO trong namespace `argo` (xem `setup/mlops/kind/README.md`), nên Workflow ở namespace nào cũng truyền artifact được mà không cần Secret. Image `eta-serve:dev` (lab ở `tracks/mlops/modules/13-kubernetes-for-ml/lab/service/`) có sẵn module `app.etaml` với `make_trips(seed, n)` (trả `x, y`), `train(x, y)` và `mae(model, x, y)`.

Hoàn thiện `starter/workflow.yaml` (Workflow tên **`eta-train`**, giữ `image: eta-serve:dev`). Luật mà test kiểm:

1. `spec.arguments.parameters` có `seed` và `rows`. Test đặt `seed=7`, `rows=4000`.
2. Template entrypoint là DAG đúng ba task `prepare`, `train`, `evaluate`; `train` phụ thuộc `prepare`; `evaluate` phụ thuộc cả `prepare` và `train`.
3. `prepare` sinh dữ liệu bằng `make_trips(seed, rows)`, 80% đầu là train, 20% cuối là test (`cut = int(rows * 0.8)`), xuất **artifact** `train` và `test`.
4. `train` nhận artifact `train`, huấn luyện bằng `app.etaml.train`, xuất artifact `model`; template `train` có `retryStrategy.limit` ≥ 1.
5. `evaluate` nhận artifact `model` và `test` (không train lại), tính `mae` và xuất **output parameter** `metrics` là JSON `{"mae": <số>, "n_test": <số dòng test>}`.

Test apply vào namespace tạm, chờ Workflow kết thúc (tối đa 300 giây), đòi `Succeeded`, đọc `status.nodes` để kiểm artifact vào/ra từng bước, rồi tự tính MAE kỳ vọng trên máy với cùng seed/rows và so với `metrics.mae` (sai số 1e-6).

## Tiêu chí đạt

- Workflow `Succeeded`; `prepare` xuất `train` và `test`; `evaluate` nhận `model` và `test`.
- `metrics.n_test == 800` và `metrics.mae` khớp MAE tính lại.
- Giải thích được khi nào truyền bằng parameter, khi nào bằng artifact.

## Gợi ý

### Gợi ý 1

Output của một task dùng trong task sau qua `{{tasks.<task>.outputs.artifacts.<tên>}}` (trong `arguments.artifacts[].from`); parameter của Workflow vào template qua `{{workflow.parameters.<tên>}}`.

### Gợi ý 2

Xem Workflow đang chạy: `kubectl --context kind-mlops -n <ns> get workflow eta-train -o yaml` (phần `status.nodes`), log một bước: `kubectl ... logs <pod> -c main`.
