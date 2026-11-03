# Lời giải: SLO và burn-rate alert

Bài Advanced không có đáp án duy nhất. `SLO.md` và `slo.rules.yml` cạnh tệp này là bản mẫu đã chạy qua test; chấm theo chất lượng lập luận.

## Ý chính

- **Burn rate tách "nặng bao nhiêu" khỏi "tỉ lệ lỗi tuyệt đối".** Cùng 1% lỗi: với SLO 99.9% là burn rate 10 (khẩn), với SLO 95% là 0.2 (không đáng kể).
- **Hai cửa sổ.** Cửa sổ dài một mình giữ alert bắn rất lâu sau khi đã sửa; cửa sổ ngắn một mình bắn vì một đợt spike ngắn. `and` cả hai
  cho alert vừa đáng tin vừa tự tắt nhanh. Tỉ lệ 1/12 là quy ước phổ biến.
- **Ba tầng.** Cháy nhanh đánh thức người trực (2% budget trong 1 giờ); cháy chậm chỉ cần ticket. Không có tầng chậm thì sự cố
  rỉ rả 3 ngày đốt hết budget mà không ai biết.
- **Recording rule.** Tính tỉ lệ lỗi một lần cho mỗi cửa sổ, đặt tên theo quy ước `level:metric:operations`, để alert và dashboard dùng lại và truy vấn không nặng.
- **Budget là công cụ chính sách.** Không có hệ quả (freeze) thì SLO chỉ là con số trang trí.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| SLI đo đúng thứ khách thấy | 20 | Ít nhất khả dụng, độ trễ, một SLI riêng của model; định nghĩa PromQL đọc được và không dùng CPU/RAM |
| Toán budget và burn rate | 20 | Budget 216 phút đúng; mỗi dòng bảng burn-rate có % budget tiêu khớp `burn x cửa sổ / 720h` |
| Cấu trúc hai cửa sổ | 20 | `and` giữa cửa sổ dài và ngắn, ngắn bằng 1/12 dài, hằng số khớp bảng; recording rule đặt tên đúng quy ước |
| Chính sách khi hết budget | 20 | Ngưỡng cụ thể, ai ký ngoại lệ, hạn ngoại lệ, postmortem |
| Giới hạn và trung thực | 10 | Nêu traffic thấp, đo từ phía server, SLO không phủ chất lượng dự đoán |
| Rõ ràng | 10 | Bảng ngắn, sơ đồ đúng, không thuật ngữ trần |

Dưới 70: thường vì chọn SLI theo thứ dễ đo (CPU) thay vì thứ khách thấy, hoặc burn rate chép số mà không tự tính được % budget.
