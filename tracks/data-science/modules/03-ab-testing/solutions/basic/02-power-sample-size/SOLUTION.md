# Lời giải: power, MDE và cỡ mẫu

## Cách làm

Cả ba hàm dựa vào cùng một hằng số `z = z_{1−α/2} + z_{power}`. Tách hàm `_n_exact` (chưa làm tròn)
để `mde_proportions` giải phương trình liên tục; nếu giải trên bản đã làm tròn, hàm có bậc thang và
`brentq` vẫn chạy nhưng nghiệm kém chính xác.

`sample_size_means` dùng xấp xỉ normal nên nhỏ hơn bản t-distribution của statsmodels khoảng 1–2
đơn vị: không đáng kể khi n hàng nghìn, đáng kể khi n vài chục.

## Đọc kết quả cho Olist

```python
n = sample_size_proportions(0.128, -0.01)   # 16 930 đơn mỗi nhóm
weeks = 2 * n / 1259                        # ≈ 27 tuần
```

27 tuần là không khả thi: mùa vụ thay đổi, sản phẩm thay đổi, và nửa năm không ra quyết định.
Một DS sẽ quay lại bàn thiết kế với các lựa chọn:

| Lựa chọn | Tác động lên cỡ mẫu |
| --- | --- |
| Chấp nhận MDE 2 điểm % | Giảm khoảng 4 lần, còn ~6.5 tuần |
| Chỉ áp cho đơn có nguy cơ trễ (baseline review xấu ~50%) | Variance đổi, nhưng tác động kỳ vọng lớn hơn nhiều; thường lợi hơn |
| Giảm variance bằng CUPED (module 04) | Giảm n theo hệ số (1 − ρ²) |
| Đổi metric nhạy hơn (điểm review trung bình thay vì tỉ lệ ≤ 2 sao) | Phụ thuộc dữ liệu; phải đo |

## Vì sao mô phỏng cho ~80%

Power 80% nghĩa là nếu tác động thật đúng bằng MDE thì 80% số thí nghiệm sẽ bác bỏ H0. Test chạy
3 000 thí nghiệm giả lập để kiểm tra đúng định nghĩa đó, thay vì tin công thức. Đây là thói quen
tốt: khi nghi ngờ một công thức thống kê, hãy mô phỏng.

## Bẫy thường gặp

- Nhầm cỡ mẫu **mỗi nhóm** với **tổng**: thời lượng phải tính từ tổng (2n với 50/50).
- Lấy baseline của toàn bộ user trong khi thí nghiệm chỉ áp lên một tập con.
- Tính lại power sau khi thí nghiệm kết thúc ("post-hoc power") từ tác động quan sát được: con số
  đó chỉ là biến đổi của p-value, không thêm thông tin gì.
