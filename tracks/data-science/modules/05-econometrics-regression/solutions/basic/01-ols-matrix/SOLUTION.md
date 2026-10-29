# Lời giải: OLS bằng ma trận

## Vì sao `lstsq` thay vì nghịch đảo

Công thức sách giáo khoa $$\hat\beta = (X^\top X)^{-1} X^\top y$$ đúng về toán nhưng tệ về số học:
$$X^\top X$$ có condition number bằng **bình phương** condition number của X. Khi các cột gần cộng
tuyến (cân nặng và thể tích sản phẩm), nghịch đảo mất nhiều chữ số chính xác. `np.linalg.lstsq`
giải bằng SVD trên chính X, ổn định hơn, và trả về luôn rank để phát hiện cột thừa.

Ở bước tính SE vẫn cần $$(X^\top X)^{-1}$$. Sau khi đã kiểm X đủ rank, `np.linalg.inv` chấp nhận
được; thư viện chuyên nghiệp dùng QR: nếu $$X = QR$$ thì $$(X^\top X)^{-1} = R^{-1} R^{-\top}$$.

## Bậc tự do

$$\hat\sigma^2$$ chia cho $$n - k$$, không phải $$n$$: residual luôn nhỏ hơn sai số thật vì OLS đã
chọn $$\hat\beta$$ để làm chúng nhỏ nhất, mất $$k$$ bậc tự do. Đây cũng là chỗ fixed effects tự làm
hay sai (bài Advanced 01): demean theo $$N$$ đơn vị tiêu thêm $$N$$ bậc tự do.

## Thiếu rank: raise thay vì im lặng

`lstsq` vẫn trả về **một** nghiệm khi X thiếu rank (nghiệm có chuẩn nhỏ nhất), nhưng nghiệm đó
không có ý nghĩa diễn giải: có vô số bộ hệ số cho cùng dự đoán. Statsmodels cũng chỉ cảnh báo. Trong
pipeline phân tích, raise lỗi sớm tốt hơn là báo cáo một hệ số vô nghĩa. Ví dụ thật: đưa cả log chiều
dài, cao, rộng và log thể tích vào model phí ship Olist (vì $$\log V = \log L + \log H + \log W$$).

## Kiểm tra trực giao

$$X^\top \hat\varepsilon = 0$$ là điều kiện bậc nhất của bài toán bình phương nhỏ nhất. Có cột hằng
số thì riêng dòng đầu cho $$\sum \hat\varepsilon_i = 0$$. Test này bắt được lỗi dấu, lỗi chuyển vị
mà so sánh với statsmodels đôi khi che (nếu bạn so nhầm cùng một đại lượng sai).

## Kết quả trên Grunfeld

`invest ~ value + capital` (pooled, 220 dòng): hệ số 0.1145 và 0.2275, $$R^2 = 0.818$$. Con số này
gộp chênh lệch **giữa** các công ty (General Motors to gấp hàng trăm lần Diamond Match) với chênh
lệch **trong** từng công ty theo thời gian. README mục 7 cho thấy fixed effects đổi hệ số `capital`
thành 0.31.

## Sai lầm hay gặp

- Quên cột hằng số: hồi quy đi qua gốc toạ độ, hệ số sai và $$R^2$$ tính quanh 0 cho số đẹp giả.
- Dùng `np.var(resid)` (chia n) làm $$\hat\sigma^2$$.
- Tính p-value bằng phân phối chuẩn thay vì t: khác biệt nhỏ với n lớn nhưng sai ở mẫu nhỏ.
