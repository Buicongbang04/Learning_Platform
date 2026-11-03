---
title: Export model phân đoạn ra ONNX với batch động và kiểm sai số
level: basic
services: []
files:
  - path: starter/export_onnx.py
    note: 4 hàm TODO
  - path: tests/test_export.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/basic/01-onnx-export-parity -q
---

## Mục tiêu

Export một model PyTorch ra ONNX sao cho service dùng được với mọi batch size, và có một bước `verify` chặn artifact hỏng (opset cũ, batch bị cố định, output lệch PyTorch) trước khi nó tới production.

## Đề bài

Test tự sinh một model phân đoạn tí hon (vài lớp conv, 3 lớp: nền, thú cưng, viền; input `(N, 3, 64, 64)`, output logits `(N, 3, 64, 64)`). Hằng `INPUT_NAME="pixel_values"`, `OUTPUT_NAME="logits"`, `OPSET=17`, `SIZE=64` đã có. Điền `starter/export_onnx.py`:

- `export(model, path, size=SIZE)`: `torch.onnx.export` với `opset_version=OPSET`, `input_names=[INPUT_NAME]`, `output_names=[OUTPUT_NAME]`, trục 0 của **cả** input và output là động (`dynamic_axes`, tên trục `"batch"`), `dynamo=False` (exporter TorchScript, không cần `onnxscript`). Trả `Path` của tệp. Session ONNX Runtime phải chạy được batch 1, 3, 8.
- `pick_providers(available)`: nhận danh sách provider (như `ort.get_available_providers()`), trả `["CUDAExecutionProvider", "CPUExecutionProvider"]` nếu có CUDA, nếu không thì `["CPUExecutionProvider"]`. Bỏ mọi provider khác (TensorRT, Azure...). CPU luôn đứng cuối để làm đường fallback.
- `max_abs_diff(model, session, batch)`: chạy cùng `batch` (numpy float32) qua PyTorch (`eval`, `torch.no_grad`) và qua `session`, trả `float` sai khác tuyệt đối lớn nhất.
- `verify(model, path, batch_sizes=(1, 4), atol=1e-4, min_opset=OPSET)`: kiểm theo thứ tự, gặp lỗi thì `raise ValueError` với thông điệp **chứa** từ khoá:
  1. `onnx.checker.check_model` qua.
  2. Opset của domain mặc định (`""` hoặc `"ai.onnx"`) nhỏ hơn `min_opset`: thông điệp chứa `opset`.
  3. Trục 0 của input đầu tiên hoặc output đầu tiên không phải `dim_param` (bị cố định thành số): thông điệp chứa `batch`.
  4. Với mỗi `size` trong `batch_sizes`, batch `np.random.default_rng(size).random((size, 3, SIZE, SIZE), dtype=np.float32)` chạy trên session CPU; `max_abs_diff > atol` thì thông điệp chứa `atol`.

  Qua hết thì trả `{"opset": <int>, "max_abs_diff": <lớn nhất qua các batch>, "batch_sizes": [...]}`.

Bài có một test GPU: export bằng hàm của bạn, rồi chạy tệp ONNX bằng `onnxruntime-gpu` trong môi trường `setup/gpu` (qua `mlopskit.gpu_python`, sau `ort.preload_dlls()`), đòi provider đầu tiên thật sự là CUDA (không lặng lẽ fallback) và output khớp CPU trong `1e-3`. Máy không có CUDA thì test này skip; mọi test khác chạy bằng CPU.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/basic/01-onnx-export-parity -q` pass (test GPU được skip nếu không có CUDA).
- Giải thích được vì sao `verify` chạy ít nhất hai batch size khác nhau chứ không chỉ batch dùng lúc export.
- Nói được hậu quả khi `CUDAExecutionProvider` thiếu thư viện: ONNX Runtime làm gì, và service biết bằng cách nào.

## Gợi ý

### Gợi ý 1

`dynamic_axes={INPUT_NAME: {0: "batch"}, OUTPUT_NAME: {0: "batch"}}`. Đọc lại bằng `onnx.load(path).graph.input[0].type.tensor_type.shape.dim[0]`: trục động có `dim_param`, trục cố định có `dim_value`.

### Gợi ý 2

Opset nằm ở `proto.opset_import` (một danh sách, mỗi phần tử có `domain` và `version`). `session.run([OUTPUT_NAME], {INPUT_NAME: batch})[0]` trả numpy.
