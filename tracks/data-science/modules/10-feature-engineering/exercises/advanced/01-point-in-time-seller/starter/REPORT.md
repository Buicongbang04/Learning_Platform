# Báo cáo: feature lịch sử seller point-in-time

Người đọc: DS khác trong team, người sẽ đưa feature này vào production. Xoá mọi dòng TODO khi viết
xong. Mọi con số lấy từ các cell `explore` của `seller_history.ipynb`.

## 1. Vấn đề

TODO: cách tính "tỉ lệ review xấu của seller" trên toàn bộ dữ liệu sai ở đâu; nó rò thông tin gì
(tương lai, nhãn của chính đơn).

## 2. Cách tính point-in-time

TODO: định nghĩa chính xác (mốc thời gian nào so với mốc nào, so sánh chặt hay không, xử lý nhãn của
chính đơn, smoothing, seller chưa có lịch sử). Vì sao chọn `review_answer_timestamp` làm lúc nhãn được biết.

## 3. Kết quả

TODO: bảng AUC validation và test của bốn biến thể; đọc bảng: vì sao biến thể sai trông tốt nhất, và
biến thể nào bạn tin.

## 4. Đưa vào production

TODO: tính feature này lúc serving thế nào (feature store, as-of join, độ trễ cập nhật), rủi ro
training-serving skew, và cách kiểm tra feature không rò rỉ trước mỗi lần retrain.
