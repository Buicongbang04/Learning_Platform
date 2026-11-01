---
title: Product Quantization tự viết và chọn index ANN theo ngân sách
level: advanced
services: []
files:
  - path: starter/pq.ipynb
    note: pq_train, pq_encode, pq_decode, pq_search, pareto_front TODO; phần đo tự viết
  - path: starter/REPORT.md
    note: Bảng đo, biên Pareto, lựa chọn cho ba kịch bản
  - path: tests/test_pq.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/advanced/01-ann-benchmark-pq/starter/pq.ipynb
  - uv run pytest tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/advanced/01-ann-benchmark-pq -q
---

## Mục tiêu

Tự cài Product Quantization với tìm kiếm ADC, rồi làm việc một kỹ sư làm trước khi chọn index cho production: đo một
bảng đủ rộng trên dữ liệu thật theo ba trục recall, độ trễ, bộ nhớ, tìm biên Pareto, và chọn cấu hình cho từng ngân sách
bằng số, kèm phép chiếu lên quy mô lớn hơn.

## Đề bài

**Phần cứng:** CPU · ~4 giờ

Dữ liệu: 61 425 vector `bge-m3` (cache của bài Intermediate 01), 300 câu hỏi ghim (300 query-id đầu của
`qrels/test.jsonl`). Ground truth là top-10 của kNN chính xác.

1. **Hàm** (notebook mô tả chính xác, có test): `pq_train`, `pq_encode`, `pq_decode`, `pq_search` (ADC), `pareto_front`.
2. **Bảng đo** ít nhất 10 cấu hình, gồm: exact (numpy hoặc `IndexFlatIP`), HNSW (ít nhất 2 `efSearch`), IVF (ít nhất 2
   `nprobe`), PQ tự viết với ít nhất 2 giá trị `m`, cùng PQ đó có rescoring top-100 bằng vector gốc, và FAISS `IndexIVFPQ`.
   Mỗi dòng: recall ANN@10, Recall@10 theo nhãn, ms/câu (ghi rõ đo từng câu hay cả lô, số luồng), byte/vector, thời gian
   dựng. Đo trên CPU, `OMP_NUM_THREADS` và `faiss.omp_set_num_threads` cùng một giá trị.
3. **Biên Pareto** bằng `pareto_front`; vẽ recall ANN@10 theo ms/câu và theo byte/vector, đánh dấu các điểm trên biên.
4. **Ba kịch bản** trong `REPORT.md`, mỗi kịch bản một cấu hình và lý do bằng số:
   - (a) laptop 8 GB RAM, corpus này, p95 dưới 20 ms;
   - (b) 10 triệu vector 1 024 chiều trên một máy 32 GB RAM, recall ANN@10 ít nhất 0.9;
   - (c) corpus này nhưng cần recall ANN@10 ít nhất 0.99 và cập nhật vài nghìn điều mỗi ngày.
5. Một đoạn ngắn: PQ tự viết so với `IndexPQ` của FAISS cùng `m` (recall, tốc độ), và giải thích chênh lệch.

## Tiêu chí đạt

- Test hàm pass (`uv run pytest ... -q`); `pq_search` trùng kNN trên vector giải nén.
- Bảng có đủ các nhóm cấu hình ở bước 2 với số đo thật và điều kiện đo ghi rõ.
- Biên Pareto đúng với bảng; hai biểu đồ có nhãn trục và đơn vị.
- Mỗi kịch bản có phép tính bộ nhớ ra con số (byte/vector nhân số vector cộng overhead) và chọn một điểm trên (hoặc gần)
  biên, nói rõ đánh đổi.
- Rubric chi tiết trong `SOLUTION.md` của bài (xem sau khi nộp).

## Gợi ý

### Gợi ý 1

Train codebook trên một mẫu (vài chục nghìn vector là đủ cho `k_s = 256`) chứ không cần cả corpus; với `m = 64` và
1 024 chiều, mỗi đoạn chỉ 16 chiều. Trong `pq_search`, bảng ADC có shape `(m, k_s)`; khoảng cách của cả corpus là một
phép fancy indexing `table[arange(m), codes]` rồi cộng theo hàng.

### Gợi ý 2

PQ chuẩn dùng L2 trên vector đơn vị: thứ tự theo L2 trùng thứ tự theo cosine của vector **gốc**, nhưng vector giải nén
không còn đơn vị. Recall của PQ thuần thường thấp; rescoring top-R bằng vector gốc (lưu trên đĩa, đọc theo id) là cách các
hệ thống thật lấy lại recall. Với kịch bản (b), tính trước: 10 triệu vector float32 1 024 chiều chiếm bao nhiêu GB?
