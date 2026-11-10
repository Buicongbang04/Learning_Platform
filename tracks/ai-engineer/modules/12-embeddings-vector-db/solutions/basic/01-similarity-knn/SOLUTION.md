# Lời giải: cosine, dot, L2 và kNN chính xác

## Cách làm

**`l2_normalize`.** Ép về `float32` bằng `np.asarray(x, dtype=np.float32)` (tạo bản mới nếu kiểu khác, nên không sửa đầu
vào), tính chuẩn theo trục cuối với `keepdims=True` để cùng một dòng code chạy cho mảng một và hai chiều, rồi chia cho
`np.where(norms == 0, 1, norms)`. Vector 0 chia cho 1 vẫn là 0, không thành `NaN`.

**`pairwise`.** `"dot"` là `q @ b.T`. `"cosine"` là chuẩn hoá hai phía rồi nhân ma trận (vector 0 cho cosine 0 nhờ
`l2_normalize`). `"l2"` dùng khai triển

$$
\lVert q - x\rVert^2 = \lVert q\rVert^2 + \lVert x\rVert^2 - 2\, q^\top x
$$

nên chỉ cần hai vector chuẩn bình phương và **một** phép nhân ma trận, không dựng mảng `(n_q, n_b, d)` (với 300 câu hỏi
× 61 425 vector × 1 024 chiều, mảng đó là 75 GB `float32`). Cuối cùng `np.maximum(sq, 0)`.

**`knn`.** Đổi mọi metric về "nhỏ hơn là tốt hơn" (giữ nguyên khoảng cách L2, đảo dấu điểm dot/cosine) rồi
`np.argsort(key, axis=1, kind="stable")[:, :k]`. Sort ổn định giữ chỉ số nhỏ trước khi bằng điểm; slicing tự xử lý
`k > n_base`.

**`ann_recall`.** Với mỗi cặp dòng, `len(set(a[:k]) & set(e[:k])) / k`, rồi trung bình.

## Vì sao phải kẹp về 0: sai số của khai triển trong `float32`

Khai triển là hiệu của hai số lớn gần bằng nhau khi hai vector gần nhau và có chuẩn lớn. Đo với 20 vector 64 chiều
toạ độ quanh `offset` (`.superpowers/scratch/logs/basic01_cancel.log`):

| offset | sai số lớn nhất trên đường chéo (đúng là 0) | giá trị nhỏ nhất | khoảng cách thật, trung vị |
| --- | --- | --- | --- |
| 0 | 6e-5 | -6e-5 | 124 |
| 100 | 0.375 | -0.25 | 127 |
| 1 000 | 40 | -24 | 125 |

Ở offset 1 000, sai số (cỡ 40) đã ngang một phần ba khoảng cách thật: thứ hạng theo L2 không còn đáng tin. `np.maximum`
chỉ chữa triệu chứng (giá trị âm, căn bậc hai ra `NaN`); thuốc thật là đừng để dữ liệu có chuẩn lớn lệch xa gốc toạ độ:
embedding đã chuẩn hoá (chuẩn 1) có sai số cỡ `1e-7`, và FAISS, các vector DB đều dùng đúng khai triển này.

## Ba metric và chuẩn hoá

- Trên vector đơn vị, $$\lVert a - b\rVert^2 = 2 - 2\cos(a, b)$$ là hàm giảm của cosine, và dot chính là cosine: ba metric
  cho **cùng thứ hạng** (test thứ 9 kiểm điều này). Đó là lý do chuẩn hoá một lần lúc index rồi dùng inner product là
  cách làm mặc định.
- Trên vector chưa chuẩn hoá thì không: dot ưu tiên vector dài (trong test, vector `[10, 10]` thắng dù lệch hướng 45°),
  L2 ưu tiên vector gần về vị trí, cosine chỉ xét hướng. Một vector DB đặt metric `l2` (mặc định của Chroma và LanceDB)
  trên embedding chưa chuẩn hoá sẽ trả kết quả khác cosine mà không báo lỗi gì.

## Recall của ANN khác Recall@k của retrieval

`ann_recall` so index xấp xỉ với kNN chính xác **trên cùng vector**: nó đo index, không đo embedding. Recall@k của module 13
so với tài liệu đúng theo nhãn: nó đo cả hệ thống. Một index có recall ANN 1.0 vẫn có Recall@10 theo nhãn chỉ bằng của kNN
chính xác (với `bge-m3` trên Zalo Legal là khoảng 0.9, xem bài Intermediate 02).

## Bẫy thường gặp

- `argsort(scores)[:, ::-1]` cho thứ tự giảm dần nhưng bằng điểm thì chỉ số **lớn** đứng trước.
- `np.argsort` mặc định (`quicksort`) không ổn định với mảng dài hơn 16 phần tử; test có 40 vector trùng nhau để bắt việc này.
- Chia cho `len(exact[i])` thay vì `k` trong `ann_recall`: sai khi ground truth có nhiều cột hơn `k`.
- Quên `np.maximum(..., 0)` rồi lấy căn: `NaN` lan vào thứ hạng và `argsort` đẩy `NaN` xuống cuối, không báo lỗi.
