# Lời giải: vector, phép chiếu và condition number

## Cosine similarity

$$\cos\theta = \frac{a\cdot b}{\lVert a\rVert\,\lVert b\rVert}$$ chỉ đo **hướng**, bỏ qua độ dài. Vì thế nó là
thước đo mặc định cho embedding (văn bản, sản phẩm, user): hai mô tả sản phẩm dài ngắn khác nhau nhưng
cùng chủ đề vẫn có cosine cao. Lỗi hay gặp: dùng cosine trên vector chưa trừ trung bình khi mọi thành
phần đều dương (đếm, TF), mọi cặp đều có cosine cao và thước đo mất sức phân biệt. Vector 0 thì
cosine không xác định; code production nên chặn trường hợp này.

## Chiếu lên một vector

$$\mathrm{proj}_u v = \frac{v\cdot u}{u\cdot u}\,u$$. Hai tính chất test kiểm chính là định nghĩa của phép
chiếu vuông góc: phần dư $$v - \mathrm{proj}_u v$$ vuông góc với $$u$$, và chiếu lần hai không đổi gì.

## Ma trận chiếu và least squares

$$P = X(X^\top X)^{-1}X^\top$$ đưa mọi vector $$y$$ về điểm gần nhất trong không gian cột của $$X$$. Điểm đó
chính là $$\hat y$$ của linear regression, và residual $$y - \hat y$$ vuông góc với mọi cột: đây là normal
equation $$X^\top(y - Xw) = 0$$ viết dưới dạng hình học. `trace(P)` bằng số cột độc lập, cũng là
"số bậc tự do" model dùng; đó là lý do ước lượng variance của residual chia cho $$n - d$$.

Lời giải giải hệ `np.linalg.solve(X.T @ X, X.T)` thay vì nghịch đảo. Trong thực tế bạn **không bao
giờ** tạo ma trận n×n này; nó chỉ là công cụ để hiểu. Leverage $$h_{ii} = P_{ii}$$ thì có dùng: điểm có
leverage cao (sản phẩm 40 kg giữa một catalog toàn đồ nhẹ) kéo đường hồi quy mạnh, và Cook's
distance dựa trên nó.

## Condition number

$$\kappa(X) = \sigma_{\max}/\sigma_{\min}$$. Trên Olist thật (train, ma trận `[1, kg, lít]`), κ ≈ 36.4; đổi sang
`[1, gram, cm³]` thì κ ≈ 36 431, gấp khoảng 1000 lần, dù hai ma trận chứa cùng thông tin. Phần
ill-conditioning sinh ra do đơn vị đo bỏ được bằng chuẩn hoá cột; phần do các cột gần phụ thuộc
tuyến tính thì không (bài Advanced 01).

## Sai lầm hay gặp

- `np.linalg.inv(X.T @ X) @ X.T @ y`: chậm hơn và kém chính xác hơn `solve`; khi κ lớn thì sai thấy rõ.
- Tính `np.linalg.cond(X.T @ X)` rồi nghĩ đó là κ của X: nó là $$\kappa(X)^2$$.
- Quên rằng `projection_matrix` cần các cột độc lập; có cột trùng thì $$X^\top X$$ suy biến.
