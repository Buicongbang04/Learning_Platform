---
title: "Chấm quillo trên nhãn CUAD: trích dẫn, recall điều khoản, từ chối"
level: basic
services: []
files:
  - path: starter/eval_metrics.py
    note: Bạn viết hàm evaluate
  - path: tests/fixtures/cuad-eval.json
    note: 33 câu hỏi trên 6 hợp đồng CUAD, câu trả lời thật của quillo 1.0.0 (llm-small) và nhãn chuyên gia
  - path: tests/expected/cuad-eval.json
    note: Kết quả đúng cho fixture
  - path: tests/capture_answers.py
    note: Script đã ghi fixture (đọc để biết dữ liệu đến từ đâu; không cần chạy)
  - path: tests/test_eval_metrics.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/09-production-trust/exercises/basic/01-eval-metrics -q
---

## Mục tiêu

Công ty luật hỏi một câu đơn giản: "trợ lý của các anh trả lời đúng bao nhiêu phần trăm?". Con số đó chỉ có nghĩa khi đo
trên **tài liệu của chính khách** với nhãn người có chuyên môn đặt, và khi tách được ba câu hỏi khác nhau: trích dẫn có
trỏ đúng chỗ không, điều khoản có tìm ra không, và hệ thống có biết nói "không có" khi hợp đồng không có điều khoản đó
không. Bài này viết phần chấm cho một bộ eval như vậy, trên câu trả lời thật của quillo và nhãn của CUAD.

## Đề bài

Viết `starter/eval_metrics.py` (Python 3.12, chỉ thư viện chuẩn): hàm `evaluate(items) -> dict` và CLI
`python eval_metrics.py <fixture.json>` in kết quả của `evaluate` cho mảng `items` trong tệp ra stdout (JSON), thoát `0`.

**Dữ liệu.** Mỗi phần tử của `items` (xem `tests/fixtures/cuad-eval.json`, ghi bằng `tests/capture_answers.py`):

| Trường | Ý nghĩa |
| --- | --- |
| `id`, `contract`, `clause`, `question` | mã câu, hợp đồng (tên trong CUAD) được hỏi, loại điều khoản CUAD, câu hỏi đã gửi quillo |
| `gold` | nhãn chuyên gia: danh sách khoảng ký tự `[start, end)` trong văn bản hợp đồng; rỗng = hợp đồng **không có** điều khoản này |
| `answer` | câu trả lời nguyên văn của quillo |
| `citations` | trích dẫn quillo trả, mỗi cái `{contract, chunk, start, end}`: đoạn `[start, end)` của hợp đồng `contract` |

Văn bản hợp đồng không nằm trong fixture; bạn không cần nó (vị trí đã đủ). Văn bản CUAD v1 là của The Atticus Project,
giấy phép CC BY 4.0 (xem `data/README.md`).

**Quy tắc** (test chấm đúng các quy tắc này):

1. *Câu có nhãn* là câu có `gold` không rỗng; *câu không nhãn* là câu có `gold` rỗng.
2. *Từ chối*: chuyển `answer` về chữ thường, thay `’` bằng `'`, bỏ khoảng trắng hai đầu. Câu trả lời là từ chối khi (a)
   sau khi bỏ thêm các ký tự `.!?,;:` và dấu cách ở cuối, nó **bằng** `no`, `none` hoặc `n/a`; hoặc (b) nó **chứa** một
   trong các cụm: `i don't know`, `i do not know`, `does not contain`, `doesn't contain`, `do not contain`,
   `not mentioned`, `no information`, `cannot find`, `can't find`, `not specified`, `not provided`, `no mention`,
   `there is no`, `not found`, `no documents have been ingested`.
3. *Trích dẫn đúng*: cùng `contract` với câu hỏi **và** chồng lên một khoảng `gold` của câu đó ít nhất
   `min(độ dài khoảng gold, 50)` ký tự (độ chồng của `[a, b)` và `[c, d)` là `min(b, d) − max(a, c)`).
4. *Câu tìm ra*: câu có nhãn, không phải từ chối, có ít nhất một trích dẫn đúng.
5. Chỉ số (làm tròn 4 chữ số thập phân; mẫu số bằng 0 thì `null`):
   - `citation_precision` = số trích dẫn đúng / số trích dẫn, tính trên mọi câu **không** phải từ chối (câu không nhãn
     mà vẫn trả lời thì mọi trích dẫn của nó đều sai).
   - `clause_recall` = số câu tìm ra / số câu có nhãn.
   - `correct_refusal_rate` = số câu không nhãn bị từ chối / số câu không nhãn.
   - `false_refusal_rate` = số câu có nhãn bị từ chối / số câu có nhãn.
6. Output là object có `items`, `answerable`, `unanswerable` (số câu), bốn chỉ số trên, và `per_clause`: với mỗi
   `clause`, `{"items", "answerable", "found"}` (số câu, số câu có nhãn, số câu tìm ra).

## Tiêu chí đạt

`test_eval_metrics.py`:

- `test_recorded_answers`: `evaluate` trên fixture ra đúng `tests/expected/cuad-eval.json` (sai số < 1e-4 với số thực).
- `test_same_result_after_renaming_and_shifting`: fixture bị xáo thứ tự, đổi tên hợp đồng và `id`, dời mọi vị trí của
  một hợp đồng đi cùng một khoảng ngẫu nhiên vẫn ra đúng kết quả đó.
- `test_rules`, `test_per_clause_counts`: các ca nhỏ dựng tay cho từng quy tắc (ngưỡng 50 ký tự, nhãn ngắn, sai hợp đồng,
  từ chối, mẫu số 0).
- `test_cli_prints_same_json`: CLI in đúng JSON đó.

## Gợi ý

### Gợi ý 1

Viết quy tắc 3 thành một hàm thuần nhận một trích dẫn và một câu, thử nó với vài khoảng vẽ trên giấy trước khi gộp số.

### Gợi ý 2

Khi có kết quả, đọc lại vài câu trong fixture mà bạn thấy chỉ số "bất công" với quillo. Câu hỏi đáng hỏi không phải "chỉ
số có sai không" mà "chỉ số này đo hành vi nào của hệ thống, và khách có quan tâm hành vi đó không".
