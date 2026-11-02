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

Bản tham chiếu (code ngoài repo), PC của track: RTX 3060 dùng chung, env `setup/gpu`, fp16, 512×512; 8 prompt tiếng Anh ×
2 seed = 16 ảnh mỗi cấu hình; CLIP `openai/clip-vit-base-patch32` chạy trên cùng GPU. Log: `adv02_sweep_cuda.log`,
`adv02_sweep_cpu.log`, `sd_probe_cuda.log` trong `.superpowers/scratch/logs/`.

| Bước | `guidance_scale` | CLIP score TB | Độ lệch chuẩn | Giây mỗi ảnh (trung vị) |
| --- | --- | --- | --- | --- |
| 1 | 0 | 31.14 | 3.49 | 0.236 |
| 2 | 0 | 29.68 | 3.08 | 0.297 |
| 4 | 0 | 30.30 | 2.76 | 0.420 |
| 1 | 2.0 | 31.23 | 3.45 | 0.305 |
| 4 | 2.0 | 30.06 | 3.18 | 0.594 |
| Prompt tiếng Việt, 1 bước, 0 | | 22.40 | 5.14 | 0.233 |
| Đường nền: ảnh 1 bước so với prompt của ảnh khác | | 15.21 | | |

VRAM đỉnh 3.59 GiB khi pipeline và CLIP cùng nằm trên GPU (pipeline một mình: 3.02 GiB). CPU 4 luồng fp32 (2 prompt × 2
seed): 13.8 giây ở 1 bước, 23.5 giây ở 4 bước, CLIP 33.1 và 33.4.

Đọc kết quả:

- **Không cấu hình tiếng Anh nào hơn cấu hình khác một cách đo được**: CLIP score chênh tối đa 1.6 điểm, trong khi độ lệch
  chuẩn giữa các ảnh khoảng 3 và sai số chuẩn của trung bình 16 ảnh khoảng 0.8. Khoảng cách tới đường nền (khoảng 15 điểm)
  cho thấy CLIP score vẫn phân biệt rõ "khớp" và "không khớp"; nó chỉ không đủ nhạy để chọn giữa các cấu hình gần nhau.
- **Khuyến nghị cho "dưới 1 giây trên GPU 4GB"**: 1 bước, không guidance: 0.24 giây, nhanh nhất, chất lượng CLIP không thua.
  Nhìn ảnh: 4 bước có guidance cho màu bão hoà và tương phản gắt hơn (đúng hiện tượng "ảnh cháy" của guidance lớn ở module
  06), không đẹp hơn.
- **Prompt tiếng Việt** tụt khoảng 9 điểm CLIP, độ lệch gần gấp đôi: "một tờ hoá đơn mua hàng trên bàn" cho ảnh một con
  phố, trong khi "một bát phở bò" vẫn ra một tô mì (chữ "phở" có trong dữ liệu train tiếng Anh). Text encoder OpenCLIP chủ
  yếu học từ chú thích tiếng Anh; sản phẩm cho người Việt nên dịch prompt trước.
- **Chữ trong ảnh**: mọi ảnh hoá đơn có các dòng ký tự vô nghĩa; CLIP score của chúng vẫn ngang các prompt khác. Đó là ví dụ
  rõ nhất của thứ CLIP score không đo.
- Giấy phép: SD-Turbo theo Stability AI Non-Commercial Research Community License, pipeline tải về không có safety checker
  (diffusers in cảnh báo khi nạp).

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
