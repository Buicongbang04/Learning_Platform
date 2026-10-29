# Lời giải: diễn giải GLM

## Odds ratio và CI

CI tính trên thang log-odds (nơi phân phối của $$\hat\beta$$ xấp xỉ chuẩn) rồi mới `exp`, nên CI của
OR **không đối xứng** quanh OR. Tính `OR ± 1.96 × SE(OR)` (delta method trên thang OR) cho CI có thể
chứa số âm với OR nhỏ, và có coverage kém.

## Marginal effect: vì sao "rời rạc"

`get_margeff()` mặc định lấy **đạo hàm** của xác suất theo từng biến, tại từng điểm, rồi lấy trung
bình. Với biến liên tục đó là đúng. Với biến 0/1, "tăng late thêm một lượng vô cùng nhỏ" không có
nghĩa; đạo hàm của đường logistic tại điểm có xác suất thấp (phần lớn đơn đúng hẹn, ~9%) nhỏ hơn
nhiều so với bước nhảy thật từ 0 lên 1. Trên Olist (model có thêm biến kiểm soát, README mục 5): đạo
hàm cho +24.1 điểm %, rời rạc cho +45.4 điểm %. Trên dữ liệu mô phỏng của test, AME rời rạc lớn gấp
khoảng 1.9 lần bản đạo hàm.

Khi model chỉ có một biến 0/1, logistic khớp hoàn hảo tỉ lệ mỗi nhóm, nên AME rời rạc bằng đúng
chênh lệch tỉ lệ thô. Trên Olist: 54.1% − 9.2% = 44.9 điểm %, OR = 11.59.

## Kết quả trên Olist

| | Giá trị |
| --- | --- |
| OR của giao trễ (model chỉ có `late`) | 11.59 |
| AME rời rạc | +0.449 |
| Số món thêm: mean / variance | 0.142 / 0.290 |
| Pearson $$\chi^2$$/df (Poisson) | 1.98 |
| Hệ số `log_mean_price`: Poisson / NegBin | −0.389 / −0.401 |
| SE Poisson cổ điển / robust | 0.0097 / 0.0150 |
| AIC Poisson / NegBin | 87 399 / 78 047 |

`fit_count_model` chọn Negative Binomial. Hệ số gần như không đổi giữa hai model (Poisson vẫn nhất
quán cho mean); thứ thay đổi là SE và chất lượng dự đoán phân phối.

## Ngưỡng 1.5 là quyết định, không phải định luật

Không có ngưỡng chuẩn. Dispersion 1.1 với 100 nghìn dòng đã là overdispersion "có ý nghĩa thống kê"
nhưng ảnh hưởng SE chỉ khoảng $$\sqrt{1.1} \approx 1.05$$ lần. Cách làm vững hơn:

- Chỉ cần hệ số và SE: Poisson + robust SE, không cần chọn.
- Cần phân phối dự đoán (xác suất có 0, 1, 2… món): so NegBin với Poisson bằng AIC hoặc likelihood
  ratio test cho $$\alpha = 0$$ (nhớ chia đôi p-value vì $$\alpha$$ nằm ở biên).
- Thừa số 0 có cơ chế riêng: zero-inflated / hurdle. Olist có 90.0% đơn một món so với 86.7% Poisson
  dự đoán.

## Sai lầm hay gặp

- Nói "OR 11.6 nghĩa là khả năng review xấu gấp 11.6 lần" (thật ra gấp khoảng 6 lần về xác suất).
- So OR giữa các model có biến kiểm soát khác nhau như so hệ số OLS: OR không "collapsible", thêm
  một biến không tương quan với `late` vẫn làm OR của `late` đổi. AME không có vấn đề này.
- Dùng `res.predict()` không truyền dữ liệu rồi trừ cho nhau: chỉ dự đoán trên dữ liệu gốc, không
  thay đổi `var`.
- Model số món bằng Poisson trên `n_items` (luôn ≥ 1): Poisson gán xác suất cho 0 món, model sai dạng.
  Dùng `n_items − 1` hoặc zero-truncated Poisson.
