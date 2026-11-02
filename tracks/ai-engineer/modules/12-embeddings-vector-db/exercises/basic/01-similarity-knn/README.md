---
title: Cosine, dot, L2 và kNN chính xác bằng numpy
level: basic
services: []
files:
  - path: starter/similarity.py
    note: 4 hàm TODO
  - path: tests/test_similarity.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/basic/01-similarity-knn -q
---

## Mục tiêu

Tự viết lớp dưới cùng của mọi vector database: chuẩn hoá L2, ba độ đo (dot, cosine, L2), tìm k láng giềng gần nhất
**chính xác**, và thước đo dùng để chấm mọi index xấp xỉ ở các bài sau: recall của ANN so với kNN chính xác. Làm xong
bạn biết khi nào ba độ đo cho cùng thứ hạng, khi nào không, và vì sao kết quả "đúng" của một vector DB có thể sai chỉ
vì đặt nhầm metric.

## Đề bài

**Phần cứng:** CPU · ~40 phút

Trong `starter/similarity.py`, chỉ dùng numpy, viết:

1. `l2_normalize(x)`: chia mỗi vector (mỗi dòng nếu `x` hai chiều, hoặc chính nó nếu một chiều) cho chuẩn L2 của nó.
   Trả `float32`, không sửa mảng đầu vào. Vector toàn 0 giữ nguyên 0.
2. `pairwise(queries, base, metric)`: ma trận `(n_queries, n_base)` với `metric` là
   - `"dot"`: tích vô hướng $$q^\top x$$;
   - `"cosine"`: $$\frac{q^\top x}{\lVert q\rVert\,\lVert x\rVert}$$, vector 0 cho cosine 0;
   - `"l2"`: **bình phương** khoảng cách Euclid $$\lVert q - x\rVert^2$$, không bao giờ âm;
   - giá trị khác: `ValueError`.

   Với hàng nghìn vector, đừng dựng mảng ba chiều `(n_queries, n_base, d)`: mục 3 lý thuyết có cách tính bằng một phép
   nhân ma trận.
3. `knn(queries, base, k, metric)`: mảng số nguyên `(n_queries, min(k, n_base))`, mỗi dòng là chỉ số các vector **tốt
   nhất trước**: điểm lớn nhất với `dot` và `cosine`, khoảng cách nhỏ nhất với `l2`. Bằng điểm thì chỉ số nhỏ trước.
4. `ann_recall(approx, exact, k)`: với mỗi query, tỉ lệ phần tử của `k` cột đầu của `approx` có mặt trong `k` cột đầu
   của `exact`; trả trung bình theo query (một `float`). Đây là **recall của ANN** ở mục 5 lý thuyết, khác với Recall@k
   của retrieval (so với tài liệu đúng theo nhãn) mà module 13 dùng.

## Tiêu chí đạt

- `l2_normalize` trả `float32`, không có `NaN` với vector 0, giữ hình dạng một chiều.
- `pairwise` khớp giá trị tính tay của ba độ đo; `l2` không âm kể cả với vector có toạ độ cỡ 1 000 trong `float32`;
  với vector đơn vị, `l2` bằng $$2 - 2\cos$$.
- Trên một ví dụ dữ liệu chưa chuẩn hoá, ba độ đo chọn ba láng giềng khác nhau; sau khi chuẩn hoá, ba độ đo cho cùng
  thứ hạng.
- `knn` giữ chỉ số nhỏ trước khi bằng điểm (kể cả 40 vector trùng nhau), trả `n_base` cột khi `k > n_base`.
- `ann_recall` chỉ so `k` cột đầu, không quan tâm thứ tự trong top-k, chia cho `k`.

## Gợi ý

### Gợi ý 1

Khai triển $$\lVert q - x\rVert^2$$ thành ba số hạng: hai số hạng chỉ phụ thuộc một phía tính một lần cho mỗi dòng, số
hạng còn lại là một phép nhân ma trận. Trong `float32`, hiệu của hai số lớn gần bằng nhau có thể ra số âm nhỏ.

### Gợi ý 2

`np.argsort` mặc định không ổn định với mảng dài; xem tham số `kind`. Đảo dấu điểm trước khi sort để có thứ tự giảm
dần mà vẫn giữ chỉ số nhỏ trước. Với `ann_recall`, phép giao của hai `set` là đủ.
