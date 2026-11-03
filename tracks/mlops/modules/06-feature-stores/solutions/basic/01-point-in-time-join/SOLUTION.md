# Lời giải: point-in-time join

`pit.py` cạnh tệp này. Các điểm cần nhớ:

- **`merge_asof` backward chính là luật "chỉ dùng cái đã biết".** Mỗi dòng trái lấy dòng phải gần nhất có thời điểm không
  muộn hơn; `allow_exact_matches=True` khớp mặc định của Feast (feature có timestamp đúng bằng thời điểm sự kiện được dùng).
- **`feature_ts` là lúc giá trị khả dụng, không phải lúc nó mô tả.** Trong test, tốc độ trung bình của giờ 10:00–11:00 chỉ
  tính xong lúc 11:00, nên `feature_ts = 11:00`. Đóng dấu 10:00 là cách phổ biến để vô tình rò rỉ: sự kiện lúc 10:30 sẽ
  "thấy" một số chưa ai tính ra.
- **Trả đúng thứ tự gốc.** `merge_asof` buộc phải sắp bảng trái theo thời gian; gắn `_order` trước khi sắp rồi sắp lại
  sau là cách đơn giản nhất, và `stable` sort để các sự kiện cùng giây giữ thứ tự.
- **`tolerance` là cách nói "giá trị quá cũ coi như thiếu".** Offline phải dùng cùng ngưỡng với TTL của online store, nếu
  không train thấy giá trị mà serve không thấy.

Lỗi hay gặp: nối theo khoá rồi lọc `feature_ts <= event_ts` (mất sự kiện không có feature, và chọn dòng bất kỳ chứ không phải
dòng mới nhất); quên rằng dữ liệu một bên là `datetime64[us]`, bên kia `[ns]`, `merge_asof` báo lỗi kiểu khoá.
