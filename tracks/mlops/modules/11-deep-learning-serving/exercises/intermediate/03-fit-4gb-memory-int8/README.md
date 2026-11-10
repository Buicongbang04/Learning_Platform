---
title: Vừa GPU 4 GB - bộ nhớ theo batch size, FP16 và INT8
level: intermediate
services: []
files:
  - path: starter/memory_plan.py
    note: 6 hàm TODO (chạy trên CPU)
  - path: starter/gpu_memory.py
    note: 1 hàm TODO (chạy trong setup/gpu, test skip khi không có CUDA)
  - path: tests/test_memory_plan.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/intermediate/03-fit-4gb-memory-int8 -q
---

## Mục tiêu

Trả lời bằng số câu hỏi "model này chạy batch bao nhiêu thì vừa card 4 GB": ước lượng bộ nhớ từ graph ONNX, đo bộ nhớ đỉnh thật trên GPU theo batch size và kiểu số, và đánh giá INT8 bằng cả kích thước lẫn chất lượng mask.

## Đề bài

Model là model phân đoạn tí hon của module (input `pixel_values` `(N, 3, 64, 64)`, 3 lớp). Điền `starter/memory_plan.py` (chạy bằng CPU):

- `activation_bytes(onnx_path, batch_size, bytes_per_element=4)`: nạp graph, đặt trục 0 của mọi input và output bằng `batch_size`, xoá `graph.value_info`, chạy `onnx.shape_inference.infer_shapes(model, strict_mode=True)`, rồi cộng số phần tử của mọi tensor trong `graph.input`, `graph.value_info`, `graph.output` **trừ** tensor là initializer; nhân `bytes_per_element`. Đây là cận trên bảo thủ (coi như không tensor nào dùng lại bộ nhớ).
- `weight_bytes(onnx_path, bytes_per_element=4)`: tổng số phần tử của các initializer nhân `bytes_per_element`.
- `max_batch_size(onnx_path, budget_bytes, bytes_per_element=4, reserve_bytes=0)`: batch lớn nhất `b` sao cho `weight_bytes + activation_bytes(b) + reserve_bytes <= budget_bytes`; trả `0` nếu batch 1 cũng không vừa. Phải nhanh với ngân sách 4 GiB (đừng thử từng batch một).
- `quantize_int8(src, dst)`: `onnxruntime.quantization.quantize_dynamic(src, dst, weight_type=QuantType.QUInt8)`; trả `Path(dst)`.
- `mean_iou(pred, target, num_classes=3)`: trung bình IoU của các lớp có `union > 0`.
- `int8_report(fp32_path, int8_path, images, masks)`: dict `fp32_bytes`, `int8_bytes` (kích thước tệp), `fp32_miou`, `int8_miou` (chạy cả batch `images` bằng ONNX Runtime CPU, `argmax` theo trục lớp, so với `masks`).

**Ngưỡng chất lượng INT8 của bài**: tệp INT8 không quá 50% tệp FP32, và mIoU giảm **không quá 0.02** (tuyệt đối) so với FP32 trên 64 ảnh tổng hợp. Graph INT8 phải chứa op lượng tử hoá thật (`ConvInteger`, `DynamicQuantizeLinear`...).

`starter/gpu_memory.py` chạy trong môi trường `setup/gpu` (torch CUDA) qua `mlopskit.gpu_python`:

- `peak_memory_mib(model, batch_sizes, size=128, dtype=torch.float32, channels_last=False)`: đưa model lên CUDA với `dtype` (và `memory_format=torch.channels_last` nếu bật, input cũng vậy); với từng batch: `synchronize`, `empty_cache`, `reset_peak_memory_stats`, ghi `memory_allocated()` làm mốc, chạy một lần trong `torch.inference_mode()` với input ngẫu nhiên `(batch, 3, size, size)`, `synchronize`, trả `{batch: (max_memory_allocated() - mốc) / 2**20}`.

Test GPU (skip khi không có CUDA) đòi: FP32 tăng theo batch (batch 64 hơn 20 lần batch 1), FP16 không tốn hơn FP32, và FP16 + `channels_last` ở batch 64 dưới 60% FP32. Mọi test khác chạy bằng CPU.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/intermediate/03-fit-4gb-memory-int8 -q` pass (test GPU skip nếu không có CUDA).
- Có CUDA: in kết quả `peak_memory_mib` cho FP32, FP16, FP16 + `channels_last` và giải thích vì sao FP16 với layout mặc định gần như không giảm bộ nhớ đỉnh.
- Nói được vì sao `max_batch_size` tính từ graph chỉ là điểm khởi đầu, còn con số dùng cho production phải đo trên card thật với ngân sách chừa lại cho phân mảnh và CUDA context.

## Gợi ý

### Gợi ý 1

`value.type.tensor_type.shape.dim[0].dim_value = batch_size` ghi đè trục động. `int(np.prod([d.dim_value for d in value.type.tensor_type.shape.dim]))` cho số phần tử.

### Gợi ý 2

Bộ nhớ tăng đơn điệu theo batch, nên tìm `max_batch_size` bằng nhân đôi rồi chia đôi (binary search). Trên GPU, chỉ số đáng tin là `torch.cuda.max_memory_allocated`; `nvidia-smi` cho thấy cả bộ nhớ cache của allocator nên luôn cao hơn.
