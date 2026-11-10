# Benchmark: SegFormer-b0 Oxford Pets

## Môi trường

| Mục | Giá trị |
| --- | --- |
| CPU / số luồng ONNX Runtime | |
| GPU / driver / CUDA | |
| onnxruntime / onnxruntime-gpu | |
| Kích thước input | |
| Model (MLflow run, sha256 tệp ONNX) | |

## Chất lượng (tập val)

| Biến thể | mIoU | IoU pet | IoU border | Kích thước tệp |
| --- | --- | --- | --- | --- |
| PyTorch FP32 | | | | |
| ONNX FP32 | | | | |
| ONNX INT8 (CPU) | | | | |
| ONNX FP16 (CUDA) | | | | |

## Model đơn lẻ (harness, warmup loại)

| Provider | Batch | p50 ms | p95 ms | ảnh/giây | Bộ nhớ đỉnh |
| --- | --- | --- | --- | --- | --- |
| CPU | 1 | | | | |

## Qua HTTP (service, dynamic batching)

| Provider | Đồng thời | max batch / max wait | p50 ms | p95 ms | req/giây | Lỗi |
| --- | --- | --- | --- | --- | --- | --- |

## Kết luận

- Cấu hình chọn cho CPU:
- Cấu hình chọn cho GPU 4 GB:
- Điều bất ngờ nhất khi đo:
