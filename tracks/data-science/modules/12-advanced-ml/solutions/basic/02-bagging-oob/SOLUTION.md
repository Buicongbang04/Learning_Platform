# Lời giải: bagging và out-of-bag estimate

## Cách làm

- $$P(i \notin \text{bootstrap}) = (1 - 1/n)^n \to e^{-1} \approx 0.368$$. Mỗi cây bỏ sót khoảng
  37% điểm, và với 100 cây thì xác suất một điểm có mặt ở mọi mẫu là $$0.632^{100}$$, coi như 0.
- Mỗi cây cộng dự đoán vào `test_sum`, và chỉ cộng vào `oob_sum` cho các điểm nằm ngoài mẫu
  bootstrap của nó. `oob_pred = oob_sum / oob_count`.

## Vì sao bagging giảm sai số

Gọi $$\sigma^2$$ là variance dự đoán của một cây và $$\rho$$ là tương quan giữa dự đoán của hai cây. Trung
bình của B cây có variance:

$$
\operatorname{Var}\Big(\frac1B\sum_b h_b\Big) = \rho\,\sigma^2 + \frac{1 - \rho}{B}\,\sigma^2
$$

Tăng B chỉ xoá được số hạng thứ hai. Số hạng $$\rho\sigma^2$$ còn nguyên, nên muốn giảm thêm phải làm
cây **bớt giống nhau**: đó là việc của `max_features` trong random forest. Bias không đổi: trung
bình nhiều cây sâu vẫn có bias của một cây sâu (thấp). Vì thế bagging hợp với base learner bias
thấp, variance cao, và gần như vô dụng với cây depth 1.

## Số liệu khi kiểm 15 seed

- MSE test của 100 cây bagging bằng tối đa 65% MSE của một cây sâu (ngưỡng test 75%).
- Tỉ số OOB MSE / test MSE nằm trong 0.91–1.19.
- Nếu "ước lượng" bằng sai số của chính bagging trên tập train (cây đã thấy điểm), tỉ số chỉ còn
  khoảng 0.14 (seed 0): lạc quan gấp 7 lần.

## Khi nào dùng OOB

| Tình huống | OOB dùng được? |
| --- | --- |
| Dữ liệu i.i.d., cần chọn nhanh `max_features`, `min_samples_leaf` | Có, tiết kiệm một tập validation |
| Dữ liệu theo thời gian (Olist, giao dịch) | **Không**: OOB trộn tương lai vào quá khứ, giống KFold ngẫu nhiên (module 10) |
| Nhiều dòng của cùng một khách | Không: điểm OOB vẫn có "anh em" trong mẫu, OOB lạc quan |
| Cần so sánh với mô hình khác (boosting) | Không công bằng; dùng chung một holdout |

## Lỗi hay gặp

- Dùng chung một `random_state` cố định cho mọi cây khi `max_features < 1`: mọi cây rút cùng một chuỗi số ngẫu
  nhiên để chọn feature, các cây giống nhau hơn và một phần tác dụng giảm tương quan bị mất.
- Quên trường hợp `oob_count == 0` (chia cho 0) với ít cây.
