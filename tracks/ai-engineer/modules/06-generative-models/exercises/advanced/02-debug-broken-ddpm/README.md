---
title: Gỡ lỗi một pipeline DDPM hỏng mà không báo lỗi
level: advanced
services: []
files:
  - path: starter/broken_ddpm.ipynb
    note: 5 bug im lặng, không nói ở đâu
  - path: starter/BUGS.md
    note: Ghi lại từng bug
  - path: tests/test_broken_ddpm.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py mnist
  - uv run jupyter lab tracks/ai-engineer/modules/06-generative-models/exercises/advanced/02-debug-broken-ddpm/starter/broken_ddpm.ipynb
  - uv run pytest tracks/ai-engineer/modules/06-generative-models/exercises/advanced/02-debug-broken-ddpm -q
---

## Mục tiêu

Diffusion có một kiểu hỏng riêng: loss giảm đẹp, mọi tensor đúng shape, nhưng ảnh sinh ra xám xịt, toàn nhiễu, hoặc kém mà không rõ vì
sao. Nguyên nhân gần như luôn là **train và sinh đang giải hai bài toán khác nhau**, hoặc đánh giá đang đo sai thứ. Bài này cho bạn một
pipeline DDPM hoàn chỉnh trên MNIST có 5 bug như vậy. Làm xong bạn có một quy trình khoanh vùng bằng phép đo cho mọi pipeline diffusion,
và một `BUGS.md` đáng đưa vào portfolio.

## Đề bài

**Phần cứng:** GPU 4GB · ~150 phút

Thời gian trên là thời gian điều tra. Mỗi lần train 3 000 bước (U-Net 1.05 triệu tham số, batch 128) mất khoảng 3 phút trên GPU; trên CPU
notebook tự giảm còn 600 bước (khoảng 5 phút) và ảnh mờ hơn, đủ để so trước và sau khi sửa. Phần lớn giả thuyết kiểm được trong vài giây
trên CPU mà không cần train lại (xem gợi ý).

`starter/broken_ddpm.ipynb` đọc MNIST, train một DDPM (schedule linear $$T = 1000$$, dự đoán nhiễu, AdamW, EMA 0.999), sinh 1 000 ảnh bằng DDIM
50 bước với trọng số EMA, và chấm bằng một classifier MNIST: tỉ lệ ảnh classifier tự tin trên 0.9, số lớp xuất hiện, và độ sáng trung bình
(ảnh MNIST thật: khoảng 0.12). Notebook chạy hết, loss giảm, nhưng giám khảo cho điểm rất thấp. Trong các cell định nghĩa có **5 bug im
lặng**, mỗi bug một chỗ, đều là lỗi hay gặp khi tự viết hoặc sửa một pipeline diffusion.

1. Tìm và sửa cả 5 bug ngay trong notebook. Không đổi chữ ký hàm, siêu tham số mặc định của `train`, kiến trúc `UNet`, schedule hay
   `DEVICE`: sửa ở gốc, không bù triệu chứng bằng cách train lâu hơn, đổi lr hay đổi sampler.
2. Mỗi giả thuyết một phép thử; thêm cell `explore` tuỳ ý. Công cụ: các phép kiểm của bài Basic 03 và Intermediate 03, mục 5 lý thuyết, câu
   "case" cuối của interview.
3. Ghi `starter/BUGS.md`: mỗi bug một mục `## Bug N: <tên ngắn>` với **triệu chứng** (con số), **cách phát hiện** (phép thử nào, kết quả gì)
   và **sửa** (dòng trước và sau). Cuối cùng ghi thứ tự gỡ, giám khảo sau mỗi lần sửa, bug nào che bug nào, và checklist bạn sẽ chạy trước
   khi train một diffusion model lâu.
4. Làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Siêu tham số mặc định của `train`, schedule và kiến trúc `UNet` (1 045 729 tham số) không đổi.
- Mỗi hàm làm đúng việc mà tên và docstring của nó nói: test so `preprocess`, `postprocess`, `q_sample`, `ddpm_loss` với cài đặt tham chiếu;
  `ddim_sample` trả đúng ảnh khi model là oracle của dữ liệu một điểm, và tất định với cùng generator kể cả khi model đưa vào đang ở chế độ
  train; `EMA` là trung bình trượt riêng, không đụng tới trọng số của model; `train` cập nhật EMA thật.
- `BUGS.md` không còn TODO, ít nhất 5 mục `## Bug N`, ít nhất 350 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`; trên GPU, bản đã sửa cho tỉ lệ tự tin của giám khảo khoảng gấp đôi bản gốc (0.56 so với 0.28)
  và độ sáng trung bình gần ảnh thật (khoảng 0.17 so với 0.12).

## Gợi ý

### Gợi ý 1

Chia pipeline thành bốn đoạn và kiểm từng đoạn độc lập, rẻ trước đắt sau: dữ liệu vào model (thang, min/max, đi vòng qua hàm đảo ngược),
forward process (so với công thức trên giấy, hoặc chạy chuỗi Markov từng bước), sampler (một model "oracle" biết đúng nhiễu cho dữ liệu chỉ
có một ảnh: sampler đúng phải trả lại đúng ảnh đó; chạy hai lần với cùng seed), và đường đánh giá (đưa ảnh **thật** qua đúng đường mà ảnh sinh
đi qua trước khi tới giám khảo). Đừng sửa gì trước khi có một con số chứng minh nó sai.

### Gợi ý 2

Một số bug chỉ lộ ra khi các bug khác đã sửa, và một số bug làm giám khảo nói sai về những bug còn lại. Sửa xong mỗi bug, chạy lại mọi phép
thử và ghi điểm giám khảo. Kiểm cả những thứ "sống" qua nhiều bước: trạng thái train/eval của model khi sinh, và EMA có thật sự là một bản
sao riêng hay không (so `data_ptr()` hoặc sửa một bên rồi nhìn bên kia).
