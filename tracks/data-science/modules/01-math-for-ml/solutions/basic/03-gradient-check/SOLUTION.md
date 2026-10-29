# Lời giải: gradient bằng tay và gradient check

## Sai phân trung tâm

Khai triển Taylor: $$f(x \pm \varepsilon) = f(x) \pm \varepsilon f'(x) + \tfrac{\varepsilon^2}{2}f''(x) \pm \tfrac{\varepsilon^3}{6}f'''(x) + \dots$$
Trừ hai vế, số hạng bậc chẵn triệt tiêu, nên $$\frac{f(x+\varepsilon) - f(x-\varepsilon)}{2\varepsilon} = f'(x) + O(\varepsilon^2)$$,
còn sai phân tiến chỉ $$O(\varepsilon)$$. Test với $$f(x) = x^3$$, $$\varepsilon = 10^{-3}$$: trung tâm cho đúng
$$3 + \varepsilon^2$$, tiến cho $$3 + 3\varepsilon$$.

Lời giải sao chép `x` (`np.array(x, dtype=float)`) rồi sửa từng toạ độ và **trả lại giá trị cũ** sau
mỗi lần. Sửa thẳng vào mảng của người gọi là bug khó thấy: hàm vẫn "đúng" nhưng phá dữ liệu bên ngoài.
Chi phí: 2d lần gọi `f`, nên gradient check chỉ dùng để kiểm, không dùng để train (model có hàng triệu
tham số thì check trên vài toạ độ ngẫu nhiên).

## MSE

$$L = \frac1n\lVert Xw - y\rVert^2$$, $$\nabla L = \frac{2}{n}X^\top(Xw - y)$$. Lỗi kinh điển là quên hệ số 2
(nhầm với quy ước $$\tfrac{1}{2n}$$); gradient check bắt được ngay với sai số tương đối 1/3, như test
cuối cho thấy.

## Logistic loss và chain rule

Chuỗi tính: $$w \to z = Xw \to p = \sigma(z) \to L$$. Chain rule:

$$
\frac{\partial L}{\partial w} = \frac{\partial L}{\partial p}\cdot\frac{\partial p}{\partial z}\cdot\frac{\partial z}{\partial w}
= \frac{p - y}{p(1-p)}\cdot p(1-p)\cdot x = (p - y)\,x
$$

Hai thừa số $$p(1-p)$$ triệt tiêu: đó là lý do sigmoid đi cùng cross-entropy (và softmax đi cùng
categorical cross-entropy) cho gradient gọn và không bị "tắt" khi model sai nặng.

**Ổn định số.** Tính `p = 1 / (1 + np.exp(-z))` rồi `np.log(p)`: với z = −1000, `exp(1000)` tràn thành
`inf`, `p = 0`, `log(0) = -inf`. Viết loss theo logit, $$\log(1 + e^{z}) - yz$$, với `np.logaddexp(0, z)` thì
mọi z đều ổn. PyTorch có `BCEWithLogitsLoss` vì đúng lý do này; dùng `BCELoss` sau `sigmoid` là lỗi
hay gặp.

## Ngưỡng sai số tương đối

| Sai số tương đối | Đọc là |
| --- | --- |
| < 1e-7 | Gradient đúng |
| 1e-7 tới 1e-4 | Nghi ngờ; có thể do hàm có điểm gãy (ReLU, `abs`) gần điểm kiểm |
| > 1e-4 | Gần như chắc chắn có bug |

Kiểm bằng float64, ở điểm ngẫu nhiên (không phải w = 0, nơi nhiều bug bị che), và tắt dropout hay mọi
thứ ngẫu nhiên trong loss.
