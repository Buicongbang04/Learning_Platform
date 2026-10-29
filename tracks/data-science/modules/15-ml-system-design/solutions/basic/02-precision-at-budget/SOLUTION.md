# Lời giải: precision@k theo ngân sách

## Cách làm

Một hàm phụ `_top_hits` làm phần chung: kiểm tra k, cắt k về n, lấy top k bằng `argsort(-scores)`
(`kind="stable"` để kết quả tái lập được khi có điểm bằng nhau), trả số ca dương trong top k và tổng ca
dương. `precision_at_k`, `recall_at_k` và `weekly_at_k` đều dùng lại nó, nên định nghĩa không lệch nhau.

Điểm bằng nhau là chuyện thật (model cây cho nhiều đơn cùng một điểm). Khi đó precision@k phụ thuộc cách
phá hoà; báo cáo nghiêm túc nên nói rõ cách phá hoà, hoặc chọn theo ngưỡng thay vì theo k.

## Đọc kết quả trên Olist

Với ngân sách cố định, precision tuần phụ thuộc số ca dương **trong tuần đó**. Giai đoạn 06/2017 –
07/2018 có trung vị 61 đơn trễ mỗi tuần nhưng phân vị 90 là 289 và tuần tệ nhất 565 (lý thuyết, mục 3).
Một tuần chỉ có 4 đơn trễ (tuần 2018-06-03 ở tập test) thì top 25 có precision tối đa 16%, chỉ
nhỉnh hơn break-even 11.1% của tin nhắn tự động; tuần có hàng trăm đơn trễ thì top 25 bỏ sót gần hết. Vì vậy:

- Báo cáo cả precision **gộp** (tổng hits / tổng selected) lẫn phân phối theo tuần.
- Đặt sàn precision bằng ngưỡng điểm, trần bằng k: chính sách lai (bài Advanced 01).
- Khi số tuần chạm trần tăng, đó là tín hiệu vận hành (cần thêm người), không phải tín hiệu model.

## Bẫy thường gặp

- Tính precision@k trên **toàn bộ tập test** trong khi quyết định thật làm theo tuần: con số gộp che mất
  tuần tệ.
- Dùng recall@k làm metric chính khi k cố định: recall tự giảm khi số ca dương tăng, dù model không đổi.
- Quên rằng `k` lớn hơn số ứng viên trong tuần.
