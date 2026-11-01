---
title: Reasoning model mini bằng GRPO, có số trước/sau (portfolio)
level: advanced
services: []
files:
  - path: starter/grpo_trl.ipynb
    note: 3 hàm TODO, 5 hàm dán, khung thí nghiệm
  - path: starter/REPORT.md
    note: Báo cáo trước/sau
  - path: tests/test_grpo_trl.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py gsm8k
  - uv run jupyter lab tracks/ai-engineer/modules/15-reasoning-models/exercises/advanced/01-grpo-reasoning-mini/starter/grpo_trl.ipynb
  - uv run pytest tracks/ai-engineer/modules/15-reasoning-models/exercises/advanced/01-grpo-reasoning-mini -q
---

## Mục tiêu

Một dự án để đưa vào portfolio: train một "reasoning model mini" bằng RL với phần thưởng kiểm được (GRPO của TRL trên
`Qwen2.5-0.5B-Instruct`, GSM8K), và chứng minh mức tăng bằng số đáng tin: tập đo ghim, khoảng tin cậy, nhiều seed, tách
phần tăng do **định dạng** khỏi phần tăng do **giải đúng hơn**, đường cong train và phân tích lỗi. Người tuyển dụng đọc
`REPORT.md` phải thấy bạn biết RL trên LLM làm được gì, không làm được gì, và đo nó thế nào.

## Đề bài

**Phần cứng:** GPU 12GB (PC) · ~300 phút

Thời gian trên là thời gian làm bài (code, chạy, đọc mẫu, viết báo cáo). Máy chạy riêng: bản tham chiếu với cấu hình `PC`
mất khoảng thời gian ghi ở `SOLUTION.md` cho mỗi seed (train + đo), RTX 3060 12GB. **Laptop GPU 4GB:** cấu hình `LAPTOP`
trong notebook (batch nhỏ hơn, completion ngắn hơn, ít bước hơn) vừa 4GB; mức tăng nhỏ hơn và nhiễu hơn, báo cáo phải ghi
rõ cấu hình. Không đủ thời gian cho hai seed trên laptop thì một seed kèm khoảng tin cậy bootstrap và nói rõ giới hạn đó.
Đọc mục 4, 5, 7 lý thuyết; làm Intermediate 02 trước.

1. Trong `starter/grpo_trl.ipynb`, cell chấm điểm: dán các hàm từ Basic 01 và Intermediate 01; viết `build_rows`,
   `reward_correct`, `reward_format` theo giao diện reward function của TRL (mô tả trong notebook).
2. Cell `explore` (khung có sẵn, bạn hoàn thiện): đo model gốc greedy trên 500 câu test ghim, train GRPO với LoRA cho
   **ít nhất hai seed**, đo lại, lấy mẫu 8 lời giải cho 200 câu đầu trước và sau để so pass@1 với pass@8.
3. Viết `starter/REPORT.md` theo khung, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt:**

- Mở bằng con số: "accuracy greedy 500 câu từ X lên Y (hiệu Z, khoảng tin cậy 95% [a, b], 2 seed), trong đó phần lớn/nhỏ
  đến từ định dạng". Không mở bằng định nghĩa GRPO.
- Hai thước đo cạnh nhau: `accuracy` (bộ trích dễ dãi, đo khả năng giải) và `boxed_correct` (đúng như reward, đo cả định
  dạng). Mức tăng chỉ có ở cột thứ hai là model học **khung**, không học **toán**.
- Đường cong theo bước: reward từng phần, độ dài, tỉ lệ nhóm std = 0; giải thích hình dạng của chúng.
- Phân tích lỗi bằng ví dụ thật, có đếm; nói rõ có hay không dấu hiệu reward hacking.
- Giới hạn trung thực: 500 câu là ±4 điểm phần trăm, 2 seed, một model, một prompt.

## Tiêu chí đạt

- `build_rows` đúng cấu trúc TRL, đáp số chuẩn hoá (`1,600` thành `1600`).
- `reward_correct`, `reward_format` đọc completion hội thoại, nhận và bỏ qua keyword thừa, trả đúng điểm trên 4 completion
  mẫu (đúng, chữ thừa sau hộp, không có hộp, nhiều số trong hộp).
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng và ít nhất một đường cong.
- Không commit adapter, checkpoint hay cache.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đọc `trainer.state.log_history` sau khi train: mỗi bước là một dict có reward trung bình, reward từng hàm, độ dài
completion, tỉ lệ nhóm std = 0, KL (nếu `beta > 0`), thời gian. Lưu nó ra JSON ngay để vẽ lại sau. Đo trước/sau bằng
**cùng** hàm sinh greedy, cùng prompt, cùng `max_new_tokens`, rồi bootstrap theo cặp trên danh sách đúng/sai từng câu.

### Gợi ý 2

Phần lớn thời gian một bước GRPO là sinh 64 completion. Nếu GPU còn trống, tăng batch sinh nhanh hơn tăng số bước. Nếu
reward đúng khung đã gần 1 ngay từ đầu, phần tăng còn lại phải đến từ đúng đáp số; nếu `frac_reward_zero_std` cao (nhiều
nhóm cùng reward), thử `temperature` cao hơn hoặc lọc câu quá dễ/quá khó, và báo cáo điều bạn đã thử.
