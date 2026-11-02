---
title: Thước đo retrieval recall@k, MRR@k, nDCG@k
level: basic
services: []
files:
  - path: starter/metrics.py
    note: 3 hàm TODO
  - path: tests/test_metrics.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/13-rag/exercises/basic/03-retrieval-metrics -q
---

## Mục tiêu

Tự viết ba thước đo retrieval mà mọi thí nghiệm của module (chunking, BM25, hybrid, rerank) dùng để so sánh, và hiểu
mỗi cái trả lời câu hỏi gì. Không có chúng thì "cách này tốt hơn" chỉ là cảm giác.

## Đề bài

**Phần cứng:** CPU · ~40 phút

Trong `starter/metrics.py`, chỉ dùng thư viện chuẩn, viết ba hàm cùng chữ ký
`(retrieved: list[list[str]], relevant: list[set[str]], k: int) -> float`. `retrieved[i]` là danh sách id hệ thống trả
về cho truy vấn `i` theo thứ tự xếp hạng (không trùng, có thể ngắn hơn `k` hoặc rỗng), `relevant[i]` là tập id đúng
(từ qrels). Mỗi hàm trả **trung bình trên các truy vấn** (`float` Python), đúng định nghĩa ở mục 6 lý thuyết:

1. `recall_at_k`: $$\frac{\left|\mathrm{Rel}_q \cap \{d_1,\dots,d_k\}\right|}{|\mathrm{Rel}_q|}$$ (chia cho số tài liệu đúng,
   không chia cho $$k$$).
2. `mrr_at_k`: $$\frac{1}{\mathrm{rank}_q}$$ với $$\mathrm{rank}_q$$ là hạng (từ 1) của tài liệu đúng **đầu tiên** trong top-$$k$$;
   không có thì 0.
3. `ndcg_at_k`: $$\frac{\mathrm{DCG@}k}{\mathrm{IDCG@}k}$$ với $$\mathrm{DCG@}k = \sum_{i=1}^{k}\frac{\mathrm{rel}_i}{\log_2(i + 1)}$$,
   gain nhị phân $$\mathrm{rel}_i \in \{0, 1\}$$, và IDCG là DCG của thứ tự lý tưởng: mọi tài liệu trong
   $$\mathrm{Rel}_q$$ đứng đầu, kể cả tài liệu đúng mà hệ thống **không** trả về, cắt ở $$k$$.

`k` lớn hơn độ dài danh sách không phải lỗi. Ném `ValueError` khi: một truy vấn có tập đúng rỗng (recall và nDCG không
xác định), không có truy vấn nào (`retrieved` rỗng: trung bình trên 0 truy vấn không xác định), số danh sách
`retrieved` khác số tập `relevant`, hoặc `k < 1`.

Ví dụ ở lý thuyết: đúng {A, B}, trả về [C, A, D, B, E]: recall@3 = 0.5, MRR = 0.5, nDCG@5 = 0.6509.

## Tiêu chí đạt

- Ba hàm khớp giá trị tính tay trên 3 truy vấn với `k = 3` và `k = 5` (dài hơn danh sách của hai truy vấn).
- Recall chia cho số tài liệu đúng; MRR chỉ tính tài liệu đúng đầu tiên, trong top-$$k$$, và lấy trung bình.
- nDCG: IDCG tính từ toàn bộ tập đúng nhưng cắt ở $$k$$; khớp `sklearn.metrics.ndcg_score` trên 20 truy vấn ngẫu nhiên.
- `k` lớn hơn danh sách và danh sách rỗng không lỗi; truy vấn không có tài liệu đúng, không có truy vấn nào, số truy vấn lệch, `k < 1` ném `ValueError`.

## Gợi ý

### Gợi ý 1

Viết một hàm phụ kiểm đầu vào dùng chung cho cả ba hàm, rồi mỗi hàm chỉ là "tính cho một truy vấn, cộng lại, chia số
truy vấn". Cắt `ret[:k]` trước khi làm gì khác: slice của Python không lỗi khi `k` vượt độ dài. `enumerate(..., start=1)`
cho hạng bắt đầu từ 1.

### Gợi ý 2

Với IDCG, câu hỏi là: thứ tự tốt nhất có thể có bao nhiêu tài liệu đúng trong top-$$k$$? Không phải số tài liệu đúng mà
hệ thống tìm được, cũng không phải toàn bộ $$|\mathrm{Rel}_q|$$ nếu nó lớn hơn $$k$$. Tự kiểm bằng hai trường hợp biên: 3
tài liệu đúng, `k = 1`, hạng 1 đúng (phải ra 1.0); và 2 tài liệu đúng mà hệ thống chỉ trả về một, ở hạng 1 (không được
ra 1.0).
