---
title: Bốn vector store, một giao diện - FAISS, Chroma, Qdrant local, LanceDB
level: intermediate
services: []
files:
  - path: starter/vectordbs.ipynb
    note: distance_to_cosine, latency_summary, sql_quote, FaissStore, QdrantStore, LanceStore TODO (ChromaStore là mẫu)
  - path: tests/test_vectordbs.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/intermediate/02-vector-dbs/starter/vectordbs.ipynb
  - uv run pytest tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/intermediate/02-vector-dbs -q
---

## Mục tiêu

Viết adapter cho ba công cụ lưu và tìm vector theo cùng một hợp đồng (upsert, search có lọc, delete, count), rồi nạp cùng
61 425 vector `bge-m3` vào cả bốn và đo bằng số những thứ quyết định chọn công cụ: thời gian nạp, dung lượng đĩa, độ trễ
p50/p95, recall so với kNN chính xác, lọc metadata, xoá và mở lại. Làm xong bạn biết mỗi công cụ trả "khoảng cách" theo
quy ước nào, và vì sao bộ lọc phải nằm **trong** truy vấn.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Cần cache `data/raw/zalo-legal/cache/bge-m3.npy` do bài Intermediate 01 tạo. Các cell đo nạp 61 425 vector vào bốn store
trên đĩa (thư mục tạm, xoá ở cuối); cả notebook chạy khoảng 13 phút trên PC của track.

Mở `starter/vectordbs.ipynb`. Notebook mô tả chính xác hợp đồng chung và từng lớp; tóm tắt:

1. `distance_to_cosine(d, kind)`: đổi `cosine_similarity`, `cosine_distance`, `squared_l2`, `l2` về cosine (vector đơn vị).
   `latency_summary(ms)`: p50, p95, trung bình. `sql_quote(value)`: chuỗi SQL có escape nháy đơn.
2. `FaissStore`: `IndexIDMap2(IndexFlatIP)`, tự quản lý bảng uid và metadata, lọc bằng `IDSelectorBatch`, bỏ id `-1`.
3. `QdrantStore`: local mode, `Distance.COSINE`, id của point là UUID5 của uid, uid và metadata trong payload.
4. `LanceStore`: bảng Lance, thêm hoặc thay bằng `merge_insert`, metric cosine, lọc bằng SQL đã escape.

`ChromaStore` đã viết sẵn làm mẫu. Rồi chạy các cell `explore`: kiểm trên dữ liệu sinh, nạp và đo bốn store, thêm index
cho LanceDB và FAISS HNSW, lọc theo văn bản, post-filter, xoá và mở lại. Phần pgvector ở cuối là tuỳ chọn, cần Docker,
không chấm. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `distance_to_cosine` đúng cả bốn quy ước; `latency_summary` dùng `np.percentile` mặc định; `sql_quote` nhân đôi nháy đơn.
- Với cả bốn store: top-5 trùng kNN cosine chính xác, điểm trả về là cosine (sai số dưới `1e-4`), lọc bằng nhau đúng kể cả
  giá trị chứa nháy đơn, lọc không khớp gì trả danh sách rỗng, ít hơn `k` bản ghi khớp thì trả ít hơn (không có phần tử giả).
- `delete` làm giảm `count` và bản ghi không quay lại; `upsert` một uid đã có thay cả vector lẫn metadata, không nhân bản.
- Qdrant, LanceDB, Chroma ghi ra đĩa, mở lại đúng số bản ghi và vẫn nhận ra uid cũ khi upsert.

## Gợi ý

### Gợi ý 1

Với vector đơn vị, $$\lVert a - b\rVert^2 = 2 - 2\cos(a, b)$$ (mục 3 lý thuyết); ba quy ước còn lại suy ra từ đó. Trong
`FaissStore`, mọi thứ FAISS không biết (uid, metadata) nằm trong ba `dict` khai báo ở `__init__`; id số chỉ tăng.

### Gợi ý 2

Qdrant local mode từ chối id dạng chuỗi tuỳ ý nhưng nhận UUID; `uuid5` cho cùng UUID với cùng uid, nên upsert lần sau tự
thay point cũ. LanceDB: `merge_insert("uid").when_matched_update_all().when_not_matched_insert_all().execute(bảng)`; tên văn
bản luật có thể chứa nháy đơn, và một chuỗi SQL không escape là lỗi (hoặc lỗ hổng) chờ xảy ra.
