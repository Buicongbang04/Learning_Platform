# Lời giải: momentum và SGD minibatch

## Gradient descent trên hàm bậc hai

Với $$f(w) = \tfrac12 w^\top A w - b^\top w$$, sai số $$e_t = w_t - w^*$$ thoả $$e_{t+1} = (I - \text{lr}\,A)e_t$$.
Theo hướng eigenvector có trị riêng $$\lambda$$, sai số nhân với $$1 - \text{lr}\,\lambda$$ mỗi bước:

- $$\text{lr} > 2/L$$: hướng $$\lambda = L$$ có $$|1 - \text{lr}\,L| > 1$$, phân kỳ.
- $$\text{lr} = 1/L$$: hướng $$\lambda = \mu$$ chỉ giảm $$1 - 1/\kappa$$ mỗi bước, cần cỡ $$\kappa\ln(1/\text{tol})$$ bước.

Trên 10 hàm bậc hai bị xoay ngẫu nhiên với trị riêng {1, 3, 10, 40, 100}, gradient descent cần
1 015 – 1 342 bước để khoảng cách tới nghiệm còn 1e-6 lần ban đầu.

## Momentum

Heavy ball thêm "quán tính": $$v_{t+1} = \beta v_t - \text{lr}\,\nabla f(w_t)$$. Theo hướng cong ít, các
gradient nhỏ cùng dấu cộng dồn lại; theo hướng cong nhiều, các gradient đổi dấu triệt tiêu nhau.
Với tham số tối ưu cho hàm bậc hai

$$
\text{lr} = \frac{4}{(\sqrt L + \sqrt\mu)^2}, \qquad \beta = \left(\frac{\sqrt L - \sqrt\mu}{\sqrt L + \sqrt\mu}\right)^2,
$$

tốc độ thành $$(\sqrt\kappa - 1)/(\sqrt\kappa + 1) \approx 0.82$$ mỗi bước với κ = 100: chỉ 83 – 93 bước trên
cùng 10 bài toán, nhanh hơn khoảng 12 – 15 lần. Cấu hình "mặc định" β = 0.9, lr = 1/L cần 240 – 261 bước:
vẫn nhanh hơn gradient descent nhiều dù không tối ưu.

Trong deep learning không biết μ, L và loss không phải bậc hai, nên β = 0.9 là mặc định phổ biến.
Adam kết hợp momentum với việc chia gradient theo độ lớn trung bình của từng toạ độ (một dạng tiền
điều kiện chéo, giảm κ).

## SGD minibatch

Gradient của một batch là ước lượng **không chệch** nhưng **có nhiễu** của gradient toàn bộ. Với lr
cố định, nhiễu không bao giờ tắt: w nhảy quanh nghiệm trong một vùng có bán kính tỉ lệ với lr. Trên
10 seed (n = 5 000, batch 16, 20 epoch, lr = 0.05), khoảng cách tới nghiệm least squares là
0.39 – 1.69 với lr cố định, còn 0.008 – 0.028 với $$\text{lr}_t = 0.05/(1 + 0.01t)$$.

Lý thuyết (Robbins–Monro) đòi $$\sum_t \text{lr}_t = \infty$$ (đi được đủ xa) và $$\sum_t \text{lr}_t^2 < \infty$$ (nhiễu
tắt dần); $$1/t$$ thoả cả hai. Thực tế deep learning hay dùng warmup rồi cosine hoặc step decay.

## Đánh đổi batch size

| Batch | Ưu | Nhược |
| --- | --- | --- |
| 1 | Cập nhật nhiều nhất mỗi epoch, nhiễu giúp thoát điểm yên ngựa | Không tận dụng được vector hoá / GPU |
| 32 – 512 | Cân bằng, mặc định trong deep learning | Phải chỉnh lr theo batch |
| Toàn bộ | Gradient chính xác, hội tụ đơn điệu | Mỗi bước đắt, không chạy được khi dữ liệu lớn |

## Sai lầm hay gặp

- Tạo lại `rng` mỗi epoch với cùng seed: mọi epoch có cùng thứ tự, mất tính ngẫu nhiên.
- Không xáo dữ liệu đã sắp theo thời gian hay theo nhãn: các batch liên tiếp lệch, SGD dao động mạnh.
- Reset biến đếm `t` mỗi epoch: lr nhảy lại về `lr0`.
- So optimizer bằng số epoch thay vì thời gian hoặc số lần tính gradient.
