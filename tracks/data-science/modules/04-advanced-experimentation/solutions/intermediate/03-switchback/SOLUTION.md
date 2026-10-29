# Lời giải: network effect và switchback

## Cách làm

- `switchback_schedule`: hoán vị một dãy block 0/1 cân bằng rồi lặp mỗi phần tử `block` lần. Cân
  bằng số block quan trọng hơn ở switchback so với A/B theo user, vì số đơn vị random (block) chỉ
  vài chục đến vài trăm.
- `switchback_estimate`: sắp theo `period`, đánh số đoạn bằng `(treat != treat.shift()).cumsum()`,
  bỏ `burn_in` vị trí đầu mỗi đoạn, Welch trên tỉ lệ đơn mỗi period.
- `user_split_estimate`: Welch trên từng user-period.

## Kết quả mô phỏng (các seed trong test)

| Thiết kế | Ước lượng | So với tác động thật 0.0109 |
| --- | --- | --- |
| A/B theo user | 0.0407 (SE 0.0013) | gấp khoảng 3.7 lần |
| Switchback đổi nhánh mỗi period, không burn-in | 0.0003 | khoảng 2%, gần như mất hẳn |
| Switchback block 6, không burn-in (trung bình 5 lần) | 0.0088 | khoảng 81% |
| Switchback block 6, bỏ 1 period đầu | | khoảng 89% |
| Switchback block 6, bỏ 2 period đầu | 0.0105 | khoảng 96% |

## Vì sao A/B theo user sai

Khi chia user 50/50 trong cùng một period, hai nhánh **dùng chung** 110 shipper. Treatment đặt nhiều
đơn hơn nên chiếm phần lớn shipper: tỉ lệ đơn được phục vụ của treatment là 0.119, của control chỉ
0.078, thấp hơn hẳn mức 0.099 khi không có thí nghiệm. Hiệu 0.04 gồm phần tác động thật **cộng**
phần treatment "cướp" của control. Khi bật cho tất cả, không còn ai để cướp: số đơn bị chặn bởi
110 shipper, tác động thật chỉ 0.011. Đây là vi phạm **SUTVA** (kết quả của một user phụ thuộc
treatment của user khác), và nó không biến mất khi tăng cỡ mẫu: CI hẹp lại quanh con số sai.

## Vì sao cần burn-in

Đơn không được phục vụ trong period treatment đặt lại ở period sau. Nếu period sau là control, nó
nhận thêm hàng chục đơn tồn từ treatment và trông giống treatment. Đổi nhánh mỗi period thì mọi
period đều bị nhiễm, ước lượng gần như về 0. Block dài hơn và bỏ vài period đầu mỗi block cho hệ
thống thời gian về trạng thái ổn định của nhánh mới.

Đánh đổi khi chọn block và burn-in:

| Lựa chọn | Lợi | Hại |
| --- | --- | --- |
| Block ngắn | Nhiều đơn vị random, SE nhỏ, cân bằng giờ trong ngày tốt | Carryover chiếm phần lớn thời gian |
| Block dài | Carryover ít | Ít đơn vị, dễ trùng với xu hướng ngày/giờ, SE lớn |
| Burn-in dài | Ít thiên lệch | Bỏ phí dữ liệu (ở đây bỏ 2/6 = 33% period) |

## Giới hạn của SE trong bài

SE Welch trên từng period coi các period độc lập. Carryover và xu hướng theo giờ làm các period
liền nhau tương quan, nên SE này thường quá nhỏ. Trong thực tế: tính metric theo **block** rồi so
các block, hoặc dùng randomization inference (hoán vị lại lịch switchback nhiều lần, tính lại hiệu,
xem hiệu thật nằm đâu trong phân phối đó), như Bojinov, Simchi-Levi và Zhao đề xuất.

## Bẫy thường gặp

- Chỉ chạy switchback vào giờ thấp điểm: không có nghẽn shipper thì không thấy interference, và
  kết quả không đại diện cho giờ cao điểm.
- Đơn vị phân tích là user nhưng đơn vị random là period: phải phân tích theo period (hoặc block).
- Quên rằng switchback đo **tác động ngắn hạn** trong khung giờ. Hiệu ứng dài hạn (user quen phí
  thấp, shipper đổi giờ làm) cần thí nghiệm theo vùng địa lý kéo dài nhiều tuần.
