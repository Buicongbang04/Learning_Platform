---
title: Distillation từ model thầy so với GRPO và tự học
level: advanced
services: []
files:
  - path: starter/distill.ipynb
    note: 1 hàm TODO, 7 hàm dán, khung thí nghiệm
  - path: starter/REPORT.md
    note: Báo cáo so sánh và khuyến nghị
  - path: tests/test_distill.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py gsm8k
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/15-reasoning-models/exercises/advanced/02-distill-vs-grpo/starter/distill.ipynb
  - uv run pytest tracks/ai-engineer/modules/15-reasoning-models/exercises/advanced/02-distill-vs-grpo -q
---

## Mục tiêu

Trả lời câu hỏi mà mọi đội làm model nhỏ gặp: muốn model 0.5B giải toán tốt hơn thì nên **distill** từ một model lớn hơn,
chạy **RL** với reward kiểm được, hay để model **tự học** từ lời giải đúng của chính nó? Bạn dựng nhánh distillation (sinh
dữ liệu tổng hợp bằng model thầy, lọc bằng verifier, SFT), rồi so cả ba nhánh trên cùng tập đo ghim, cùng bộ đo, có
khoảng tin cậy và chi phí. Kết quả trung thực kể cả khi chênh lệch nhỏ.

## Đề bài

**Phần cứng:** GPU 12GB (PC) · ~240 phút

Thời gian trên là thời gian làm bài. Máy chạy riêng trên bản tham chiếu (PC, RTX 3060 12GB): sinh dữ liệu bằng model thầy
`Qwen2.5-3B-Instruct` bf16 qua Transformers, SFT và đo; số phút ghi ở `SOLUTION.md`. **Laptop GPU 4GB:** model thầy là
`qwen2.5:3b` qua Ollama (REST như Intermediate 01, `temperature` 0.7, `seed` theo lượt), khoảng 1 600 lượt gọi; được giảm
số câu train, ghi rõ trong báo cáo. Trên PC có thể thử thêm `qwen2.5:7b` qua Ollama làm thầy mạnh hơn. Cần kết quả đã cache
của Intermediate 03 và Advanced 01 (làm trước); thiếu Advanced 01 thì so hai nhánh và nói rõ.

1. Trong `starter/distill.ipynb`, cell chấm điểm: dán các hàm từ Basic 01, Intermediate 01, Intermediate 03; viết
   `compare_table` (mô tả trong notebook).
2. Cell `explore`: sinh 2 lời giải mỗi câu cho cùng 800 câu train của Intermediate 03 bằng model thầy, đo model thầy greedy
   trên 500 câu test, lọc bằng `select_traces`, SFT model trò bằng **cùng công thức** với Intermediate 03, đo, so sánh.
3. Viết `starter/REPORT.md` theo khung, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt:**

- Mở bằng khuyến nghị có số và chi phí: "distill từ 3B tăng X điểm [a, b] với Y phút sinh dữ liệu; GRPO tăng Z điểm với
  W phút train; tự học ...". Chỉ khác **một biến** giữa các nhánh SFT (nguồn dữ liệu) để so được.
- Bảng `compare_table` cộng chi phí; câu đọc bảng phân biệt chênh lệch thật với nhiễu của 500 câu (một câu = 0.2 điểm,
  khoảng tin cậy của một hiệu cỡ ±3 tới 4 điểm).
- Phân tích dữ liệu tổng hợp: thầy đúng bao nhiêu, bao nhiêu câu có lời giải, độ dài và văn phong so với trò; kiểm
  nhiễm bẩn.
- Giới hạn và điều kiện: thầy 3B chỉ hơn trò vừa phải; giấy phép dùng output của model thầy (Qwen2.5 3B có giấy phép riêng,
  đọc model card); API đóng thường cấm dùng output để train model cạnh tranh.

## Tiêu chí đạt

- `compare_table` đúng cột và thứ tự, hiệu và khoảng tin cậy khớp `paired_bootstrap(..., seed=0)`, `ValueError` khi hai
  phương pháp đo trên số câu khác nhau, `KeyError` khi thiếu `base`.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng so sánh có chi phí.
- Không commit adapter, checkpoint hay cache.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Giữ mọi thứ khác cố định: cùng 800 câu train, cùng `select_traces` (đúng đáp số và đúng khung, tối đa 2 lời giải mỗi câu),
cùng `SFTConfig`, cùng hàm đo. Nếu thầy sinh khung khác (ví dụ không dùng `\boxed`), bộ lọc sẽ bỏ gần hết lời giải: in tỉ lệ
giữ trước khi train.

### Gợi ý 2

So model thầy greedy với model trò sau distill trên cùng 500 câu: khoảng cách đó là trần của distill với lượng dữ liệu
này. Nếu muốn thêm một điểm dữ liệu rẻ, chạy lại SFT với **một nửa** số mẫu để thấy đường cong theo lượng dữ liệu.
