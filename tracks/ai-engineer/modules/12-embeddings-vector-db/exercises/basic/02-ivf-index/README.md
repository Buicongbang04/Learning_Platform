---
title: Tự viết IVF index (k-means + nprobe)
level: basic
services: []
files:
  - path: starter/ivf.py
    note: assign, kmeans và 3 phương thức của IVFIndex TODO
  - path: tests/test_ivf.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/basic/02-ivf-index -q
---

## Mục tiêu

Tự cài index ANN đơn giản nhất mà FAISS, Milvus, pgvector (`ivfflat`) đều có: chia không gian bằng k-means, mỗi cụm
một danh sách (inverted list), lúc tìm chỉ quét `nprobe` cụm gần query nhất. Làm xong bạn đo được bằng chính code của
mình đánh đổi "quét ít hơn, sót nhiều hơn" mà tham số `nprobe` điều khiển.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Trong `starter/ivf.py`, chỉ dùng numpy. Mọi khoảng cách là **bình phương khoảng cách Euclid**, tính bằng hàm có sẵn
`sq_dists(x, centroids)`. Với vector đã chuẩn hoá L2 (như embedding của module này), thứ tự theo L2 trùng thứ tự theo
cosine (mục 3 lý thuyết).

1. `assign(x, centroids)`: chỉ số centroid gần nhất cho mỗi dòng, bằng khoảng cách thì chỉ số nhỏ.
2. `kmeans(x, n_clusters, n_iter=20, seed=0)`: Lloyd k-means.
   - Khởi tạo **đúng** như sau để kết quả tái lập: `rng = np.random.default_rng(seed)`, centroid ban đầu là
     `x[rng.choice(len(x), n_clusters, replace=False)]`.
   - Mỗi vòng (chạy đúng `n_iter` vòng, `n_iter=0` trả luôn centroid khởi tạo): gán mọi điểm vào centroid gần nhất,
     rồi đặt mỗi centroid bằng trung bình các điểm được gán. Cụm không có điểm nào giữ centroid cũ.
   - Trả `float32` `(n_clusters, d)`.
3. `IVFIndex(nlist, n_iter=20, seed=0)` với các thuộc tính đã khai báo trong `__init__`:
   - `train(x)`: học `centroids` bằng `kmeans(x, nlist, n_iter, seed)`, tạo `nlist` danh sách rỗng.
   - `add(x)`: thêm vector vào `vectors`; id là số thứ tự toàn cục (lần `add` thứ hai nối tiếp sau lần đầu). Mỗi id vào
     danh sách `lists[c]` của centroid gần nhất, mỗi danh sách là mảng id tăng dần.
   - `search(q, k, nprobe=1)`: chọn `nprobe` centroid gần `q` nhất (bằng khoảng cách thì chỉ số nhỏ trước), tính khoảng
     cách tới **mọi** vector trong các danh sách đó, trả `(ids, n_scanned)`: `ids` là list `int` của tối đa `k` vector gần
     nhất, khoảng cách tăng dần, bằng nhau thì id nhỏ trước; `n_scanned` là số vector đã tính khoảng cách.

## Tiêu chí đạt

- `kmeans` khởi tạo đúng quy tắc, tìm lại 4 cụm tách biệt, tổng bình phương khoảng cách tới centroid không tăng theo
  số vòng, không ra `NaN` khi có cụm rỗng.
- Mỗi id nằm trong đúng một danh sách, đúng danh sách của centroid gần nhất, kể cả khi `add` hai lần.
- `nprobe = nlist` cho kết quả trùng kNN chính xác; `n_scanned` bằng tổng kích thước các danh sách được quét; chỉ trả id
  thuộc các danh sách đó; bằng khoảng cách thì id nhỏ trước dù nằm ở danh sách khác.
- Trên 2 000 vector ngẫu nhiên, `nlist = 32`: recall của ANN tăng dần theo `nprobe` và bằng 1 khi quét hết; `nprobe = 1`
  chỉ quét dưới 15% dữ liệu.

## Gợi ý

### Gợi ý 1

`assign` là một dòng trên kết quả của `sq_dists`. Trong `kmeans`, cập nhật centroid theo từng cụm bằng mặt nạ
`labels == c`; kiểm số phần tử trước khi lấy trung bình.

### Gợi ý 2

Ở `search`, ghép các danh sách được probe thành một mảng ứng viên. Muốn "bằng khoảng cách thì id nhỏ trước" bằng một
sort ổn định, thứ tự ứng viên **trước khi** sort theo khoảng cách phải là thứ tự id.
