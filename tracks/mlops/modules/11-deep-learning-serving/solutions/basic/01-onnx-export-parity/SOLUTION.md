# Lời giải: export ONNX với batch động và kiểm sai số

## Cách làm

- `export` gọi `torch.onnx.export(..., opset_version=17, dynamic_axes={...: {0: "batch"}}, dynamo=False)`. Dummy input có batch 2 (không phải 1) để exporter không "hằng hoá" nhánh nào phụ thuộc batch 1. Không có `dynamic_axes`, trục batch bị ghi thành `dim_value: 2` và session từ chối batch khác.
- `pick_providers` chỉ giữ CUDA và CPU, CPU cuối cùng. ONNX Runtime chạy node trên provider đầu tiên hỗ trợ nó; node nào CUDA không có kernel thì rơi về CPU. Nếu CUDA EP không nạp được (thiếu cuDNN, sai phiên bản CUDA) ONNX Runtime **chỉ cảnh báo** và chạy hết trên CPU. Vì vậy test GPU kiểm `session.get_providers()[0]` chứ không tin danh sách đã yêu cầu. Service thật nên log `get_providers()` lúc khởi động và báo lỗi (hoặc metric) nếu nó khác cấu hình.
- `max_abs_diff` chạy cùng batch hai phía và so `np.abs(a - b).max()`; kiểm thêm shape để lỗi shape không thành lỗi broadcast khó hiểu.
- `verify` theo thứ tự rẻ tới đắt: checker, opset, trục batch (đọc graph, không chạy), rồi mới chạy suy luận trên nhiều batch size.

## Vì sao từng kiểm tra

| Kiểm tra | Bắt được |
| --- | --- |
| `check_model` | graph hỏng, kiểu sai |
| opset tối thiểu | export bằng opset cũ thiếu op (vd. `Resize` đời đầu cho kết quả nội suy khác) hoặc runtime production không hỗ trợ |
| trục batch là `dim_param` | export quên `dynamic_axes`: chạy được với batch lúc export, gãy với batch khác ngay khi bật dynamic batching |
| so output nhiều batch size | lệch số học (op được thay bằng xấp xỉ), trọng số không khớp (export nhầm checkpoint), lỗi chỉ hiện ở batch khác 1 |

`atol=1e-4` cho FP32 trên CPU là thoáng mà vẫn bắt được lệch thật: model tí hon lệch cỡ `1e-6`. Với FP16 hoặc INT8 phải đổi sang so trên **nhiệm vụ** (mIoU của mask) thay vì logits, xem bài quantization.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Test | Mọi test CPU pass; test GPU pass trên máy có CUDA hoặc skip |
| Hai batch size | Giải thích được rằng lỗi trục batch chỉ lộ ra với batch khác batch lúc export |
| Fallback | Nói được ONNX Runtime chỉ cảnh báo khi CUDA EP không nạp được, và kiểm bằng `get_providers()` |
