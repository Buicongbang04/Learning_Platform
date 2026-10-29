# Lời giải: tự viết CUPED

## Cách làm

Cả năm hàm xoay quanh một phép biến đổi:

$$
Y_{\text{cuped}} = Y - \theta\,(X - \bar X), \qquad \theta = \frac{\mathrm{cov}(Y, X)}{\mathrm{var}(X)}
$$

- `cuped_theta` dùng `np.cov(y, x)[0, 1] / np.var(x, ddof=1)`: cả tử và mẫu cùng ddof=1.
- `cuped_adjust` trừ $$\theta(X - \bar X)$$, không trừ $$\theta X$$: trừ phần đã căn giữa để mean của
  metric giữ nguyên, báo cáo vẫn đọc được bằng đơn vị gốc.
- `cuped_effect` tính `theta` **một lần trên dữ liệu gộp**, rồi áp Welch cho cả bản gốc và bản điều
  chỉnh. Hàm phụ `_diff_se` dùng chung cho hai bản để chắc chắn so sánh cùng một công thức.
- `n_after_cuped` trừ `1e-9` trước khi `ceil`: `10000 * (1 - 0.9**2)` trong dấu phẩy động là
  `1899.9999999999995`, không trừ cũng ra 1900, nhưng có những cặp số cho ra `x.0000000001` và bị
  làm tròn lên thừa một đơn vị.

## Vì sao không lệch

$$X$$ đo trước khi random, nên $$\mathbb{E}[\bar X_T] = \mathbb{E}[\bar X_C]$$. Hiệu sau điều chỉnh là
$$(\bar Y_T - \bar Y_C) - \theta(\bar X_T - \bar X_C)$$: số hạng thứ hai có kỳ vọng 0, chỉ "trừ bớt
xui rủi" khi một nhánh tình cờ nhận nhiều user chi tiêu cao hơn. Đó là lý do test mô phỏng thấy
trung bình ước lượng CUPED vẫn quanh 1.0, còn độ lệch chuẩn giảm khoảng 40%.

Khi $$X$$ đo **sau** can thiệp (test cuối), $$\bar X_T - \bar X_C$$ chứa chính tác động, và CUPED trừ
mất nó. Trong thực tế lỗi này đến từ việc chọn cửa sổ "trước thí nghiệm" chồng lên ngày bật thí
nghiệm, hoặc dùng một feature bị treatment làm thay đổi (số lần mở app khi treatment là push
notification).

## Đọc con số

| $$\rho$$ | Giảm variance | Traffic cần còn lại |
| --- | --- | --- |
| 0.3 | 9% | 91% |
| 0.5 | 25% | 75% |
| 0.8 | 64% | 36% |
| 0.99 (Rossmann, doanh số cửa hàng) | 98% | 2% |

Với baseline Olist ở module 03 (16 930 đơn mỗi nhóm để phát hiện giảm 1 điểm % review xấu), một
covariate có $$\rho = 0.3$$ chỉ đưa cỡ mẫu về 15 407: CUPED mạnh khi covariate là **chính metric
đó** của cùng đơn vị trong quá khứ, yếu khi đơn vị phần lớn là khách mới.

## Bẫy thường gặp

- Tính `theta` riêng từng nhánh rồi điều chỉnh mỗi nhánh một kiểu: vẫn hợp lệ nếu làm đúng (đó là
  hồi quy có tương tác), nhưng làm sai rất dễ đưa tác động vào `theta`. Gộp là mặc định an toàn.
- Báo cáo SE của CUPED mà quên rằng `theta` cũng được ước lượng: với n hàng nghìn sai số này không
  đáng kể; với vài chục đơn vị (thí nghiệm theo cửa hàng, theo thành phố) thì dùng hồi quy OLS để
  có SE chuẩn.
- Đơn vị không có dữ liệu trước thí nghiệm (user mới): điền giá trị trung bình **và** thêm biến chỉ
  báo "không có lịch sử", đừng bỏ user đó (xem mục 2 lý thuyết).
