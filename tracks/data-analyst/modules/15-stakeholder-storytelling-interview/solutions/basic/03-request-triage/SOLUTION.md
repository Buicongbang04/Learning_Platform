# Lời giải: phân loại và xếp lịch hàng đợi yêu cầu

## Cách làm

- `classify` là một chuỗi `if` theo đúng thứ tự quy tắc. Thứ tự quan trọng: một yêu cầu đã có trên dashboard là
  self-serve **dù** chưa rõ quyết định (gửi link mất 5 phút, không cần hỏi lại); một yêu cầu chưa rõ quyết định thì
  hỏi lại **dù** nó lặp lại hay lớn (chưa biết làm gì thì chưa nên dựng dashboard hay viết plan).
- Hàm phụ `_missing` gom ba dạng "trống": `None`, `NaN` (ô trống CSV) và chuỗi chỉ có khoảng trắng.
- `quadrant` là hai phép so sánh ngưỡng.
- `prioritize` thêm ba cột trên bản sao, tách phần "tốn giờ" (`dashboard`, `project`, `ad-hoc`) khỏi phần trả lời
  ngay (`self-serve`, `clarify`), sắp phần đầu theo (góc phần tư, score giảm, id), ghép lại.
- `plan_week` duyệt tham lam, bỏ money pit và việc không vừa giờ còn lại.

## Kết quả trên `backlog.csv`

| Nhóm | Yêu cầu |
| --- | --- |
| Quick win | R04 (dashboard giao trễ, 1.33), R09 (khách sỉ giảm mua, 1.00), R01 (doanh thu theo nước, 0.83) |
| Big bet | R08 (hoàn hàng khớp kế toán, 0.50), R05 (email, 0.33), R10 (SKU bán chậm, 0.20) |
| Fill-in | R12 (đơn tăng đột biến, 3.00), R07 (wishlist, 1.50) |
| Money pit | R06 (hoa hồng 3 năm trước, 40 giờ) |
| Trả lời ngay | R02, R11 (self-serve: gửi link); R03 (hỏi lại quyết định) |

Lịch 30 giờ: R04, R09, R01, R08 (23 giờ), R05 (12 giờ) và R10 (20 giờ) không vừa phần còn lại, rồi R12, R07: tổng 26
giờ. Bốn giờ dư là chỗ cho việc phát sinh, đúng ý đồ: lịch kín 100% sẽ vỡ ở yêu cầu khẩn đầu tiên.

## Đọc kết quả như một DA

- **Score không đủ một mình.** R12 có score cao nhất (3.0) nhưng impact 3; nếu chỉ sắp theo score, fill-in sẽ chiếm
  đầu tuần. Sắp theo góc phần tư trước giữ quick win và big bet lên trên.
- **Tin nhắn cho người không được xếp lịch** là một phần của quy trình: R05 và R10 nhận "tuần sau, vì tuần này ưu
  tiên báo cáo hội đồng quản trị (R08)"; R06 nhận đề xuất rẻ hơn (chỉ đối chiếu đúng khiếu nại đó, không tính lại 3
  năm); R03 nhận bản nháp câu hỏi ("chị đang cân nhắc chương trình gì cho nhóm khách nào?").
- **Ngưỡng là quyết định của team**, không phải chân lý: nửa ngày cho dự án, 8 giờ cho effort thấp. Ghi ngưỡng thành
  hằng số trong code là cách để team thấy và tranh luận về chúng.
- **Impact do người hỏi khai thường bị thổi phồng.** Trong thực tế, DA hoặc trưởng nhóm chấm lại impact bằng câu "nếu
  kết quả là X thì anh/chị làm gì khác".
