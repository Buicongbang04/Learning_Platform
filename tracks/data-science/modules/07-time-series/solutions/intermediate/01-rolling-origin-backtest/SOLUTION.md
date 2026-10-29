# Lời giải: backtest rolling origin

## Thiết kế

- `rolling_origin_splits` chỉ làm việc với vị trí: đơn giản, dễ kiểm, dùng lại được cho numpy,
  pandas và cả dữ liệu nhiều chuỗi (chia theo ngày rồi lọc).
- `backtest` truyền `values[train_idx].copy()`: forecaster không thể đọc tương lai (chỉ có mảng
  train) và không thể sửa dữ liệu gốc. Đây là hàng rào chống leakage bằng cấu trúc, tốt hơn mọi lời
  nhắc "nhớ đừng dùng dữ liệu test".
- `compare` tính MASE theo từng origin với mẫu số từ train của origin đó, rồi lấy trung bình. Với
  chuỗi tăng trưởng (Olist năm 2018 gấp gần 3 lần đầu 2017), một mẫu số chung sẽ cho các origin sau
  trọng số lớn hơn.

## Expanding hay sliding window

| | Expanding | Sliding |
| --- | --- | --- |
| Dữ liệu train | Tăng dần | Cố định k điểm gần nhất |
| Ưu | Ước lượng ổn định hơn, tận dụng mùa vụ năm | Thích nghi khi hành vi thay đổi (sau Covid, sau đổi giá) |
| Nhược | Dữ liệu cũ lỗi thời vẫn có trọng số | Ít dữ liệu, phương sai lớn |
| Giống production khi | Retrain trên toàn bộ lịch sử | Retrain trên k ngày gần nhất |

Quy tắc: backtest phải mô phỏng đúng cách model sẽ được retrain và dùng trong production, kể cả
**độ trễ dữ liệu** (dữ liệu hôm qua sáng nay mới có thì origin phải lùi thêm một ngày).

## Error theo horizon

Với random walk và dự báo naive, sai số ở bước h là tổng h cú sốc độc lập, nên độ lệch chuẩn tỉ lệ
với căn bậc hai của h. Bảng MAE theo h là thứ nên đưa cho người dùng dự báo: họ cần biết dự báo cho
ngày mai đáng tin hơn dự báo cho hai tuần tới bao nhiêu, chứ không chỉ một con số MAE chung.

## So với thư viện

- `sklearn.model_selection.TimeSeriesSplit`: expanding (hoặc `max_train_size` cho sliding), có `gap`
  để mô phỏng độ trễ, nhưng chia theo số fold thay vì theo horizon cố định.
- `statsforecast`/`sktime` có `cross_validation`/`ExpandingWindowSplitter` đúng ý tưởng rolling origin.
- Module 10 bàn kỹ CV theo thời gian cho bài toán ML dạng bảng (có `gap`, purging).
