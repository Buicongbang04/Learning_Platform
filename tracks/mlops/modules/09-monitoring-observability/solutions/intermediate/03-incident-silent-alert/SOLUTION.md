# Lời giải: alert không bắn dù service lỗi thật

## Nguyên nhân

Rule lọc lỗi bằng `status=~"5.."`, nhưng service này xuất mã HTTP ở label tên `code`, không phải `status`. Một bộ chọn trên
label không tồn tại không báo lỗi: nó đơn giản không khớp series nào. Tử số của phép chia là vector rỗng, nên kết quả rỗng,
điều kiện `> 0.05` không có gì để so, và alert ở trạng thái `inactive` mãi mãi. `promtool check rules` chỉ kiểm cú pháp PromQL,
không kiểm rule có khớp dữ liệu thật hay không.

Vì sao không ai thấy: một alert im lặng trông giống hệt một hệ thống khoẻ. Rule được viết theo quy ước tên label của dịch vụ khác
(`status`) và chưa bao giờ được chạy với đầu ra thật của service này.

## Cách sửa

Đổi `status=~"5.."` thành `code=~"5.."` (xem `rules.yml`). Mọi thứ khác giữ nguyên: đây là sự cố về selector, không phải về ngưỡng.

## Cách chẩn đoán nhanh

1. Chạy riêng từng nửa của phép chia. Mẫu số trả giá trị, tử số trả rỗng: vấn đề nằm ở bộ chọn của tử số.
2. Xem `/metrics` thật: `http_requests_total{method="POST",route="/predict",code="500"}`. Đối chiếu từng tên và giá trị label
   với bộ chọn trong rule.
3. Thử bỏ dần điều kiện trong bộ chọn cho tới khi có dữ liệu: điều kiện cuối cùng bị bỏ là thủ phạm.

## Để lần sau không lặp lại

- **Test rule bằng đầu ra thật.** Test của bài này sinh chuỗi thời gian từ chính `/metrics` của app rồi chạy `promtool test
  rules`; đưa nó vào CI của dịch vụ để rule và code cùng được kiểm khi một trong hai đổi.
- **Chứng minh alert bắn được.** Mỗi alert nên có một ca "bắn" trong test, không chỉ ca "im". Ca im luôn qua, kể cả với rule hỏng.
- **Alert về chính alert.** Thêm alert cho trường hợp tử số hay mẫu số biến mất; bài Basic 03 đã có `absent()` cho metric, mở
  rộng cho các chuỗi quan trọng.
- **Tiêm lỗi có chủ đích** ở staging định kỳ (hoặc `amtool alert add` / endpoint giả lỗi) để biết toàn bộ đường từ metric tới
  điện thoại người trực còn thông.
- **Thống nhất tên label** (`status` hay `code`) trong thư viện instrument dùng chung của công ty, và ghi vào hợp đồng metric.
