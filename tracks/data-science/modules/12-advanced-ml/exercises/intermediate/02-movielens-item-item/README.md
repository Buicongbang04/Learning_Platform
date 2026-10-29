---
title: Item-item collaborative filtering và precision@k trên MovieLens
level: intermediate
services: []
files:
  - path: starter/itemcf.ipynb
    note: 4 hàm TODO + nhận xét
  - path: tests/test_itemcf.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py movielens
  - uv run jupyter lab tracks/data-science/modules/12-advanced-ml/exercises/intermediate/02-movielens-item-item/starter/itemcf.ipynb
  - uv run pytest tracks/data-science/modules/12-advanced-ml/exercises/intermediate/02-movielens-item-item -q
---

## Mục tiêu

Dựng trọn một vòng recommender offline trên dữ liệu thật: chia train/test theo thời gian, một
baseline phổ biến, item-item CF chạy được trên ma trận thưa mà không tạo ma trận độ giống đầy đủ,
và đánh giá bằng precision@k, recall@k, coverage. Hiểu vì sao baseline popularity khó thắng hơn
bạn nghĩ.

## Đề bài

MovieLens latest-small (610 user, 9 724 phim, 100 836 rating). Mở `starter/itemcf.ipynb`:

1. `split_last_fraction(ratings, frac=0.2)`: mỗi user, $$\lceil 0.2 \cdot n_u \rceil$$ rating mới nhất
   (theo `timestamp`, bằng nhau thì theo `movieId`) vào test.
2. `popularity_recs(train, users, k=10)`: phim nhiều rating nhất mà user chưa xem; user lạ nhận danh
   sách phổ biến.
3. `item_item_recs(train, users, k=10)`: cosine trên ma trận user × phim nhị phân, điểm của phim là
   tổng cosine với các phim trong lịch sử; không gợi ý phim đã xem; user lạ nhận danh sách rỗng.
4. `evaluate(recs, test, k=10) -> {"precision", "recall", "coverage"}`.
5. Viết nhận xét ở cell cuối: so hai cách, và chọn cách nào cho user mới / user lâu năm.

Quy ước thứ tự: điểm bằng nhau thì `movieId` nhỏ đứng trước.

## Tiêu chí đạt

- Split đúng số dòng mỗi user và đúng quy tắc phá hoà.
- Popularity bỏ phim đã xem và phá hoà đúng.
- Item-item cho cùng top-k với cách tính bằng ma trận dày trên dữ liệu ngẫu nhiên (3 seed), không
  gợi ý trùng hay phim đã xem.
- `evaluate` lấy trung bình theo user của test, cắt danh sách ở k.
- Trên MovieLens thật: train 80 419 / test 20 417 dòng; precision@10 popularity ≈ 0.0748, item-item
  ≈ 0.0970; item-item có recall cao hơn và coverage gấp hơn 4 lần.

## Gợi ý

### Gợi ý 1

Mã hoá id thành chỉ số bằng `np.searchsorted` trên mảng id đã sort; dựng
`scipy.sparse.csr_matrix((np.ones(n), (rows, cols)))`. Chuẩn hoá cột:
`sp.csr_matrix(X.multiply(1 / np.sqrt(X.sum(axis=0))))` (với ma trận 0/1, độ dài cột là căn của
tổng cột).

### Gợi ý 2

Với user có lịch sử `hist` (chỉ số cột), `v = Xn[:, hist].sum(axis=1)` là vector theo user, và
`Xn.T @ v` cho điểm của mọi phim trong một phép nhân. Gán `-np.inf` cho phim đã xem; xếp hạng có
phá hoà bằng `np.lexsort((items, -score))` (khoá cuối cùng là khoá chính).
