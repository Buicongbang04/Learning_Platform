# M12: Xây một luồng dữ liệu độc lập và xử lý sự cố

## Mục tiêu

Tự chuyển yêu cầu thành hệ thống có thể dựng lại, giải thích và khôi phục. Làm sau phần local
M01–M10; M11/cloud tùy chọn. Đọc lại lý thuyết được, nhưng tự viết thiết kế và code trước khi đối chiếu
lời giải bài cũ. Milestone này không có một kiến trúc hay lời giải mẫu duy nhất.

## Việc cần làm

### Yêu cầu từ nhóm vận hành

“Mỗi ngày tôi cần biết tiền hàng đã giao theo bang và đơn giao trễ. Tôi muốn thấy trạng thái mới
nhất của đơn trong vòng vài phút, và không muốn báo cáo bị sai khi dữ liệu tới muộn hay job chạy lại.”

Tự hỏi và ghi câu trả lời: tiền hàng có tính vận chuyển không, dùng ngày mua hay ngày giao,
bang của khách hay seller, đơn thiếu ngày giao xử lý ra sao, ai có quyền xem dữ liệu chi tiết.
Không tự để SQL quyết định những quy ước này. Có thể đóng cả vai người yêu cầu, nhưng phải ghi giả định.

### Phạm vi và dữ liệu thử

1. Chọn dữ liệu Olist giả, seed cố định, ít nhất 2.000 đơn và ba ngày nghiệp vụ. Giữ raw để replay.
2. Thiết kế một pipeline batch tới bảng serving và một luồng cập nhật trạng thái. Dùng CDC lab
   hoặc event giả lập; ghi rõ đã chọn cách nào, không gọi event giả là đã kiểm chứng CDC nguồn.
3. Tự chọn công cụ từ những gì đã học. Không cần dùng hết MongoDB, Cassandra, Spark hay Kubernetes.
   Giải thích lựa chọn theo yêu cầu, dữ liệu, khả năng vận hành và chi phí.
4. Viết contract và bộ số liệu chuẩn có thể tính tay cho tập nhỏ gồm:

| Ca thử | Điều cần kiểm |
| --- | --- |
| Một đơn có nhiều item và hai payment | Tiền không bị nhân khi join |
| Khách/sản phẩm tới sau đơn | Không mất fact, sau đó nối đúng dimension |
| Hai event giống nhau | Không tạo bản ghi hoặc phép cộng trùng |
| Event shipped tới sau delivered | Trạng thái không lùi theo quy tắc đã chọn |
| Ngày không có đơn và ngày thiếu batch | Phân biệt doanh thu 0 với chưa đủ dữ liệu |
| Đơn bị xóa hoặc hủy | Phản ánh đúng trong trạng thái và metric theo contract |
| Cột tiền đổi kiểu/đơn vị | Chặn hoặc chuyển đổi có quy tắc; không xuất bản số sai |

### Tự chọn mục tiêu có thể đo

Ghi mục tiêu độ trễ, số dòng/ngày, RPO và RTO phù hợp máy lab. Ví dụ mục tiêu cập nhật trạng thái
60 giây trong lab, RTO 15 phút; đây là giả định tự đặt, cần đo mới biết có đạt.
Thiết kế cách lấy số đo, nguồn thời gian và điểm bắt đầu/kết thúc. Benchmark bằng dữ liệu nhỏ không
chứng minh đạt cùng tốc độ khi dữ liệu tăng 100 lần.

### Tình huống sự cố bắt buộc

1. Ngắt một job sau khi đã xử lý một phần batch, rồi chạy lại cùng ngày.
2. Chạy lại event/lô trùng và gửi một thay đổi tới muộn.
3. Đưa một thay đổi schema không tương thích vào nguồn lab.
4. Làm hỏng hoặc xóa một bảng **bản sao trong database lab riêng**, khôi phục từ backup/bản nền
   và phần thay đổi còn giữ. Chọn một người khác làm theo runbook nếu có thể.
5. Thử đọc dữ liệu hạn chế bằng danh tính BI; phải bị từ chối tại tầng thực thi quyền.

Trước mỗi sự cố, lưu baseline và khoanh tài nguyên được phép tác động. Sau phục hồi, đối chiếu
tập khóa, tổng tiền theo ngày/bang, trạng thái mới nhất và freshness; chỉ “job đã xanh” chưa đủ.

### Thay đổi yêu cầu cuối bài

Sau khi bản đầu ổn định, thêm yêu cầu “xem cả đơn chưa giao nhưng chưa hủy”. Tạo metric mới hoặc
phiên bản mới, giải thích vì sao khác metric đã giao. Giữ khả năng kiểm lại báo cáo cũ, migration
có ngày hiệu lực và cách quay lại. Đây là kiểm tra thiết kế khi nghiệp vụ thay đổi.

## Kết quả nộp

- Thư mục dự án riêng do bạn chọn, README có sơ đồ, yêu cầu/giả định, contract, owner và lệnh dựng lại.
- Code, dependency lock, test và dữ liệu thử nhỏ; dữ liệu sinh lớn/secret không commit.
- `EVIDENCE.md`: số đo baseline, kết quả các ca thử, log sự cố/phục hồi và đối chiếu sau cùng.
- `RUNBOOK.md`: triệu chứng, nơi xem log, hành động, rollback/restore, điều kiện kết thúc sự cố.
- `DECISIONS.md`: ít nhất ba quyết định và phương án khác đã cân nhắc.
- `COST.md`: tài nguyên local đã dùng; nếu chọn cloud, ghi giá/region/ngày ước tính và bằng chứng dọn.

## Tiêu chí đạt

Tự chấm theo bằng chứng; mỗi nhóm chỉ nhận điểm khi có kết quả kiểm chứng, không chỉ có lời hứa.

| Nhóm | Điểm tối đa | Bằng chứng cần có |
| --- | --- | --- |
| Đúng nghiệp vụ và dữ liệu | 25 | Bộ chuẩn, đối chiếu khóa/tiền/trạng thái, quy tắc NULL và thời gian |
| Chạy lại và dữ liệu tới muộn | 20 | Retry/replay/backfill không thiếu hoặc trùng |
| Khôi phục và vận hành | 20 | Timeline, backup/restore thử thật, RPO/RTO quan sát, runbook |
| Thiết kế và giải thích | 15 | Grain, contract, đánh đổi công cụ và phiên bản metric |
| Bảo mật | 10 | Quyền cho phép/từ chối, secret không trong mã/log chia sẻ |
| Dựng lại và bàn giao | 10 | README đủ lệnh, dependency, fixture, giới hạn đã ghi |

- [ ] Tối thiểu 75/100 theo rubric và không bỏ ca sự cố bắt buộc.
- [ ] Không mất/nhân đôi tiền trên tập chuẩn sau phục hồi.
- [ ] Không lộ dữ liệu hạn chế trong bài kiểm quyền.
- [ ] Dựng lại được bằng tài liệu; test quan trọng chạy được trên dữ liệu nhỏ.
- [ ] Phân biệt rõ phần đã chạy thật, phần mô phỏng và phần mới là thiết kế.

Đây là đánh giá nội bộ của lộ trình, không phải chứng chỉ hay cam kết tuyển dụng. Nếu chưa đạt,
ghi ca lỗi cụ thể và quay lại module liên quan để sửa, rồi chạy lại ca đó.
