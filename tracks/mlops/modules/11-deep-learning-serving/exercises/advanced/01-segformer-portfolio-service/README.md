---
title: Portfolio - service SegFormer cho Oxford Pets có benchmark CPU/GPU
level: advanced
services: []
files:
  - path: starter/finetune_segformer.py
    note: Script chuẩn bị (chạy một lần), không sửa
  - path: starter/BENCHMARK.md
    note: Mẫu báo cáo benchmark
run:
  - uv run python data/download_dataset.py oxford-pets
  - uv run python data/download_dataset.py oxford-pets-trimaps
  - uv run --project setup/gpu python tracks/mlops/modules/11-deep-learning-serving/exercises/advanced/01-segformer-portfolio-service/starter/finetune_segformer.py --device cuda
  - uv run python tracks/mlops/modules/11-deep-learning-serving/exercises/advanced/01-segformer-portfolio-service/starter/finetune_segformer.py --log-only
---

## Mục tiêu

Ghép mọi phần của module thành một dự án đưa vào portfolio: service phân đoạn ảnh thú cưng dùng SegFormer-b0 thật, chạy được trên CPU và GPU 4 GB, có số đo chất lượng và hiệu năng mà người phỏng vấn kiểm lại được.

## Đề bài

**Chuẩn bị (một lần, xem mục 0 của lý thuyết):** `starter/finetune_segformer.py` fine-tune `nvidia/mit-b0` (checkpoint công khai) trên 800 ảnh train, đánh giá trên 200 ảnh của split test, lưu thư mục Hugging Face, tệp ONNX (opset 17, batch động, input 256×256, output logits ở 1/4 độ phân giải) và `meta.json` vào `data/raw_models/segformer-b0-pets/`, rồi `--log-only` ghi tất cả vào MLflow local (`data/raw_models/mlflow.db`). Không có GPU thì chạy `--device cpu --train 300 --size 192`; chất lượng thấp hơn nhưng đủ cho bài serving.

**Dự án** (thư mục tuỳ chọn, ví dụ repo riêng), tối thiểu gồm:

1. **Nạp model từ MLflow** theo run id hoặc alias, kiểm `verify` kiểu bài Basic 01 (opset, batch động, so output PyTorch và ONNX Runtime trên vài ảnh val, ngưỡng ghi rõ) trước khi nhận traffic.
2. **Service FastAPI** `POST /segment` trả mask PNG đúng kích thước ảnh gốc (logits 1/4 phải được phóng về), header `X-Model-Version` là run id; kiểm định dạng và kích thước ảnh theo hồ sơ dữ liệu của bài Basic 03; `/healthz` và `/readyz` phản ánh đúng trạng thái model và worker.
3. **ONNX Runtime CPU và CUDA**: chọn provider có fallback, log `get_providers()` lúc khởi động, cấu hình qua biến môi trường.
4. **Dynamic batching** có cả trần kích thước lẫn thời gian chờ; trần batch suy ra từ số đo bộ nhớ trên card của bạn, ghi rõ cách đo.
5. **Biến thể INT8** cho CPU, có mIoU trên tập val và quyết định có dùng hay không.
6. **Benchmark** điền `BENCHMARK.md`: model đơn lẻ theo batch (harness của bài Basic 02) và qua HTTP với tải đồng thời (k6 hoặc script), cả CPU và GPU (GPU tuỳ chọn nếu không có card). Mọi con số kèm cấu hình máy và cách tái lập.
7. **Image Docker CPU** (máy học không có NVIDIA runtime cho Docker, nên image GPU chỉ là tuỳ chọn), non-root, healthcheck, không nhúng model vào image hoặc giải thích vì sao nhúng.
8. **README dự án**: kiến trúc (sơ đồ), cách chạy, kết quả, giới hạn đã biết.

## Tiêu chí đạt

- Chấm theo rubric trong `SOLUTION.md` (tự chấm hoặc nhờ người review); không có test tự động.
- Người khác clone dự án, chạy theo README, tái lập được số chất lượng (sai lệch nhỏ) và thấy service trả mask hợp lý trên ảnh thú cưng thật.
- `BENCHMARK.md` có đủ bảng, mọi ô có số hoặc ghi rõ "không đo vì ...".

## Gợi ý

### Gợi ý 1

Làm theo thứ tự rủi ro: export và `verify` trên model thật trước (SegFormer có attention và resize, dễ lệch hơn model conv), rồi service một ảnh, rồi batching, rồi benchmark. Đừng tối ưu trước khi có số đo đầu tiên.

### Gợi ý 2

Trên card 4 GB, đo bộ nhớ đỉnh của ONNX Runtime CUDA bằng `nvidia-smi --query-gpu=memory.used --format=csv -lms 100` trong lúc chạy từng batch size, hoặc đặt `gpu_mem_limit` của CUDA provider để tái hiện card nhỏ hơn. Nhớ trừ phần màn hình laptop đang dùng.
