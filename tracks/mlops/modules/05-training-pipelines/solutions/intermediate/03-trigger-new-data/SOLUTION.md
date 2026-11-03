# Lời giải: trigger theo dữ liệu mới

Mã nằm trong `trigger.py` cạnh tệp này.

## Vì sao hash nội dung

Ba tín hiệu để biết "có dữ liệu mới": thời điểm sửa tệp (mtime), tên/đường dẫn, và nội dung. Hai cái đầu nói dối: `touch`, `cp`,
`rsync` đổi mtime mà không đổi dữ liệu, tải lại cùng một tệp từ nguồn cũng vậy; ngược lại một job có thể ghi dữ liệu khác vào cùng
đường dẫn mà mtime bị giữ nguyên. Hash nội dung trả lời đúng câu hỏi bạn quan tâm. Với dữ liệu lớn dùng hash do nguồn cung cấp
(`dvc.lock`, ETag, snapshot id) để khỏi đọc lại cả tập.

## Hash đổi chưa đủ lý do để train

`min_new_rows` là guardrail chống "retrain vì một dòng". Quyết định then chốt là **không ghi hash khi bỏ qua**: nếu ghi, dữ liệu
tích luỹ từng chút một sẽ không bao giờ vượt ngưỡng vì mỗi lần so với một mốc vừa được cập nhật. Giữ mốc ở lần train thành công
gần nhất thì lượng dữ liệu mới tính theo mốc đó và cuối cùng vượt ngưỡng. Đây cũng là nơi nhãn về muộn nên được tính: "dòng mới"
nên là dòng mới **đã có nhãn**.

## Ghi state sau khi train thành công

Nếu ghi trước và train hỏng, hệ thống coi dữ liệu này đã được huấn luyện; lần chạy sau thấy hash trùng và bỏ qua, model cũ ở
lại vô thời hạn mà không ai biết. Ghi sau: train hỏng thì state cũ còn nguyên, lần sau thử lại. Cái giá là một cửa sổ nhỏ: train
xong nhưng chết trước khi ghi state dẫn tới train lại một lần; chấp nhận được vì train phải idempotent, và an toàn hơn kết cục
ngược lại.

## Vì sao `force`

Có việc buộc phải train dù dữ liệu không đổi: đổi code, đổi siêu tham số, sửa lỗi pipeline. `force` là đường thoát có chủ đích
thay cho việc người ta xoá file state bằng tay (rồi quên nó tồn tại).

## Liên hệ với bài toán lớn hơn

Trigger theo dữ liệu chỉ là một trong ba (lịch, dữ liệu, cảnh báo). Cả ba nên đi qua cùng một cổng kiểm tra trước khi train;
bài Advanced 01 hỏi cổng đó nên quyết định thế nào.

## Lỗi hay gặp

- Hash theo mtime hoặc kích thước tệp.
- Đếm "dòng mới" bằng cách so số dòng giữa hai lần mà không tính tệp bị cắt bớt (số âm: nên bỏ qua, không train).
- Không phân biệt "bỏ qua" và "lỗi" trong kết quả trả về, làm dashboard không thấy khác biệt giữa hệ thống khoẻ và hệ thống hỏng.
