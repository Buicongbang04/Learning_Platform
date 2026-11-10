# Hướng làm và rubric: tự dựng hay cloud

`DECISION.md` cạnh tệp này là một lời giải tham khảo. Với giả định khác, đáp án hợp lý có thể là Lai hoặc Tự dựng; chấm lý luận và tính nhất quán, không chấm phương án.

## Hướng làm

1. **Ràng buộc của case trước, công cụ sau.** 4 người ML, 0.5 kỹ sư nền tảng, 2 model tăng lên 10, dữ liệu đã trên cloud. Ba dữ kiện này đẩy trọng số vào chi phí vận hành, tốc độ ra production và mở rộng; "tuỳ biến" và "lock-in" quan trọng nhưng ở đội nhỏ chúng là rủi ro dài hạn hơn là đau đớn hôm nay.
2. **Trọng số trước, điểm sau.** Cộng bằng 100, đặt trước khi chấm. Điểm số nguyên 1 đến 5, mỗi điểm truy về một dữ kiện (vd. Cloud 5 ở vận hành vì kỹ sư nền tảng chỉ rảnh 50%).
3. **Chi phí 24 tháng gồm nhân công.** Tự dựng có hạ tầng rẻ nhưng 16 giờ vận hành mỗi tháng (1200 USD) và hai tháng dựng ban đầu; Cloud ngược lại. Điểm hoà vốn ((18000 - 6000) / (3100 - 1900) = tháng 10) cho biết lựa chọn "rẻ hơn" phụ thuộc vào độ dài thời gian bạn nhìn: nếu kế hoạch chỉ 9 tháng, Cloud thắng về tiền.
4. **Khuyến nghị lệch khỏi điểm số cũng được, nếu nói rõ.** Cụm `lệch khỏi điểm số` bắt người viết thừa nhận khi quyết định không theo ma trận (vd. vì ràng buộc cứng mà tiêu chí chưa bắt được) thay vì chỉnh điểm cho khớp ý đã có.
5. **Điều kiện đổi hướng là thứ kiểm được.** "Khi lớn hơn" không dùng được; "hoá đơn endpoint trên 4500 USD trong 2 tháng liên tiếp" thì có người theo dõi được và có ngày để quyết định.
6. **Lock-in là chi phí rời, không phải lời chê.** Ước lượng bằng thời gian chuyển đi (khoảng 1 tháng) và giảm bằng định dạng mở ngay từ đầu.

## Rubric (tối đa 100 điểm)

| Mục | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Bối cảnh và giả định | 10 | giả định giá, nhân công, vùng dữ liệu nêu rõ và dùng lại ở các phần sau |
| Ma trận tiêu chí | 25 | trọng số phản ánh ràng buộc của case; điểm truy được về dữ kiện; có tiêu chí vận hành và chi phí |
| Chi phí 24 tháng và hoà vốn | 25 | có nhân công; tổng và điểm hoà vốn đúng; có nhận xét về độ nhạy (đổi giả định thì sao) |
| Khuyến nghị | 15 | nhất quán với ma trận hoặc giải thích vì sao lệch |
| Điều kiện đổi hướng | 15 | có ngưỡng số, có chủ theo dõi hay chỉ số theo dõi |
| Rủi ro | 10 | lock-in, chi phí nhàn rỗi, và ít nhất một rủi ro riêng của phương án khuyến nghị |

Trừ điểm: coi nhân công vận hành bằng 0 (-10); trọng số đặt sau khi biết phương án mình thích (khó kiểm, nhưng ma trận có dấu hiệu "xếp điểm cho khớp"): -5; điều kiện đổi hướng không có số (-5); bỏ qua dữ kiện dữ liệu đã nằm trên cloud (-5). Mức đạt: 70/100.
