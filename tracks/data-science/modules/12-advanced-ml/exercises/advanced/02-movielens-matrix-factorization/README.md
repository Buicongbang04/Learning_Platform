---
title: Matrix factorization, cold start và chọn recommender cho trang chủ
level: advanced
services: []
files:
  - path: starter/mf.py
    note: Lớp MatrixFactorization (3 phương thức TODO)
  - path: starter/REPORT.md
    note: Khuyến nghị cho PM và Engineering Manager
  - path: tests/test_mf.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py movielens
  - uv run pytest tracks/data-science/modules/12-advanced-ml/exercises/advanced/02-movielens-matrix-factorization -q
---

## Mục tiêu

Tự cài matrix factorization có bias, xử lý cold start một cách có nguyên tắc, rồi so ba họ
recommender (popularity, item-item, MF) trên cùng một split theo thời gian để đưa ra khuyến nghị
sản phẩm. Phát hiện quan trọng bạn cần tự tìm ra: model tốt hơn theo RMSE chưa chắc gợi ý top-10
tốt hơn.

## Đề bài

1. Trong `starter/mf.py`, cài `MatrixFactorization(n_factors, reg, n_iters, seed)` với mô hình

   $$
   \hat r_{ui} = \mu + b_u + b_i + p_u^\top q_i
   $$

   trong đó $$\mu$$ là trung bình rating của train. Bạn chọn ALS hoặc SGD, và đặt mặc định của `reg`,
   `n_iters` hợp với cách học của mình.
   - `fit(ratings)` (cột `userId`, `movieId`, `rating`) trả `self`; khởi tạo bằng
     `np.random.default_rng(seed)`.
   - `predict(users, items)`: cold start lấy $$b_u = 0, p_u = 0$$ cho user lạ, $$b_i = 0, q_i = 0$$
     cho phim lạ.
   - `recommend(user, k=10, exclude=())`: k phim của train có dự đoán cao nhất, bỏ `exclude`.
2. Trên MovieLens, cùng split với bài Intermediate 02 (20% rating mới nhất của mỗi user): RMSE so
   với baseline chỉ bias; precision@10, recall@10, coverage so với popularity và item-item (dùng lại
   hàm của bài Intermediate 02 và Basic 03). Tune `n_factors`, `reg` trên một tập validation tách từ
   train, không trên test.
3. Đo cold start: bao nhiêu phần trăm rating trong test thuộc phim chưa có trong train?
4. Viết `starter/REPORT.md` theo khung có sẵn.

## Tiêu chí đạt

- Trên dữ liệu mô phỏng hạng thấp: RMSE dưới 85% của baseline chỉ bias và dưới 0.6 (3 seed), với
  `n_factors=10` và các mặc định của bạn.
- Cùng seed cho cùng dự đoán.
- User lạ + phim lạ dự đoán đúng $$\mu$$; dự đoán cho user lạ xếp phim theo chất lượng (tương quan với
  rating trung bình của phim trên 0.8).
- `recommend` trả k phim khác nhau, chưa xem, có trong train, đúng thứ tự, và không bỏ sót phim
  điểm cao hơn.
- MovieLens thật với tham số mặc định: RMSE dưới 0.92.
- `REPORT.md` không còn TODO, ít nhất 300 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

ALS có bias: khi cố định $$Q$$ và $$b_i$$, bài toán cho mỗi user là ridge regression của
$$r_{ui} - \mu - b_i$$ theo thiết kế $$[q_i, 1]$$, nghiệm là $$[p_u, b_u]$$. Làm tương tự cho từng phim.
Dùng `scipy.sparse.csr_matrix` để lấy nhanh các phim của mỗi user (`indptr`, `indices`, `data`).

### Gợi ý 2

RMSE đo độ chính xác trên **các cặp user đã chọn xem**; top-10 cần xếp hạng trên **mọi** phim chưa
xem, kể cả những phim user không bao giờ xem. Một MF tối ưu RMSE có thể đẩy lên đầu những phim ít
người xem nhưng điểm trung bình cao. So coverage và độ phổ biến của danh sách gợi ý để thấy điều đó.
