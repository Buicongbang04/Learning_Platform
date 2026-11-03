# Hướng làm và rubric: runbook cảnh báo drift

## Hướng làm

1. **Mức nghiêm trọng theo tác động, không theo PSI.** Cảnh báo drift một mình là cấp thấp (xem trong giờ làm việc); nâng lên cao khi có tín hiệu chất lượng (MAE, fallback, dự đoán lệch baseline cùng thứ). Ghi rõ thời gian xác nhận (vd. 30 phút ban ngày, 2 giờ ngoài giờ cho cấp thấp).
2. **Detect.** Kiểm giám sát trước: cỡ mẫu của cửa sổ, baseline cùng thứ, có cửa sổ nào chứa ngày lễ, ngưỡng có vừa bị đổi không. Một báo động giả đã lặp lại ba lần là lỗi của giám sát, mở ticket sửa ngưỡng.
3. **Verify** (làm hết trước khi nghĩ tới model), theo thứ tự rẻ đến đắt: (a) deploy hoặc thay đổi cấu hình trong 48 giờ qua; (b) tỉ lệ thiếu và kiểu dữ liệu từng cột; (c) khoảng giá trị và thứ nguyên của cột bị chạm (so trung vị theo ngày với 7 ngày trước, tỉ số tròn là dấu hiệu); (d) số cột bị chạm
   và có hợp lý về nghiệp vụ không; (e) thời điểm gãy (đột ngột trong một đêm hay trôi dần); (f) hỏi đội sở hữu nguồn. Kết luận của bước này là một trong: lỗi dữ liệu (sửa nguồn, không đụng model), tín hiệu thật, chưa rõ.
4. **Impact.** Khi nhãn chưa về: phân phối dự đoán so với baseline cùng thứ, tỉ lệ fallback, tỉ lệ thiếu feature quan trọng. Khi nhãn về: MAE tổng và theo lát cắt (giờ, khu vực), so với bốn tuần trước; "xấu đi" định nghĩa bằng số
   (vd. MAE tăng trên 15% so với baseline, kéo dài hai ngày liên tiếp). Có bản trước chạy shadow thì so trực tiếp trên cùng lưu lượng.
5. **Decide.** Bảng: `keep` khi tín hiệu là lỗi dữ liệu đã sửa hoặc drift có thật nhưng MAE không xấu đi (hành động: ghi chú, theo dõi, đặt lịch xem lại); `rollback` khi vấn đề bắt đầu cùng một thay đổi gần đây và có phiên bản trước tốt hơn đã đo
   (hành động: chuyển alias registry, xác nhận bằng proxy trong 1 giờ; người duyệt: on-call tự quyết); `retrain` khi chất lượng giảm thật mà không có bản trước tốt hơn (hành động: pipeline train với cửa sổ gần đây, so challenger với champion trên holdout gần đây, shadow trước khi promote; người duyệt: chủ model).
6. **Giao tiếp.** Mẫu cập nhật (đã biết, chưa biết, hành động tiếp, lúc nào cập nhật lại), khi nào kéo đội data hay nền tảng, ngưỡng khai báo sự cố (vd. có tác động tới người dùng hoặc MAE xấu đi liên tục).
7. **Sau sự cố.** Ticket sửa nguyên nhân gốc, cập nhật ngưỡng hay rào (data contract, `range_guard`), postmortem không đổ lỗi khi chất lượng người dùng bị ảnh hưởng hoặc khi cần quyết định lớn (rollback, retrain khẩn).

## Rubric (tối đa 20 điểm)

| Mục | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Kích hoạt và nghiêm trọng | 2 | có ngưỡng, người nhận, thời gian xác nhận; mức nghiêm trọng gắn với tác động |
| Detect | 2 | có kiểm chứng giám sát không sai (cỡ mẫu, baseline, ngày lễ) |
| Verify | 5 | ít nhất bốn kiểm tra loại trừ lỗi dữ liệu theo thứ tự rẻ đến đắt, kết luận rõ ràng sau bước này |
| Impact | 4 | cả đường proxy và đường nhãn, ngưỡng "xấu đi" bằng số, so sánh bản trước nếu có |
| Decide | 4 | ba nhánh, điều kiện đo được, người duyệt, cách kiểm sau hành động; có nhánh không làm gì |
| Giao tiếp và sau sự cố | 3 | mẫu cập nhật, điều kiện khai báo sự cố, việc trong 48 giờ |

Trừ điểm: nhánh mặc định là "retrain" (-3); verify nằm sau decide hoặc chỉ nhắc "kiểm tra dữ liệu" không cụ thể (-3); ngưỡng không có căn cứ (-2); không có hành động cho lúc nhãn chưa về (-2). Mức đạt: 14/20.
