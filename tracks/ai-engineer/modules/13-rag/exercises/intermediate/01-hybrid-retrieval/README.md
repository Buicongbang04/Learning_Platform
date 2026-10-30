---
title: Hybrid retrieval BM25 + bge-m3 trên toàn bộ Zalo Legal
level: intermediate
services: []
files:
  - path: starter/retrieval.ipynb
    note: 5 hàm TODO, cộng tokenize_vi, BM25, recall_at_k, mrr_at_k dán từ Basic 02, 03
  - path: tests/test_retrieval.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/13-rag/exercises/intermediate/01-hybrid-retrieval/starter/retrieval.ipynb
  - uv run pytest tracks/ai-engineer/modules/13-rag/exercises/intermediate/01-hybrid-retrieval -q
---

## Mục tiêu

Dựng hai nhánh retrieval của hệ RAG trên **toàn bộ** 61 425 điều luật: BM25 của bài Basic và dense `bge-m3`, trộn
bằng Reciprocal Rank Fusion, rồi đo recall@k và MRR@10 trên tập đánh giá ghim. Làm xong bạn biết embed và cache một
corpus thật, và thấy bằng số con số ở lát cắt nhỏ của phần lý thuyết thay đổi thế nào khi corpus lớn gấp 17 lần.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Ngoài thời gian làm bài, lần chạy đầu embed cả corpus qua Ollama mất khoảng 45 phút trên laptop của track (GPU 4GB,
23 điều/giây; Ollama chỉ chạy CPU thì lâu hơn nhiều). Vector được cache ở `data/raw/zalo-legal/cache/bge-m3.npy`
(cùng `bge-m3.ids.json`), nên chạy lại notebook chỉ mất khoảng 1 phút. Bài 02 và 03 dùng lại cache này.

Mở `starter/retrieval.ipynb`. Cell đầu (tag `explore`) tải Zalo Legal nếu chưa có. **Tập đánh giá ghim** của cả ba
bài Intermediate: 300 query-id phân biệt đầu tiên theo thứ tự tệp `qrels/test.jsonl`, corpus là toàn bộ
`corpus.jsonl`.

1. `load_corpus(root) -> list[Article]` và `load_questions(root, n, split="test") -> list[Question]` đọc dữ liệu dạng
   BEIR. Notebook mô tả định dạng và quy tắc lấy `n` câu đầu.
2. Dán `tokenize_vi`, `BM25` (Basic 02), `recall_at_k`, `mrr_at_k` (Basic 03) vào cell của chúng. Notebook tự chứa,
   không import chéo bài.
3. `embed_corpus(texts, embed_fn, batch_size=32) -> np.ndarray`: embed theo lô, chuẩn hoá L2 (vector 0 giữ nguyên).
   `dense_search(q_vec, matrix, k) -> list[int]`: top-k theo tích vô hướng, bằng điểm thì chỉ số nhỏ trước.
4. `rrf_fuse(rankings, k=60) -> list[int]`: RRF như mục 3 lý thuyết, bằng điểm thì chỉ số nhỏ trước.

Rồi chạy các cell `explore`: index BM25 cả corpus, embed corpus (hoặc đọc cache) và 300 câu hỏi, in bảng R@1, R@5,
R@10, R@100, MRR@10 của BM25, dense và hybrid, và đếm nhánh nào cứu câu nào. Cell hybrid ghi top-100 ra
`cache/hybrid-top100.json` cho bài 03. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `load_corpus`, `load_questions` đúng trên bộ dữ liệu nhỏ sinh trong test (thứ tự qrels, gom nhiều điều đúng của một
  câu, `split="train"`, `n` lớn hơn số câu có).
- Trên dữ liệu thật: 61 425 điều; 300 câu ghim, câu đầu `268afbc1...` có đáp án `100/2019/nđ-cp+5`, tổng 301 cặp
  câu-điều đúng.
- `embed_corpus` gọi `embed_fn` theo lô `[32, 32, 6]` cho 70 văn bản, kết quả `float32` có chuẩn 1, vector 0 không
  thành `NaN`. `dense_search` tìm đúng tài liệu với `FakeLLM.embed`, ổn định khi bằng điểm.
- `rrf_fuse` khớp bảng tính tay ở mục 3 lý thuyết và đổi thứ tự đúng khi đổi `k`.
- Cell `explore` in bảng ba phương pháp trên tập ghim; với lời giải mẫu, hybrid đạt R@10 0.915 và MRR@10 0.695 (dense một mình 0.905 và 0.706).

## Gợi ý

### Gợi ý 1

`load_questions`: `dict` của Python giữ thứ tự chèn, nên một `dict` từ query-id tới tập điều đúng vừa gom được các dòng
không liền nhau vừa nhớ thứ tự xuất hiện đầu tiên. Trong `embed_corpus`, chia cho chuẩn chỉ ở những dòng có chuẩn khác 0.

### Gợi ý 2

Thứ tự giảm dần mà bằng điểm vẫn giữ chỉ số nhỏ trước: sort ổn định trên điểm âm (`argsort(scores)[::-1]` thì bằng điểm
lại đưa chỉ số **lớn** lên trước). Với RRF, điểm của một tài liệu là tổng qua các danh sách có nó; sort theo khoá gồm
điểm (giảm) rồi chỉ số (tăng).
