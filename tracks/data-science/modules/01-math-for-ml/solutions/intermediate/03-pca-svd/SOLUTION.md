# Lời giải: PCA bằng SVD trên catalog sản phẩm Olist

Notebook lời giải: `pca_products.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Vì sao SVD

Covariance của dữ liệu đã trừ trung bình là $$C = \frac{1}{n-1}X_c^\top X_c$$. Thay $$X_c = U\Sigma V^\top$$:

$$
C = \frac{1}{n-1}V\Sigma U^\top U \Sigma V^\top = V\,\frac{\Sigma^2}{n-1}\,V^\top
$$

Đây chính là eigen decomposition của $$C$$: cột của $$V$$ là eigenvector (thành phần chính), trị riêng là
$$\sigma_i^2/(n-1)$$. Làm SVD trực tiếp trên $$X_c$$ thay vì eigen trên $$C$$ tránh việc bình phương condition
number (cùng lý do QR tốt hơn normal equation), và là cách `sklearn` làm. Notebook in hai cách cạnh
nhau: eigenvalue của covariance và $$\sigma^2/(n-1)$$ trùng nhau tới 4 chữ số.

Dấu của eigenvector là tuỳ ý (nếu $$v$$ là eigenvector thì $$-v$$ cũng vậy), nên mọi so sánh với thư viện
phải "tới dấu". Quy ước dấu cố định giúp kết quả ổn định giữa các lần chạy, quan trọng khi lưu PCA
vào pipeline.

## Kết quả trên Olist thật

32 951 sản phẩm, 611 thiếu ít nhất một cột, còn 32 340.

| | PC1 | PC2 | PC3 | PC4 | PC5 | PC6 | PC7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Tỉ lệ variance | 35.89% | 17.64% | 14.06% | 12.42% | 10.35% | 5.65% | 4.00% |
| Cộng dồn | 35.89% | 53.53% | 67.58% | 80.00% | 90.36% | 96.00% | 100% |

Loadings: PC1 ≈ (0.56, 0.50, 0.40, 0.52, 0.04, 0.09, 0.06) trên (khối lượng, dài, cao, rộng, số ảnh,
độ dài tên, độ dài mô tả): **kích thước**. PC2 ≈ (−0.01, −0.03, −0.09, −0.11, 0.60, 0.55, 0.56):
**độ chăm chút listing**.

Cần 5 / 7 thành phần cho 90% variance. PCA nén kém ở đây vì ba cột văn bản/ảnh gần như độc lập với
nhau và với kích thước (mọi tương quan có trị tuyệt đối dưới 0.14). Chỉ khối kích thước (tương quan 0.23 – 0.62) là nén
được. Không chuẩn hoá thì PC1 "giải thích" 60.3% nhưng gần như chỉ là khối lượng (loading 0.91), vì
log khối lượng có độ lệch chuẩn 1.35 so với 0.45 của chiều dài.

## Khi nào dùng PCA

| Dùng | Không dùng |
| --- | --- |
| Feature tương quan mạnh, nhiều chiều (pixel, embedding, cảm biến) | Cần giải thích từng feature gốc cho kinh doanh |
| Trực quan hoá 2D/3D | Quan hệ phi tuyến (dùng UMAP / t-SNE để nhìn, autoencoder để nén) |
| Giảm nhiễu, khử đa cộng tuyến trước hồi quy | Feature quan trọng cho target nhưng variance nhỏ: PCA không nhìn target nên có thể vứt nó đi |
| Nén để tăng tốc model chậm | Model cây (LightGBM) trên dữ liệu bảng: thường không cần và còn làm mất khả năng tách theo từng feature |

## Sai lầm hay gặp

- Fit PCA (và scaler) trên toàn bộ dữ liệu rồi mới chia train/test.
- Không chuẩn hoá khi feature khác đơn vị.
- `np.linalg.svd(X)` với `full_matrices=True` trên dữ liệu nhiều dòng: tràn bộ nhớ.
- Chia variance cho tổng của k thành phần đầu thay vì tổng mọi thành phần: tỉ lệ luôn cộng lại 100%.
