---
title: Đánh giá prompt có số đo - zero-shot, few-shot, CoT, JSON schema trên UIT-VSFC
level: intermediate
services: []
files:
  - path: starter/prompt_eval.ipynb
    note: 4 hàm TODO
  - path: tests/test_prompt_eval.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/intermediate/02-prompt-eval/starter/prompt_eval.ipynb
  - uv run pytest tracks/ai-engineer/modules/11-llm-apis-prompting/exercises/intermediate/02-prompt-eval -q
---

## Mục tiêu

Thay "prompt này có vẻ tốt hơn" bằng một con số có khoảng tin cậy. Bạn so bốn kỹ thuật prompt kinh điển với
`qwen2.5:3b` trên cùng 150 câu ghim của UIT-VSFC, đọc kết quả như một kỹ sư (cái gì vượt nhiễu, cái gì không, tốn
thêm bao nhiêu token và giây), và thấy một kỹ thuật "luôn tốt" làm hỏng kết quả khi ví dụ chọn không khéo.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Mở `starter/prompt_eval.ipynb`. Các hằng prompt (`TASK`, `ONE_WORD`, `COT`, `JSON_INSTR`, `SCHEMA`, `NUM_PREDICT`) là
prompt của mục 4 và 7 lý thuyết: giữ nguyên. Trong các cell chấm điểm:

1. `build_messages(variant, sentence, examples)`: messages cho `zero_shot`, `few_shot` (mỗi ví dụ là một cặp lượt
   user/assistant), `cot`, `json_schema`.
2. `parse_label(variant, reply)`: đọc nhãn theo quy tắc của từng biến thể (một từ duy nhất; nhãn sau `Nhãn:` **cuối
   cùng**; JSON có `label` hợp lệ), không đọc được thì `None`.
3. `macro_f1(y_true, y_pred)`: `None` là dự đoán sai, khớp `sklearn`.
4. `paired_bootstrap(y_true, pred_a, pred_b, n_boot=2000, seed=0)`: hiệu macro-F1 (B trừ A) và khoảng tin cậy 95%,
   theo đúng thứ tự gọi bộ sinh số ngẫu nhiên mà notebook mô tả để số của bạn trùng số lý thuyết.

Rồi chạy các cell `explore`: 4 biến thể x 150 câu qua REST của Ollama (cache vào `data/raw/uit-vsfc/cache/`), bảng
macro-F1 kèm CI, accuracy, số `None`, độ trễ trung vị, token vào/ra; so từng biến thể với zero-shot theo cặp; chạy lại
zero-shot y hệt để đo sàn nhiễu; ma trận nhầm lẫn. Khoảng 750 lượt gọi model, khoảng 8 phút trên PC của track (GPU
dùng chung), phần lớn là CoT; trên laptop lâu hơn (chưa đo). Cell cuối (tuỳ chọn, mặc định tắt) gửi 20 câu cho một
model API qua gateway tương thích OpenAI; không cần cho bài.

Sau đó làm phần trắc nghiệm của bài trong app. Câu trả lời của model có thể lệch đôi chút giữa các máy và phiên bản
Ollama; câu trắc nghiệm số liệu lấy từ lần chạy của lời giải mẫu và hỏi theo khoảng hoặc so sánh.

## Tiêu chí đạt

- `build_messages` đúng từng message cho bốn biến thể, giữ thứ tự ví dụ, `few_shot` không ví dụ giống `zero_shot`,
  biến thể lạ thì `ValueError`.
- `parse_label` đúng 9 ca một từ (kể cả "positive hoặc negative" và "negatively" là `None`), 6 ca CoT (lấy `Nhãn:`
  cuối, chịu được `*` và backtick, không lấy nhãn trong câu suy luận), 8 ca JSON.
- `macro_f1` khớp tính tay và `sklearn` trên 30 bộ ngẫu nhiên có `None`.
- `paired_bootstrap` khớp từng chữ số với quy trình mô tả, hiệu bằng 0 khi hai dự đoán giống nhau, đổi chỗ A/B thì
  đổi dấu.
- Cell `explore` chạy hết và in bảng bốn biến thể, so sánh theo cặp, sàn nhiễu.

## Gợi ý

### Gợi ý 1

Với một từ, `re.findall(r"[a-z]+", reply.lower())` cho danh sách từ; gom các từ là nhãn vào một `set`. Với CoT,
`re.findall` cho mọi lần khớp theo thứ tự xuất hiện: lấy phần tử cuối. Viết test nhỏ của riêng bạn với vài câu trả lời
thật in ra từ cell chạy trước khi tin parser.

### Gợi ý 2

F1 của một nhãn là $$\frac{2\,TP}{2\,TP + FP + FN}$$: `None` không bao giờ là `FP` của nhãn nào, nhưng là `FN` của nhãn
đúng. Với bootstrap, chuyển ba danh sách sang `np.array(..., dtype=object)` để đánh chỉ số bằng mảng `idx` được cả khi
có `None`, và dùng **cùng** `idx` cho A và B: đó là chữ "theo cặp".
