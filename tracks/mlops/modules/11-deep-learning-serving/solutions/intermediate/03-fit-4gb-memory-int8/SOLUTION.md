# Lời giải: vừa GPU 4 GB

## Cách làm

- `activation_bytes`: cố định trục batch, xoá `value_info` cũ (có trục `batch` dạng chữ), chạy shape inference rồi cộng kích thước mọi tensor không phải trọng số. Với model tí hon: khoảng 2.2 MB mỗi ảnh 64×64, tuyến tính theo batch.
- `max_batch_size`: nhân đôi tới khi vượt ngân sách, rồi chia đôi. Mỗi bước là một lần shape inference, vài chục lần là đủ cho 4 GiB.
- `quantize_int8`: `quantize_dynamic` lượng tử hoá trọng số Conv/MatMul sang 8 bit; activation được lượng tử hoá **lúc chạy** (`DynamicQuantizeLinear`) nên không cần dữ liệu hiệu chỉnh.
- `peak_memory_mib`: đo bằng `max_memory_allocated` trừ mốc trước khi chạy, sau `reset_peak_memory_stats`. `synchronize` trước và sau vì kernel CUDA chạy bất đồng bộ.

## Kết quả tham khảo

INT8 (CPU): tệp 78 KB xuống 28 KB (36%), mIoU 0.929 sang 0.930 (lệch trong nhiễu). Model lớn hơn thường giảm 0.5–2 điểm mIoU với dynamic quantization; static quantization (có dữ liệu hiệu chỉnh) giữ chất lượng tốt hơn với Conv vì activation có thang cố định, và nhanh hơn vì không tính min/max lúc chạy.

RTX 3050 Laptop 4 GB, model tí hon, ảnh 128×128, MiB tăng thêm:

| Batch | FP32 | FP16 | FP16 + channels_last |
| --- | --- | --- | --- |
| 1 | 3.8 | 3.4 | 1.8 |
| 8 | 29.4 | 26.8 | 14.7 |
| 32 | 116.6 | 108.0 | 58.3 |
| 64 | 230.6 | 214.0 | 115.0 |

FP16 với layout NCHW mặc định gần như không giảm bộ nhớ đỉnh: Tensor Core làm việc với NHWC nên cuDNN chuyển layout, cấp thêm buffer tạm. Đổi sang `channels_last` thì giảm gần nửa như lý thuyết. Bài học: **đo, đừng nhân 0.5**.

## Từ số đo tới cấu hình

1. Ngân sách: 4 GB card trừ CUDA context (~300–500 MB), trừ phần cho process khác (màn hình laptop), trừ biên cho phân mảnh (10–20%).
2. Đo `peak_memory_mib` ở kích thước input production, tìm batch lớn nhất vừa ngân sách.
3. Ước lượng từ graph (`activation_bytes`) dùng để sàng lọc trước khi có card: nó bỏ qua workspace của cuDNN, buffer chuyển layout, và việc runtime dùng lại bộ nhớ, nên lệch cả hai chiều.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Test | CPU pass; GPU pass hoặc skip |
| FP16 | Giải thích được bảng trên (layout, Tensor Core) |
| INT8 | Nêu được khi nào dùng dynamic, khi nào static, và ngưỡng chất lượng bạn chấp nhận |
| Ngân sách | Liệt kê được các khoản phải trừ khỏi 4 GB trước khi chia cho batch |
