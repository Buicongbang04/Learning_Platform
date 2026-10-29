# Lời giải: robust SE và Breusch-Pagan

## Sandwich: chỉ thay phần giữa

SE cổ điển là $$\hat\sigma^2 (X^\top X)^{-1}$$, viết lại dạng sandwich:

$$
(X^\top X)^{-1} \left( \hat\sigma^2 X^\top X \right) (X^\top X)^{-1}
$$

Phần giữa giả định mọi quan sát có cùng variance $$\hat\sigma^2$$. Robust SE thay nó bằng
$$\sum_i w_i \hat\varepsilon_i^2 x_i x_i^\top$$: mỗi quan sát dùng residual bình phương của chính nó
làm ước lượng (rất nhiễu, nhưng cộng lại thì nhất quán) cho variance của nó. "Vỏ bánh"
$$(X^\top X)^{-1}$$ giữ nguyên. Cluster SE (README mục 3) cũng chỉ thay phần giữa: cộng score
$$x_i \hat\varepsilon_i$$ trong từng cluster trước, rồi mới lấy tích ngoài.

## Vì sao HC3

Residual OLS nhỏ hơn sai số thật một cách có hệ thống, nhất là ở điểm leverage cao:
$$\mathrm{Var}(\hat\varepsilon_i) = \sigma^2 (1 - h_{ii})$$. HC0 dùng thẳng $$\hat\varepsilon_i^2$$ nên
thiên nhỏ; HC1 phóng đều mọi điểm; HC3 phóng mạnh đúng các điểm leverage cao, gần với jackknife.
MacKinnon & White (1985) và Long & Ervin (2000) cho thấy HC3 cho coverage tốt nhất ở mẫu dưới vài
trăm. Với mẫu rất lớn ba cách gần như trùng nhau.

## Không dựng ma trận n × n

Hat matrix $$X(X^\top X)^{-1}X^\top$$ có $$n^2$$ phần tử: 200 000 dòng là 320 GB. Chỉ cần đường
chéo: $$h_{ii} = x_i^\top (X^\top X)^{-1} x_i$$, tính bằng `((X @ bread) * X).sum(axis=1)`. Phần giữa
cũng vậy: nhân trọng số vào từng dòng của X rồi `.T @ X`. Cả hai là $$O(nk^2)$$.

## Kết quả mô phỏng

600 lần, n = 200, sd của sai số tăng theo $$x^2$$ (seed 42 trong test):

| SE | CI 95% chứa hệ số thật |
| --- | --- |
| Cổ điển | 63.5% |
| HC0 | 94.3% |
| HC3 | 95.0% |

CI cổ điển ở đây có tỉ lệ false positive gần 37% thay vì 5%. Qua 12 seed khác, HC3 nằm trong
92.8–95.5%, cổ điển 60–64%.

## Breusch-Pagan chỉ bắt được dạng nó tìm

Breusch-Pagan hồi quy $$\hat\varepsilon^2$$ **tuyến tính** lên X. Trong dữ liệu dùng cho test coverage
(sd tăng theo $$x^2$$, đối xứng quanh 0), $$\hat\varepsilon^2$$ không có xu hướng tuyến tính theo x:
với 3 seed, Breusch-Pagan cho p = 0.98, 0.003, 0.12, trong khi heteroskedasticity cực mạnh (White
test, thêm $$x^2$$ vào hồi quy phụ, cho p < 1e-30 cả ba lần). Đó là lý do test dùng dữ liệu "hình
phễu" (x dương, sd tăng theo x) cho Breusch-Pagan.

Bài học thực tế: **không dùng test để quyết định có dùng robust SE hay không**. Test có thể bỏ sót
dạng heteroskedasticity, và test trước rồi chọn SE theo kết quả làm sai lệch inference. Dùng robust
SE mặc định; test chỉ để mô tả.

## Trên Olist

Model tuyến tính `freight_value ~ product_weight_g + distance_km + price` (86 065 đơn): Breusch-Pagan
LM = 7 977, SE HC3 của hệ số cân nặng và giá gấp 3.3 lần SE cổ điển. Model log giảm tỉ lệ đó còn
0.91–1.17, nhưng cluster theo seller vẫn làm SE tăng 3.5–8.7 lần (README mục 3).
