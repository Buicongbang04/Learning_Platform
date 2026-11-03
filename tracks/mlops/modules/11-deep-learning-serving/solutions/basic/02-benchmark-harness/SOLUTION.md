# Lời giải: benchmark harness

## Cách làm

`benchmark` tạo batch một lần, chạy `warmup` lần không đo, rồi đo `iters` lần riêng lẻ bằng `time.perf_counter()`. `summarize` lấy `np.percentile` cho p50/p95 và tính throughput từ **tổng** thời gian đo.

## Vì sao

- **Warmup**: lần chạy đầu của ONNX Runtime/PyTorch tốn thêm thời gian cấp phát arena bộ nhớ, chọn thuật toán conv (cuDNN autotune), nạp kernel CUDA, tạo cache. Đưa chúng vào số đo làm p95/p99 xấu đi giả tạo và làm kết quả phụ thuộc số vòng lặp.
- **Tạo dữ liệu ngoài vòng đo**: đo cả việc sinh ngẫu nhiên, decode ảnh hay copy là đo thứ khác model. Muốn đo end-to-end (decode + resize + model) thì làm benchmark riêng và đặt tên rõ.
- **Phân vị, không trung bình**: phân phối latency lệch phải; trung bình bị kéo bởi vài lần GC hay context switch, còn SLO viết theo p95/p99.
- **Throughput từ tổng thời gian**: `batch_size / p50` đẹp hơn thực tế vì bỏ đuôi chậm.
- **Theo batch size**: latency một request tăng theo batch, throughput tăng tới khi phần cứng bão hoà. Điểm "đầu gối" của đường cong là nơi chọn `max_batch_size` cho dynamic batching.

## Những bẫy khác khi đo DL

- GPU chạy bất đồng bộ: với PyTorch phải `torch.cuda.synchronize()` trước khi dừng đồng hồ; ONNX Runtime `run()` trả về khi output đã copy về host nên đã đồng bộ.
- Số luồng: đặt `intra_op_num_threads` cố định khi so sánh; máy đang tải nặng thì chạy lại và báo cả độ lệch.
- Kích thước input: model fully-convolutional chạy nhanh hơn nhiều với ảnh nhỏ; benchmark phải dùng đúng kích thước production.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Test | Pass |
| Đọc đường cong | Chỉ ra được batch size mà throughput gần bão hoà trên máy mình |
| Đồng bộ GPU | Giải thích được vì sao đo PyTorch CUDA không `synchronize` cho số quá đẹp |
