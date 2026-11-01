---
title: Memory dài hạn cho trợ lý - ghi, đọc, quên, và đo trên hội thoại 6 phiên
level: intermediate
services: []
files:
  - path: starter/memory.ipynb
    note: recency_weight, MemoryStore (2 phương thức), extract_facts TODO
  - path: starter/dialogue.py
    note: Hội thoại 6 phiên và 20 câu hỏi (không sửa)
  - path: tests/test_memory.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/16-ai-agents/exercises/intermediate/03-agent-memory/starter/memory.ipynb
  - uv run pytest tracks/ai-engineer/modules/16-ai-agents/exercises/intermediate/03-agent-memory -q
---

## Mục tiêu

Dựng memory dài hạn cho một trợ lý cá nhân: kho ghi nhớ có embedding (khái niệm của module 12), chính sách ghi (lưu
nguyên lượt hay trích thông tin bằng LLM, gộp bản trùng), chính sách đọc (liên quan, độ mới, độ quan trọng), chính
sách quên khi kho đầy. Rồi đo trên một hội thoại 6 phiên có 20 câu hỏi: retrieval có tìm đúng ghi nhớ không, và trợ lý
trả lời đúng bao nhiêu so với không có memory và so với nhét cả lịch sử vào context.

## Đề bài

**Phần cứng:** CPU · ~80 phút

Thời gian trên là thời gian làm bài. Các cell `explore` gọi `qwen2.5:3b` khoảng 190 lượt và `bge-m3` vài trăm lượt:
chạy khoảng 15 phút trên PC của track, phần lớn là điều kiện "toàn bộ lịch sử" (mỗi câu vài chục giây vì prompt vượt
context mặc định của Ollama).

`starter/dialogue.py` dựng 108 lượt hội thoại trong 6 phiên (24 lượt chứa thông tin về người dùng, có thông tin được
cập nhật ở phiên sau như nơi ở, công việc, đồ uống) và 20 câu hỏi chia 4 nhóm: thông tin cũ, thông tin mới, thông tin
đã cập nhật, thông tin không có.

Trong `starter/memory.ipynb`:

1. `recency_weight(age_hours, half_life_hours)`.
2. `MemoryStore.add`: bỏ văn bản rỗng, gộp bản trùng theo ngưỡng cosine (cập nhật tại chỗ, giữ `id`), thêm mới, quên
   khi vượt `capacity` theo `importance * recency_weight` (không quên cái vừa thêm).
3. `MemoryStore.search`: điểm có trọng số của độ liên quan, độ mới, độ quan trọng; thứ tự khi bằng điểm.
4. `extract_facts(llm, user_turn)`: một lời gọi LLM có `json_schema`, chịu được output hỏng và `LLMError`.

Notebook nêu chính xác quy ước của từng hàm. Rồi chạy các cell `explore`: dựng kho `raw` và kho `fact`, bảng hit@k
với và không có trọng số độ mới, thí nghiệm quên với `capacity=20`, và 20 câu hỏi với 4 điều kiện. Sau đó làm phần trắc
nghiệm của bài trong app.

## Tiêu chí đạt

- `recency_weight` đúng bán rã, tuổi âm coi như 0.
- `add`: chuẩn hoá vector, `id` tăng dần, ngưỡng gộp tính cả dấu bằng, cập nhật giữ `id` và lấy `importance` lớn hơn,
  quên đúng ghi nhớ có điểm giữ thấp nhất (kể cả khi ghi nhớ đó có `importance` cao nhưng đã rất cũ), bằng điểm thì quên
  cái cũ hơn.
- `search`: điểm đúng công thức với từng tổ hợp trọng số, bằng điểm thì mới hơn trước, kho rỗng trả `[]`, chạy được với
  `FakeLLM().embed`.
- `extract_facts`: đúng hai message và `json_schema`; 6 kiểu output hỏng và `LLMError` đều cho `[]`.
- Các cell `explore` chạy hết với `qwen2.5:3b` và `bge-m3`.

## Gợi ý

### Gợi ý 1

Chuẩn hoá vector một lần lúc thêm, rồi cosine chỉ còn là tích vô hướng: `np.stack([m.vector for m in items]) @ q`.
Với tie-break trong `search`, `list.sort` với khoá là tuple `(-score, -t, -id)` cho đúng thứ tự trong một lần sắp.

### Gợi ý 2

Khi quên, ứng viên là mọi ghi nhớ **trừ** cái vừa thêm (nếu không, một ghi nhớ mới có `importance` thấp bị xoá ngay
khi vừa vào). Thử tay: ba ghi nhớ ở giờ 0, 10, 20 với bán rã 10 giờ, tính điểm giữ của từng cái ở giờ 20, rồi so với
kết quả của bạn. Với `extract_facts`, gom mọi kiểu lỗi (JSON hỏng, thiếu khoá, sai kiểu, `LLMError`) vào cùng một
nhánh trả `[]`.
