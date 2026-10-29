# Lời giải: normal equation cho phí ship Olist

## Cách làm

Đạo hàm $$\lVert y - Xw\rVert^2$$ theo $$w$$ là $$-2X^\top(y - Xw)$$. Cho bằng 0 được normal equation
$$X^\top X\,w = X^\top y$$. Lời giải gọi `np.linalg.solve(X.T @ X, X.T @ y)`: một phân rã LU trên ma trận
d×d (ở đây 3×3), rẻ hơn và chính xác hơn tính nghịch đảo rồi nhân.

`add_intercept` thêm cột 1 để model có hệ số tự do. Không có intercept, đường hồi quy bị ép đi qua
gốc toạ độ và residual không còn trung bình 0.

## Kết quả trên Olist thật

Train: 51 216 order item mua trước 2018-01-01 (đã bỏ 18 item có sản phẩm thiếu kích thước trên toàn bộ
dữ liệu). Test: 37 318 item mua từ 2018-04-01 tới hết 2018-08-31.

$$
\widehat{\text{freight}} = 13.2485 + 1.4592\cdot\text{kg} + 0.1790\cdot\text{lít}
$$

| | R² | RMSE (BRL) |
| --- | --- | --- |
| Train | 0.458 | 10.58 |
| Test | 0.342 | 14.87 |
| Test, dự đoán bằng trung bình train | | 18.40 |

Đọc hệ số: giữ thể tích cố định, mỗi kg thêm khoảng 1.46 BRL phí ship; giữ khối lượng cố định, mỗi lít
thêm khoảng 0.18 BRL. Khối lượng và thể tích tương quan 0.79, nên "giữ cái kia cố định" là một giả
định mạnh: rất ít sản phẩm nặng mà nhỏ.

## Vì sao R² chỉ khoảng 0.34

Phí ship ở Brazil phụ thuộc mạnh vào **quãng đường** (seller ở São Paulo giao cho khách ở Amazonas) và
hợp đồng vận chuyển, không có trong hai feature này. R² test thấp hơn train vì phân phối thay đổi
theo thời gian (2018 có thêm seller, vùng giao mới). Normal equation đã cho nghiệm tốt nhất **trong lớp
model tuyến tính trên hai feature này**; muốn tốt hơn phải thêm thông tin, không phải đổi optimizer.

## Khi nào dùng normal equation

| Tình huống | Normal equation? |
| --- | --- |
| d nhỏ (vài chục tới vài nghìn), dữ liệu vừa bộ nhớ, feature đã chuẩn hoá | Có: nhanh nhất, chỉ cần $$X^\top X$$ |
| Dữ liệu không vừa bộ nhớ | Cộng dồn $$X^\top X$$ và $$X^\top y$$ theo từng chunk (hoặc trong SQL / Spark), rồi giải hệ d×d |
| d rất lớn (hàng trăm nghìn feature thưa) | Không: chi phí $$O(d^3)$$; dùng SGD hoặc solver lặp (LSQR, conjugate gradient) |
| Feature gần trùng nhau, condition number lớn | Không: dùng QR / SVD hoặc ridge (Advanced 01) |
