# Lời giải: Maximum Likelihood Estimation

## Công thức đóng

| Phân phối | Log-likelihood (bỏ hằng số) | MLE |
| --- | --- | --- |
| Bernoulli(p) | $$k \log p + (n - k)\log(1 - p)$$ | $$\hat p = k / n$$ |
| Poisson(λ) | $$\textstyle\sum x_i \log\lambda - n\lambda$$ | $$\hat\lambda = \bar x$$ |
| Exponential(λ) | $$n\log\lambda - \lambda \textstyle\sum x_i$$ | $$\hat\lambda = 1 / \bar x$$ |
| Lognormal(μ, σ) | $$-n\log\sigma - \textstyle\sum(\log x_i - \mu)^2 / (2\sigma^2)$$ | mean và std (`ddof=0`) của `log x` |

MLE của σ dùng `ddof=0`, nên **lệch xuống** (biased): kỳ vọng của nó nhỏ hơn σ thật. Với n lớn không
đáng kể; với n = 5 thì kỳ vọng của σ̂ chỉ khoảng 0.84σ, thấp hơn cỡ 16%. MLE không hứa không lệch; nó
hứa **consistent** (hội tụ về giá trị thật khi n tăng) và **hiệu quả tiệm cận** (variance nhỏ nhất có thể khi n lớn).

## Tối ưu số

Tối ưu theo `log_sigma` thay vì `sigma` là thủ thuật **reparameterization**: biến ràng buộc
`sigma > 0` thành biến tự do trên cả trục số, optimizer không bao giờ thử sigma âm. Logistic
regression làm điều tương tự với xác suất (tối ưu trên log-odds).

Chia NLL cho n không đổi điểm cực tiểu nhưng giữ gradient cỡ 1: với 96 nghìn đơn, NLL tổng cỡ 5e5 và
BFGS có thể dừng sớm vì tiêu chí hội tụ dựa trên độ lớn gradient.

## Trên dữ liệu thật

Giá trị đơn Olist (96 470 đơn giao xong): `mu ≈ 4.691`, `sigma ≈ 0.808`. Median theo mô hình là
`exp(4.691) ≈ 109` BRL, gần median thật 105.28. Nhưng mean theo mô hình
`exp(4.691 + 0.808²/2) ≈ 151` BRL, thấp hơn mean thật 159.83: mô hình Lognormal đánh giá thấp đuôi
phải. Dùng nó để ước tính doanh thu từ những đơn rất lớn sẽ thiếu.

## Khi nào MLE gặp khó

- **Không có lời giải hữu hạn**: logistic regression trên dữ liệu tách hoàn toàn (perfect separation)
  có hệ số tiến ra vô cùng. Thêm regularization (tương đương prior trong Bayesian).
- **Mẫu nhỏ**: MLE của tỉ lệ với 0/7 đơn xấu là 0%, một kết luận quá tự tin. Beta-Binomial (bài
  Intermediate 03) sửa điều này.
- **Mô hình sai**: MLE vẫn chạy và cho con số, nhưng là tham số "gần nhất" với dữ liệu trong họ phân
  phối đã chọn (theo KL divergence), không phải sự thật. Luôn kiểm tra fit (QQ-plot, so percentile).
