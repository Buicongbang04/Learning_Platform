# Lời giải: PSI và KS khớp Evidently

Ba chi tiết quyết định việc khớp từng số, cả ba đều "vô hình" nếu chỉ đọc công thức PSI:

1. **Cách chia bin.** Evidently (0.7) không chia theo quantile của reference như nhiều bài viết PSI. Với cột số có hơn 20 giá trị riêng, nó dùng
   `np.histogram_bin_edges(nối hai tập, bins="sturges")`: bin rộng bằng nhau trên khoảng giá trị của **cả hai** tập. Với dữ liệu đuôi dài, vài
   giá trị cực lớn kéo giãn khoảng và gần như toàn bộ mẫu rơi vào một hai bin đầu; PSI thành thước đo thô. Cột số ít hơn 21 giá trị riêng (vd. số hành khách,
   mã loại thanh toán) được coi như phân loại.
2. **Bin rỗng.** Thay 0 bằng `min(khác 0) / 10**6` khi giá trị nhỏ nhất đã không lớn hơn `1e-4`, ngược lại bằng `1e-4`. Một bin rỗng không đổi được $$\ln(0)$$ thành vô cực,
   nhưng *mức* thay thế làm PSI đổi: một giá trị mới xuất hiện ở `current` cộng vào PSI nhiều hay ít tuỳ chính quy tắc này.
3. **NaN.** Bỏ trước, tỉ lệ tính trên số dòng không NaN. Tỉ lệ NaN tăng vọt là một tín hiệu khác (chất lượng dữ liệu), không nên bị PSI nuốt.

Trên `trip_distance` thật của 2019-07 so với 2019-12 (mẫu 50 000 dòng, `seed=0`): PSI kiểu Evidently ≈ 0.0114, PSI chia theo quantile ≈ 0.0015, KS p-value ≈ $$5\times10^{-7}$$.
Cả hai PSI đều dưới 0.1, KS thì "rất có ý nghĩa". Với mẫu lớn, p-value đo "có chắc là khác không" chứ không đo "khác bao nhiêu"; dùng nó làm ngưỡng báo động là nguồn alert fatigue.
Cùng một dữ liệu, hai cách chia bin cho hai số PSI khác nhau, vì vậy ngưỡng 0.1 và 0.25 chỉ có nghĩa khi gắn với cách chia bin cụ thể: ghi cách chia vào tài liệu monitoring.

Ngưỡng mặc định của Evidently trong bài này: PSI $$\ge 0.1$$ và KS p-value $$< 0.05$$. Hãy coi chúng là điểm xuất phát; giá trị thật phải chọn từ dữ liệu ngày bình thường của chính bạn.
