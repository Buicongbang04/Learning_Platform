---
title: PCA bằng SVD trên catalog sản phẩm Olist
level: intermediate
services: []
files:
  - path: starter/pca_products.ipynb
    note: 5 hàm TODO + phần nhận xét
  - path: tests/test_pca.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/01-math-for-ml/exercises/intermediate/03-pca-svd/starter/pca_products.ipynb
  - uv run pytest tracks/data-science/modules/01-math-for-ml/exercises/intermediate/03-pca-svd -q
---

## Mục tiêu

Tự viết PCA bằng SVD, chứng minh bằng số rằng nó trùng với `sklearn` và với eigen decomposition
của ma trận covariance, rồi đọc ý nghĩa các thành phần chính trên 32 340 sản phẩm Olist thật.

## Đề bài

Mở `starter/pca_products.ipynb`:

1. `prepare_product_matrix(products)`: 7 cột số của sản phẩm (khối lượng, dài, cao, rộng, số ảnh,
   độ dài tên, độ dài mô tả), bỏ dòng thiếu, `log1p`, chuẩn hoá từng cột (`ddof=0`).
2. `pca_svd(X, k)`: dict gồm `components`, `explained_variance` ($$\sigma_i^2/(n-1)$$),
   `explained_variance_ratio` (chia cho tổng mọi thành phần), `scores`, `mean`; quy ước dấu: phần tử
   có trị tuyệt đối lớn nhất của mỗi thành phần là số dương.
3. `reconstruct(pca)` và `n_components_for(evr, threshold)`.
4. Chạy các cell `explore`, viết nhận xét: PC1, PC2 nghĩa là gì; cần bao nhiêu thành phần; chuẩn
   hoá thay đổi gì; khi nào dùng PCA với dữ liệu này.

## Tiêu chí đạt

- Khớp `sklearn.decomposition.PCA` (variance, tỉ lệ, thành phần và score tới dấu) trên 3 seed.
- Thành phần chính trực chuẩn và là eigenvector của ma trận covariance: $$Cv = \lambda v$$.
- Tái tạo đủ k = d thì chính xác; sai số tái tạo giảm dần theo k và bằng tổng variance bị bỏ.
- Trên Olist thật: 32 340 × 7; hai thành phần đầu giải thích 35.89% và 17.64%; cần 5 thành phần cho
  90%; PC1 có loading lớn trên 4 cột kích thước, gần 0 trên 3 cột còn lại.

## Gợi ý

### Gợi ý 1

`np.linalg.svd(Xc, full_matrices=False)` trả `U, s, Vt`. Với n = 32 340 và d = 7, `full_matrices=True`
sẽ tạo `U` cỡ 32 340 × 32 340 (khoảng 8 GB). Luôn dùng SVD rút gọn.

### Gợi ý 2

Đổi dấu: `idx = np.argmax(np.abs(Vt), axis=1)`, `signs = np.sign(Vt[np.arange(len(Vt)), idx])`,
`Vt *= signs[:, None]`. Score tính sau khi đổi dấu thì tự đúng dấu. Với `n_components_for`, so
`np.cumsum(evr) >= threshold` có thể hụt ở 1.0 vì sai số làm tròn: trừ một lượng rất nhỏ.
