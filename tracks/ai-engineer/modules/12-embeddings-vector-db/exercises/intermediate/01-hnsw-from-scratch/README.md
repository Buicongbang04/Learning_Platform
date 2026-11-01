---
title: Tự viết HNSW, đo với IVF và FAISS trên embedding Zalo Legal
level: intermediate
services: []
files:
  - path: starter/hnsw.ipynb
    note: random_level, 4 phương thức của HNSW TODO, cộng assign, kmeans, IVFIndex dán từ Basic 02
  - path: tests/test_hnsw.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - ollama pull bge-m3
  - uv run jupyter lab tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/intermediate/01-hnsw-from-scratch/starter/hnsw.ipynb
  - uv run pytest tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/intermediate/01-hnsw-from-scratch -q
---

## Mục tiêu

Cài HNSW (Malkov & Yashunin) từ đầu: tầng ngẫu nhiên, beam search trên một tầng, chọn láng giềng bằng heuristic, chèn
nút với tỉa bậc, tìm kiếm tham lam từ tầng trên xuống. Rồi đo nó trên vector `bge-m3` thật cạnh IVF của bài Basic 02 và
FAISS, theo ba trục recall của ANN, số phép tính khoảng cách và thời gian. Làm xong bạn đọc được mọi tham số `M`,
`ef_construction`, `ef_search` của Qdrant, pgvector, Chroma như đọc code của chính mình.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Ngoài thời gian làm bài: lần đầu notebook embed cả corpus qua Ollama, khoảng 45 phút trên laptop của track (GPU 4GB),
và cache ở `data/raw/zalo-legal/cache/bge-m3.npy` (cùng `bge-m3.ids.json`, đúng định dạng module 13 dùng, nên module 13 không
phải embed lại). Khi đã có cache, cả notebook chạy khoảng 6 phút trên PC của track, phần lớn là dựng HNSW bằng Python trên 20 000 vector.

Mở `starter/hnsw.ipynb`. Notebook mô tả chính xác từng hàm; tóm tắt:

1. `random_level(rng, m_l)`: tầng cao nhất của nút mới, $$\lfloor -\ln(1 - u)\, m_L \rfloor$$, đúng một lần `rng.random()`.
2. Lớp `HNSW` (vector đã chuẩn hoá, khoảng cách $$1 - q^\top x$$ qua phương thức `dist` có sẵn):
   - `search_layer(q, entry_points, ef, layer)`: beam search trên một tầng, trả tối đa `ef` cặp (khoảng cách, id) tăng dần.
   - `select_neighbors(candidates, m)`: `m` gần nhất, hoặc heuristic giữ ứng viên gần nút gốc hơn mọi láng giềng đã chọn.
   - `_insert(v)`: chèn một nút, nối hai chiều, tỉa nút vượt bậc tối đa (`M` ở tầng trên, `2M` ở tầng 0).
   - `search(q, k, ef)`: tham lam ở các tầng trên, beam search `max(ef, k)` ở tầng 0.
3. Dán `assign`, `kmeans`, `IVFIndex` của bài Basic 02.

Rồi chạy các cell `explore`: kiểm trên dữ liệu sinh có cụm, embed corpus (hoặc đọc cache), đo HNSW và IVF tự viết trên
20 000 điều đầu với 300 câu hỏi ghim (300 query-id đầu của `qrels/test.jsonl`), đo FAISS `IndexHNSWFlat` và `IndexIVFFlat`
trên 20 000 điều và trên cả 61 425 điều, và so heuristic với cách chọn `m` gần nhất. Sau đó làm phần trắc nghiệm của bài
trong app.

## Tiêu chí đạt

- `random_level` đúng công thức, mỗi lần gọi lấy đúng một số ngẫu nhiên, khoảng 1/16 số nút lên tầng 1 khi `M = 16`.
- `search_layer`: với `ef = 1` dừng ở cực tiểu địa phương trên đồ thị dựng tay, với `ef = 2` thoát ra và tìm đúng; mỗi nút
  chỉ tính khoảng cách một lần; nhiều điểm vào.
- `select_neighbors` khớp ví dụ tính tay của cả hai chế độ.
- Đồ thị dựng ra: tầng theo đúng `rng`, mọi nút có mặt ở mọi tầng của nó, bậc không vượt giới hạn, không tự nối, entry
  point là nút đầu tiên đạt tầng cao nhất, nút bị tràn bậc được tỉa bằng `select_neighbors` nhìn từ chính nó.
- `search` đi xuống qua tầng trên (đồ thị hai thành phần rời ở tầng 0), dùng `max(ef, k)`; trên 2 000 điểm có 20 cụm,
  recall của ANN@10 ít nhất 0.95 với `ef = 40` mà tính dưới 25% số khoảng cách của quét hết.
- Test dữ liệu thật (tự skip nếu chưa có cache): HNSW trên 1 500 vector `bge-m3` đầu đạt recall ANN@10 ít nhất 0.9.

## Gợi ý

### Gợi ý 1

`heapq` của Python là min-heap. Cho tập `best` cần lấy phần tử **xa nhất**, đẩy cặp (khoảng cách âm, id). Điều kiện dừng
của beam search so ứng viên gần nhất còn lại với phần tử xa nhất trong `best`, không so với `ef`.

### Gợi ý 2

Trong `_insert`, `search_layer` cho cả hai việc: tìm điểm vào ở tầng trên (`ef = 1`) và tìm ứng viên láng giềng ở các tầng
của nút mới (`ef = ef_construction`). Khi một láng giềng `e` vượt bậc, sắp danh sách của `e` theo khoảng cách tới `e`
(không phải tới nút mới) rồi chọn lại bằng `select_neighbors`.
