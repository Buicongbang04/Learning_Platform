# Hướng làm và rubric: service SegFormer portfolio

## Hướng làm

1. **Chuẩn bị**: chạy script fine-tune một lần. Trên RTX 3050 Laptop 4 GB cấu hình mặc định (800 ảnh 256 px, 4 epoch, AMP FP16) mất khoảng 1 phút (kể cả đọc dữ liệu), bộ nhớ GPU đỉnh khoảng 635 MiB; mIoU val khoảng 0.78 (nền 0.92, thú cưng 0.87, viền 0.54: viền là lớp khó nhất). Trên CPU với `--train 300 --size 192` mất lâu hơn và thấp hơn vài điểm; đủ cho bài serving.
2. **Nạp từ MLflow**: `mlflow.artifacts.download_artifacts(run_id=..., artifact_path="model")`, đọc `meta.json` để lấy `size`, `mean`, `std` (tiền xử lý đi theo model, không hard-code trong service). Chạy `verify` trên vài ảnh val: FP32 CPU thường lệch cỡ `1e-5`; FP16 CUDA lệch logits cỡ `1e-2`, nên với FP16 so trên **mask** (tỉ lệ pixel trùng ≥ 99.5% hoặc mIoU giảm ≤ 0.005).
3. **Service**: tách ba lớp: decode và kiểm ảnh, batcher, runtime. Logits ở 64×64 với input 256: phóng logits bằng bilinear lên kích thước input rồi argmax (đẹp hơn) hoặc argmax rồi phóng mask nearest (rẻ hơn); ghi rõ chọn gì.
4. **Provider**: `pick_providers` của bài Basic 01, cộng `ORT_PROVIDER=cpu|cuda|auto`. Lúc khởi động log `get_providers()`; nếu cấu hình `cuda` mà provider đầu không phải CUDA thì `/readyz` đỏ thay vì âm thầm chạy CPU.
5. **Batching**: batcher của bài Intermediate 02. Trần batch: đo bộ nhớ theo batch như bài Intermediate 03 (với ONNX Runtime dùng `nvidia-smi` hoặc `gpu_mem_limit`), lấy batch lớn nhất vừa 80% phần trống. `max_wait_ms` khoảng 5–10 ms. Hàng đợi có giới hạn, đầy thì 503.
6. **INT8**: `quantize_dynamic` cho CPU; SegFormer có nhiều MatMul nên dynamic quantization có tác dụng hơn với model conv. So mIoU val; nếu giảm quá ngưỡng bạn đặt (vd. 0.01) thì thử static quantization (QDQ, hiệu chỉnh trên 100 ảnh train) hoặc loại bỏ.
7. **Benchmark**: model đơn lẻ (harness, batch 1/4/8/16) trên CPU và CUDA; HTTP với 1, 8, 32 client đồng thời. Báo p50, p95, throughput, lỗi, cấu hình. Chạy mỗi cấu hình ít nhất hai lần và báo cả hai nếu lệch nhiều.
8. **Docker**: image CPU từ `python:3.12-slim`, `uv sync --frozen`, user không root, `HEALTHCHECK` gọi `/healthz`; model mount từ volume hoặc tải từ MLflow lúc khởi động (image không đổi khi model đổi).

## Những quyết định cần cân nhắc

| Quyết định | Phương án | Nên cân nhắc |
| --- | --- | --- |
| Độ phân giải input | 256 / 384 / 512 | Chất lượng viền và bộ nhớ tăng gần bình phương cạnh |
| Phóng logits hay phóng mask | bilinear logits / nearest mask | Biên mịn hơn so với bộ nhớ gấp số lớp |
| Precision GPU | FP32 / FP16 | FP16 nhanh hơn trên Tensor Core, cần kiểm lệch trên mask |
| Runtime | ONNX Runtime / TensorRT EP / Triton | Bài này đủ với ORT; TensorRT nhanh hơn nhưng build engine theo GPU và shape |
| Nơi chứa model | trong image / volume / tải từ MLflow | Tái lập, thời gian khởi động, rollback |

## Rubric

| Tiêu chí | 0 điểm | 1 điểm | 2 điểm |
| --- | --- | --- | --- |
| Model và verify | Không kiểm sai số | Kiểm FP32 | Kiểm FP32 và FP16/INT8 với ngưỡng ghi rõ, chặn khởi động khi fail |
| Service | Chỉ chạy được một ảnh | Đủ hợp đồng (PNG, version, kiểm đầu vào) | Thêm `/readyz` phản ánh model, provider, worker |
| CPU/GPU | Chỉ một đường | Có fallback | Fallback được log và kiểm, cấu hình qua env |
| Batching và bộ nhớ | Không batching | Có batching | Trần batch từ số đo bộ nhớ, hàng đợi có giới hạn |
| Benchmark | Không có | Có số nhưng thiếu cấu hình | Đủ bảng, warmup loại, p50/p95, tái lập được |
| INT8 | Không có | Có số kích thước | Có mIoU val và quyết định dùng hay không |
| Đóng gói | Không có | Dockerfile chạy được | Non-root, healthcheck, model ngoài image hoặc có lý do |
| Trình bày | README sơ sài | Có cách chạy | Có sơ đồ, kết quả, giới hạn đã biết |

Từ 12/16 điểm trở lên là dự án đưa được vào CV. Dưới 8 điểm: ưu tiên verify, benchmark tái lập được và README.
