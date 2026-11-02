---
title: BM25 cho tiếng Việt với tokenizer âm tiết
level: basic
services: []
files:
  - path: starter/bm25.py
    note: tokenize_vi và lớp BM25 (3 phương thức) TODO
  - path: tests/test_bm25.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/13-rag/exercises/basic/02-bm25 -q
---

## Mục tiêu

Tự cài nhánh retrieval theo từ của hệ thống RAG: tokenizer âm tiết tiếng Việt và BM25 với IDF dạng Lucene,
rồi thấy nó tái tạo đúng con số R@10 0.930 ở mục 3 lý thuyết trên lát cắt Zalo Legal.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/bm25.py`, chỉ dùng thư viện chuẩn và numpy, viết:

1. `tokenize_vi(text: str) -> list[str]`: chuẩn hoá **NFC**, chữ thường, bỏ dấu câu (mọi ký tự không phải chữ hoặc
   số coi như khoảng trắng), tách theo khoảng trắng. Mỗi token là một âm tiết hoặc một số:
   `"Nghị định 100/2019/NĐ-CP"` thành `["nghị", "định", "100", "2019", "nđ", "cp"]`. Đây là tokenizer "âm tiết"
   trong bảng so sánh ở mục 3 lý thuyết.
2. `class BM25(docs: list[list[str]], k1: float = 1.5, b: float = 0.75)`: nhận các tài liệu **đã tokenize**, dựng
   một lần mọi thống kê cần cho chấm điểm. Công thức đúng như mục 3 lý thuyết:

   $$
   \mathrm{BM25}(q, d) = \sum_{t \in q} \mathrm{IDF}(t)\cdot\frac{f(t, d)\,(k_1 + 1)}{f(t, d) + k_1\left(1 - b + b\,\frac{|d|}{\mathrm{avgdl}}\right)},
   \qquad
   \mathrm{IDF}(t) = \ln\left(1 + \frac{N - n_t + 0.5}{n_t + 0.5}\right)
   $$

   - `scores(query: list[str]) -> np.ndarray`: điểm của câu hỏi (đã tokenize) với **mọi** tài liệu, shape `(N,)`,
     theo đúng thứ tự `docs`. Tổng chạy trên từng token của câu hỏi, token lặp thì cộng mỗi lần; token không có trong
     corpus đóng góp 0.
   - `top_k(query: list[str], k: int) -> list[int]`: chỉ số (kiểu `int` Python) của `min(k, N)` tài liệu điểm cao nhất,
     giảm dần; điểm bằng nhau thì chỉ số nhỏ đứng trước.

## Tiêu chí đạt

- `tokenize_vi` bỏ dấu câu, đưa về chữ thường; "Luật" gõ NFC và "luật" dạng NFD cho cùng token `"luật"`.
- Điểm trên corpus 3 tài liệu khớp giá trị tính tay tới `1e-9`, với cả tham số mặc định lẫn `k1=1.2, b=0.5`.
- Tài liệu không chứa từ nào của câu hỏi có điểm 0; term có ở **mọi** tài liệu vẫn có IDF dương.
- `b=0` làm điểm không phụ thuộc độ dài tài liệu; tần suất bão hoà, không vượt $$\mathrm{IDF}\cdot(k_1 + 1)$$.
- `top_k` đúng thứ tự, giữ chỉ số nhỏ trước khi bằng điểm, không lỗi khi `k > N`.
- Test dữ liệu thật (tự skip nếu chưa chạy `uv run python data/download_dataset.py zalo-legal`): trên lát cắt 100 câu
  hỏi / 3 541 điều của lý thuyết, R@1 = 0.540, R@10 = 0.930, MRR@10 khoảng 0.686. Chạy dưới 5 giây.

## Gợi ý

### Gợi ý 1

`re.findall(r"\w+", ...)` tách theo chữ và số, coi mọi thứ khác là ranh giới. Nhưng thứ tự quan trọng: trên chuỗi
NFD, dấu thanh là code point riêng và **không** phải `\w`, nên chữ bị chặt vụn (mục 2 lý thuyết có ví dụ "lua", "t").
Với IDF, tự tính tay cho một term có ở cả 3/3 tài liệu: dạng có "1 +" và dạng không có khác nhau thế nào về dấu?

### Gợi ý 2

Phần mẫu số $$k_1\left(1 - b + b\,\frac{|d|}{\mathrm{avgdl}}\right)$$ chỉ phụ thuộc tài liệu, không phụ thuộc term: tính
một mảng cho cả corpus trong `__init__`. Để `scores` nhanh trên hàng nghìn tài liệu, đừng duyệt mọi tài liệu cho mỗi
term: dựng **inverted index** `term -> (mảng chỉ số tài liệu chứa term, mảng tần suất)`, rồi cộng vào mảng điểm bằng
fancy indexing của numpy. Thứ tự ổn định khi bằng điểm: xem tham số `kind` của `np.argsort`.
