# Lời giải: phân phối giá trị đơn Olist

Notebook lời giải: `distribution.ipynb` (chạy được toàn bộ khi đã tải Olist).

## MLE

- **Lognormal**: log-likelihood theo $$\mu, \sigma$$ chính là log-likelihood chuẩn của $$\log x$$ (cộng
  một hằng số $$-\sum \log x_i$$ không phụ thuộc tham số), nên MLE là trung bình và độ lệch chuẩn
  **chia n** của $$\log x$$. Dùng `ddof=1` sai nhẹ (không còn là MLE).
- **Gamma**: phương trình MLE cho shape $$a$$ là $$\log a - \psi(a) = \log \bar x - \overline{\log x}$$
  ($$\psi$$ là digamma), giải số; scale $$= \bar x / a$$. Vì vậy MLE gamma luôn giữ đúng trung bình mẫu
  (test kiểm điều này). `stats.gamma.fit(x, floc=0)` giải đúng phương trình đó.

## Kết quả trên Olist

96 470 đơn giao xong; median 105.28, mean 159.83, percentile 99 là 1 052.4 BRL.

| | Lognormal | Gamma |
| --- | --- | --- |
| Tham số | $$\hat\mu = 4.691$$, $$\hat\sigma = 0.808$$ | shape 1.448, scale 110.37 |
| Log-likelihood | −568 783 | −582 335 |
| AIC | 1 137 571 | 1 164 674 |
| KS statistic | 0.026 | 0.097 |
| P(X > 1 000) | 0.30% | 0.04% |

Thực tế P(X > 1 000) = 1.15%.

## Đọc QQ-plot

Trên thang log, QQ của lognormal bám đường chéo ở thân, rồi cong lên trên từ khoảng percentile 90:
quantile 99% của mẫu (1 052) lớn hơn của lognormal (713) 48%. Gamma lệch cả ở thân lẫn đuôi: gamma
có đuôi mũ (nhẹ hơn nhiều so với đuôi lognormal), không hợp với dữ liệu tiền.

## KS test: đọc đúng

Trên toàn bộ 96 470 đơn, KS cho lognormal D = 0.026, p ≈ 7.8e-57. Trên 500 đơn ngẫu nhiên: D = 0.029,
p = 0.78. Cùng phân phối, cùng mức lệch, kết luận ngược nhau: p-value phụ thuộc chủ yếu vào n. Thêm
nữa, tham số ước lượng từ chính dữ liệu làm p-value KS chuẩn quá lớn (Lilliefors). Dùng KS statistic để
xếp hạng các phân phối; dùng QQ-plot và đại lượng nghiệp vụ để quyết định.

## Rubric cho khuyến nghị

| Tiêu chí | Đạt khi |
| --- | --- |
| Chọn phân phối cho mục đích tổng thể | Lognormal, có số (AIC hoặc KS) |
| Nhận ra đuôi sai | Nêu tỉ lệ thực tế 1.15% so với 0.30% / 0.04% |
| Đọc đúng KS | Không kết luận "không phải lognormal nên không dùng được" |
| Đề xuất cho đuôi | Phân phối thực nghiệm, Pareto / GPD cho đuôi, hoặc mixture; theo danh mục |

## Sai lầm hay gặp

- Chọn phân phối chỉ bằng AIC rồi dùng cho mọi câu hỏi. AIC bị chi phối bởi phần thân, nơi có nhiều
  điểm nhất.
- Quên `floc=0` khi fit gamma / lognormal bằng scipy.
- So AIC giữa hai model fit trên hai tập dữ liệu khác nhau (ví dụ một model bỏ outlier).
- Mô phỏng tổng doanh thu bằng cách lấy mẫu độc lập từ phân phối giá trị đơn: bỏ qua mùa vụ và tương
  quan theo thời gian (module 07).
