# Hướng làm: benchmark sinh ảnh với diffusers

Bài không có code lời giải: lưới cấu hình, prompt và khuyến nghị là của bạn. Dưới đây là các quyết định cần cân nhắc,
kết quả của một bản tham chiếu để bạn so, và rubric chấm.

## Ba hàm được test

- `clip_score`: chuẩn hoá từng hàng rồi lấy tích vô hướng theo hàng, nhân 100, chặn dưới ở 0. Chuẩn hoá bên trong hàm vì
  `get_image_features` của `transformers` trả vector **chưa** chuẩn hoá; quên bước này thì "điểm" tỉ lệ với độ dài vector.
- `time_call`: khởi động không tính giờ, rồi mỗi lần đo `sync(); t0; fn(); sync(); t1`. Thiếu `sync` trước khi dừng đồng hồ
  thì trên GPU bạn chỉ đo thời gian **xếp lệnh** vào hàng đợi CUDA. Trả trung vị để một lần bị máy khác chen không kéo lệch.
- `pareto_front`: một dòng bị loại khi có dòng khác không tệ hơn ở cả hai trục và tốt hơn hẳn ở ít nhất một trục; hai dòng
  trùng hệt không loại nhau.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Model | `stabilityai/sd-turbo`, bản fp16 | vừa GPU 4GB (đỉnh 3.0 GiB), 1 tới 4 bước |
| Lưới | bước 1, 2, 4 với guidance 0; bước 1 và 4 với `guidance_scale=2.0` | đủ để thấy giá của bước và của CFG với model chưng cất |
| Prompt | 8 prompt tiếng Anh cho một app tài chính (đồ ăn Việt, đường phố, heo đất, hoá đơn...), 2 seed | CLIP và text encoder của SD chủ yếu hiểu tiếng Anh |
| Đo thời gian | `torch.cuda.synchronize` trước và sau, bỏ ảnh đầu | ảnh đầu khởi tạo kernel CUDA |
| VRAM | `torch.cuda.max_memory_allocated` sau `reset_peak_memory_stats` | đỉnh thật của PyTorch, không gồm context CUDA (khoảng vài trăm MB thêm) |
| Đường nền CLIP | ảnh so với prompt của ảnh khác (dịch vòng 2 vị trí) | biết khoảng cách "khớp" và "không khớp" |

Những lỗi hay gặp: so CLIP score giữa hai model CLIP khác nhau; bật guidance với Turbo rồi kết luận "nhiều bước kém hơn";
đo thời gian không đồng bộ GPU; đo VRAM bằng `nvidia-smi` khi tiến trình khác dùng chung GPU; commit ảnh sinh ra.

## Kết quả tham chiếu

⟦TODO adv02 ref⟧

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Đo đúng cách | 20 | Seed ghim, khởi động, đồng bộ CUDA, VRAM đỉnh bằng PyTorch, trung vị; ghi phần cứng và điều kiện máy |
| Lưới và đường nền | 15 | Đủ cấu hình của đề, có đường nền CLIP, có prompt tiếng Việt |
| Diễn giải trung thực | 25 | So chênh lệch CLIP với độ lệch chuẩn và đường nền; không chọn cấu hình theo chênh lệch nhỏ hơn nhiễu; nói rõ CLIP score không đo gì, có ví dụ từ ảnh |
| Khuyến nghị | 15 | Gắn với một yêu cầu cụ thể (độ trễ, phần cứng), có số, có điều kiện khi nào đổi |
| Giấy phép và an toàn | 10 | Nêu giấy phép không thương mại, không có safety checker, và hệ quả cho sản phẩm |

Đạt từ 70 điểm. Báo cáo kết luận cấu hình "tốt nhất" chỉ bằng CLIP score trung bình mà không so với độ lệch hoặc không xem
ảnh, không quá 55 điểm.
