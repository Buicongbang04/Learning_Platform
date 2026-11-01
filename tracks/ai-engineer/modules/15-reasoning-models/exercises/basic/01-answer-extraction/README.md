---
title: Trích đáp số, so chính xác và reward kiểm được trên GSM8K
level: basic
services: []
files:
  - path: starter/answers.py
    note: 7 hàm TODO
  - path: tests/test_answers.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py gsm8k
  - uv run pytest tracks/ai-engineer/modules/15-reasoning-models/exercises/basic/01-answer-extraction -q
---

## Mục tiêu

Mọi con số của module (độ chính xác CoT, self-consistency, reward của GRPO) đi qua một hàm: đọc đáp số từ câu trả lời
tự do của model rồi so với đáp án. Hàm đó sai một chút là bảng kết quả sai cả bảng, và reward sai một chút là model học
cách lách reward thay vì học giải toán. Bài này viết bộ trích đáp số và hai reward kiểm được mà cả module dùng lại.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Đọc mục 1 và mục 4 lý thuyết. Trong `starter/answers.py`, viết:

1. `normalize_number(text) -> str | None`: `text` phải là **đúng một số** (sau khi bỏ khoảng trắng hai đầu). Trả về
   `str(Fraction(...))` của số đó, để hai cách viết của cùng một giá trị (`2.50`, `5/2`, `$2.50`) có cùng một dạng.
   Chấp nhận: dấu `$` (cả `\$` của LaTeX) và `%`, dấu phẩy ngăn hàng nghìn (`1,234`, `1,000,000`; nhưng `1,2` và
   `1,0000` không phải số), dấu chấm cuối câu (`18.`), dấu `+` đầu, dấu trừ unicode `−`, số thập phân, phân số
   `a/b` với `a`, `b` nguyên (mẫu 0 thì `None`). Mọi thứ khác cho `None`.
2. `gold_answer(answer_field) -> str`: đáp số chuẩn hoá ở phần sau `####` của cột `answer` GSM8K.
3. `extract_answer(completion) -> str | None`: đáp số của một câu trả lời tự do, theo thứ tự ưu tiên:
   1. thẻ `<answer>...</answer>` **cuối cùng**, nếu trong thẻ có số: số **cuối cùng** trong thẻ;
   2. `\boxed{...}` cuối cùng, nếu có số: số cuối cùng trong đó;
   3. phần sau `####` cuối cùng, nếu có số: số **đầu tiên** sau nó;
   4. phần sau cụm `answer is` hoặc `answer:` cuối cùng (không phân biệt hoa thường), nếu có số: số đầu tiên sau nó;
   5. số cuối cùng của cả câu trả lời; không có số nào thì `None`.

   "Số" trong văn bản tự do: có thể có `$` đứng trước, phẩy ngăn hàng nghìn, phần thập phân, dạng `a/b`. Dấu `-` chỉ là
   dấu âm khi **không** đứng ngay sau chữ hoặc số: `3-4 hours` là hai số 3 và 4, `to -4 degrees` là -4.
4. `is_correct(completion, gold) -> bool`.
5. `format_reward(completion) -> float`: 1.0 khi completion đúng khung mà Qwen2.5 dùng cho toán: có lập luận (ít nhất một
   chữ cái) **trước** đúng **một** `\boxed{...}`, trong hộp là đúng một số theo `normalize_number`, và sau hộp không còn
   chữ hay số nào (chỉ khoảng trắng, dấu câu, `$`, `\]`). Ngược lại 0.0.
6. `correctness_reward(completion, gold) -> float`: 1.0 khi nội dung `\boxed{}` **cuối cùng** là đúng một số và bằng
   `gold`; không có hộp, hoặc trong hộp không phải đúng một số (`17 or 18`), thì 0.0.
7. `total_reward(completion, gold, format_weight=0.2)`: tổng hai reward trên, reward định dạng nhân trọng số.

Chỉ dùng thư viện chuẩn. Test cuối đọc GSM8K thật (tự skip nếu chưa tải).

## Tiêu chí đạt

- `normalize_number` cho cùng một dạng với `2.5`, `2.50`, `5/2`, `$2.50`, `10/4`; từ chối `1,2`, `1,0000`, `12 eggs`, `10/0`, `36.7/100`.
- `extract_answer` đúng thứ tự ưu tiên trên 15 câu trả lời mẫu (thẻ answer, `\boxed`, `####`, "answer is", số cuối;
  số âm, khoảng `3-4`, phân số, tiền có phẩy).
- `format_reward` đúng trên 12 trường hợp: chữ hoặc số thừa sau hộp, không có lập luận, hai hộp, đáp số bằng chữ hoặc nhiều số.
- `correctness_reward` không cho điểm `\boxed{17 or 18}` khi đáp án là 18, và chấm theo hộp **cuối cùng**.
- Trên GSM8K thật: đọc được đáp số của cả 8 792 câu, và `extract_answer` trên lời giải mẫu của 1 319 câu test trả đúng đáp số.

## Gợi ý

### Gợi ý 1

`fractions.Fraction` nhận chuỗi `"2.50"`, `"-3"`, `"3/4"` và tự rút gọn; `str()` của nó là dạng chuẩn bạn cần. Bỏ phẩy
hàng nghìn bằng một regex chỉ khớp dấu phẩy có chữ số ở trước và **đúng ba** chữ số ở sau. Với `extract_answer`, viết
một hàm phụ trả về mọi số (đã chuẩn hoá) trong một đoạn văn bản, rồi mỗi bước ưu tiên chỉ là "tìm đoạn, lấy số đầu
hoặc số cuối".

### Gợi ý 2

Lookbehind `(?<![\w.])` trước dấu trừ trong regex số giải quyết cả `3-4` lẫn `x-5`. Với `format_reward`, đếm số lần
xuất hiện của `\boxed{` trước, rồi tách phần trước và phần sau hộp: hai regex nhỏ "có chữ cái" và "có chữ hoặc số" là
đủ. Lớp ký tự `[^\W\d_]` khớp đúng chữ cái (kể cả chữ có dấu).
