# Lời giải: VIF và loại biến lặp

## Cách tính

Mỗi cột hồi quy lên hằng số và các cột còn lại, $$\mathrm{VIF}_j = 1/(1 - R_j^2)$$. Hằng số trong
hồi quy phụ là bắt buộc: không có nó, $$R^2$$ tính quanh 0 thay vì quanh trung bình, và một biến
như `log_weight` (trung bình 6.5, độ lệch chuẩn 1.2) tự nó đã có "VIF" vài chục. Đó chính là lỗi khi
gọi `variance_inflation_factor` của statsmodels lên DataFrame chưa `add_constant`.

Vì có hằng số, VIF không đổi khi đổi đơn vị (gram sang kg) hay dịch chuyển cột: test
`test_scale_invariant` kiểm đúng điều đó.

Cách nhanh qua ma trận tương quan, $$\mathrm{VIF} = \mathrm{diag}(R^{-1})$$, cho cùng kết quả khi ma
trận khả nghịch, nhưng với đa cộng tuyến hoàn hảo thì `inv` hoặc báo lỗi hoặc trả số rác (có khi âm).
Cách hồi quy từng cột với `lstsq` không bao giờ nổ: $$1 - R^2$$ chỉ về 0 và ta trả `inf`.

## Trên Olist thật

Model phí ship (86 065 đơn một món): VIF `log_weight` 2.80, `log_volume` 2.45, `log_distance` 2.24,
`same_state` 2.23, `log_price` 1.39. Không cần làm gì.

Thêm log chiều dài, cao, rộng cùng `log_volume`: bốn cột đó VIF = inf, vì
$$\log V = \log L + \log H + \log W$$ đúng tuyệt đối. `prune_by_vif` bỏ `log_volume` (cột inf đầu
tiên) và giữ ba kích thước.

## Giới hạn của loại biến tự động

Thuật toán chọn cột bỏ theo con số, không theo ý nghĩa. Ở ví dụ trên, giữ một cột `log_volume` thay
vì ba cột kích thước có lẽ dễ diễn giải hơn, và hãng vận chuyển tính cước theo "cân nặng quy đổi" từ
thể tích. Thứ tự cột trong DataFrame lại quyết định kết quả khi hoà. Vì vậy:

- Dùng `prune_by_vif` như **cảnh báo** trong pipeline feature, không như quyết định cuối.
- Với mục đích diễn giải, quyết định bỏ / gộp biến bằng hiểu biết nghiệp vụ.
- Với mục đích dự đoán, thường không cần bỏ: Ridge hoặc model cây xử lý tốt biến tương quan.
- Không bao giờ bỏ biến quan tâm hoặc một confounder quan trọng chỉ vì VIF cao (omitted variable bias,
  README mục 2).

## Sai lầm hay gặp

- Quên hằng số (đã nói ở trên).
- Tính VIF trên dữ liệu đã one-hot đủ mọi mức của một biến phân loại cộng hằng số: dummy trap, VIF inf
  là đúng chứ không phải lỗi. Bỏ một mức làm tham chiếu.
- Đọc VIF của biến tương tác hoặc biến bình phương ($$x$$ và $$x^2$$): VIF cao là do cách tham số
  hoá, center $$x$$ trước khi bình phương sẽ hạ VIF mà không đổi model.
