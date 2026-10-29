# Hướng làm: chọn solver khi ma trận xấu điều kiện

## Cài đặt

- `solve_normal`: `np.linalg.solve(X.T @ X, X.T @ y)`.
- `solve_qr`: `Q, R = np.linalg.qr(X)` (reduced), rồi `scipy.linalg.solve_triangular(R, Q.T @ y)`.
  Không tạo $$X^\top X$$, nên condition number của hệ phải giải là $$\kappa(R) = \kappa(X)$$.
- `solve_svd`: `U, s, Vt = np.linalg.svd(X, full_matrices=False)`, giữ `s > rcond * s[0]`,
  `w = Vt[keep].T @ ((U[:, keep].T @ y) / s[keep])`. Bỏ các σ nhỏ là "truncated SVD": nghiệm min-norm.
- `ridge`: `np.linalg.solve(X.T @ X + lam * D, X.T @ y)` với `D = diag(0, 1, …, 1)`.
- `scaled_condition_number`: chia mỗi cột cho chuẩn L2 rồi lấy $$\sigma_{\max}/\sigma_{\min}$$.

## Kết quả tham chiếu

**Vandermonde trên [0, 1], 200 điểm, `y = X @ w_true`** (trung vị sai số tương đối của w trên 10 seed):

| Bậc | κ(X) | Normal equation | QR | SVD |
| --- | --- | --- | --- | --- |
| 4 | 6.8 · 10² | 9.5 · 10⁻¹² | 1.0 · 10⁻¹⁴ | 7.9 · 10⁻¹⁵ |
| 6 | 2.1 · 10⁴ | 4.1 · 10⁻⁹ | 5.3 · 10⁻¹³ | 4.7 · 10⁻¹³ |
| 8 | 6.8 · 10⁵ | 3.6 · 10⁻⁶ | 6.8 · 10⁻¹² | 6.8 · 10⁻¹² |
| 10 | 2.2 · 10⁷ | 2.1 · 10⁻³ | 2.8 · 10⁻¹⁰ | 4.0 · 10⁻¹⁰ |
| 12 | 7.1 · 10⁸ | 3.8 · 10¹ | 3.7 · 10⁻⁹ | 1.9 · 10⁻⁹ |

Sai số normal equation tăng theo $$\kappa^2\varepsilon$$, QR/SVD theo $$\kappa\varepsilon$$. Ở bậc 12 normal equation
cho nghiệm sai hơn cả việc đoán w = 0.

**Olist, đa thức trên đơn vị gốc** `[1, gram, cm³, gram², cm⁶, gram·cm³]` (51 216 item train):
κ(X) ≈ 5.8 · 10⁹, vậy mà normal equation chỉ lệch nghiệm `lstsq` khoảng 8.5 · 10⁻¹¹ (tương đối), MSE như
nhau (105.04). Lý do: `scaled_condition_number` chỉ khoảng 12.9; gần như toàn bộ ill-conditioning đến từ
**thang đo** của cột, mà phép khử Gauss có pivot xử lý được phần lớn. Chuẩn hoá cột đưa κ về 12.2.
Đây là điểm phân biệt người hiểu bản chất: condition number lớn chưa chắc là bệnh, phải xem nó còn
lớn sau khi cân bằng cột không.

**Olist, thêm peso cubado** `[1, kg, lít, lít/6]`: hai cột cuối tỉ lệ nhau, singular value nhỏ nhất
2.4 · 10⁻¹³, κ ≈ 2.9 · 10¹⁶ và scaled κ ≈ 1.3 · 10¹⁶: bệnh thật.

| Solver | Hệ số (intercept, kg, lít, peso cubado) | MSE train |
| --- | --- | --- |
| Normal equation | 13.25, 1.459, −1.193, 8.232 | 111.864 |
| `np.linalg.qr` (không pivot) | 13.31, 1.441, −7.3 · 10¹², 4.4 · 10¹³ | 111.901 |
| SVD (rcond 1e-10) / `lstsq` | 13.25, 1.459, 0.1741, 0.0290 | 111.864 |
| Ridge λ = 1e-3 | 13.25, 1.459, 0.1741, 0.0290 | 111.864 |

Dự đoán gần như không đổi (mọi cách đều có $$w_{\text{lít}} + w_{\text{cubado}}/6 \approx 0.179$$), nhưng **hệ số
mất ý nghĩa**: normal equation nói "thêm một lít làm *giảm* phí 1.19 BRL", QR cho số 10¹³. Ai đọc hệ số để
ra quyết định (giá ship cho seller) sẽ sai. SVD cho nghiệm min-norm, chia đều theo tỉ lệ cột; ridge
cho gần như cùng kết quả và ổn định.

Thời gian (n = 51 216): d = 6, normal 0.37 ms, QR 2.8 ms, SVD 3.4 ms; d = 100 ngẫu nhiên, normal 63 ms,
QR 695 ms, SVD 816 ms. Normal equation nhanh hơn khoảng 10 lần: đó là lý do nó vẫn được dùng khi bài
toán đã chuẩn hoá tốt, và khi phải cộng dồn $$X^\top X$$ trên dữ liệu phân tán.

## Các quyết định cần cân nhắc

- **Sửa feature trước, đổi solver sau.** Peso cubado là thông tin trùng lặp; bỏ nó (hoặc giữ một
  trong hai) tốt hơn mọi solver. Kiểm tra tự động trong pipeline: scaled condition number, hoặc VIF,
  cảnh báo khi vượt ngưỡng (vd. 10³).
- **Chuẩn hoá là mặc định** cho mọi thứ dùng gradient hoặc regularization.
- **Solver mặc định**: `lstsq` / QR có pivot cho bài toán nhỏ cần độ chính xác; normal equation khi
  đã chuẩn hoá và cần tốc độ hoặc dữ liệu phân tán; ridge khi feature tương quan và cần hệ số ổn định.
- **Chọn λ cho ridge** bằng validation theo thời gian, không phải theo condition number. Trên Olist đa
  thức chuẩn hoá, λ tới 100 gần như không đổi R² test (0.3528 so với 0.3532), λ = 10 000 làm R² test giảm
  còn 0.337: ridge ở đây chỉ để ổn định, không cải thiện dự đoán.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Cài đặt đúng | 20 | Test pass; QR và SVD không tạo $$X^\top X$$; ridge không phạt intercept |
| Thí nghiệm có kiểm soát | 15 | Có bài toán biết đáp án, κ tăng dần, sai số từng solver; giải thích được $$\kappa^2$$ so với $$\kappa$$ |
| Phân biệt nguyên nhân | 20 | Dùng scaled condition number (hoặc tương đương) để chỉ ra Olist đa thức chỉ xấu do đơn vị, peso cubado xấu thật |
| Hậu quả kinh doanh | 15 | Chỉ ra dự đoán gần như không đổi nhưng hệ số vô nghĩa; nói ai bị ảnh hưởng |
| Ridge | 10 | Ảnh hưởng tới κ và hệ số; chọn λ bằng validation; nêu đánh đổi bias |
| Khuyến nghị cho team | 15 | Quy tắc cụ thể: chuẩn hoá, solver mặc định, kiểm tra tự động, khi nào normal equation vẫn đúng |
| Trình bày | 5 | Ngắn, có bảng số thật, người đọc làm theo được |

Từ 70 điểm: đủ để đưa vào tài liệu kỹ thuật của team.
