# Lời giải: giám sát drift cho model review xấu

Notebook lời giải: `drift_monitor.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Kết quả drift train → test (2018-04 tới 2018-08)

| Feature | PSI | KS | Mức |
| --- | --- | --- | --- |
| `freight` | 0.318 | 0.186 | major |
| `promised_days` | 0.296 | 0.223 | major |
| `delivery_days` | 0.224 | 0.211 | moderate |
| `approve_hours` | 0.219 | 0.177 | moderate |
| `delay_days` | 0.073 | 0.079 | stable |
| `customer_state` | 0.023 | | stable |
| `price` | 0.014 | 0.030 | stable |

Đọc từng cái:

- **`freight` tăng**: trung vị phí vận chuyển mỗi đơn từ 16.6 BRL (train) lên 18.4 BRL (test), trong
  khi `price` gần như không đổi. Đây là thay đổi thật của thị trường (giá cước), không phải lỗi dữ
  liệu. Hệ số chuẩn hoá của `freight` trong model (C = 1.0) chỉ −0.008, so với 0.50 của `delivery_days`
  và 0.37 của `delay_days`, nên drift lớn ở feature này gần như không ảnh hưởng tới score.
- **`promised_days` giảm**: trung vị số ngày hẹn giao từ 23.7 (train) xuống 13.5 ở tháng 8/2018.
  Olist hứa giao nhanh hơn. Kéo theo `delay_days` (giao thật trừ ngày hẹn) dễ dương hơn.
- **`delay_days` ổn định trên cả giai đoạn nhưng không ổn định theo tháng**: PSI tháng 3/2018 là
  0.50 (21% đơn trễ), tháng 6/2018 là 0.65 (chỉ 1.4% đơn trễ), tháng 8/2018 là 0.67. Gộp nhiều
  tháng lại thì các chiều trôi triệt tiêu nhau. Bài học: giám sát theo cửa sổ ngắn, không chỉ một
  con số cho cả giai đoạn.

## Score và AUC theo tháng

| Tháng | Tỉ lệ trễ | Review xấu | PSI score | AUC | AUC đơn đúng hẹn |
| --- | --- | --- | --- | --- | --- |
| 2018-01 | 6.5% | 13.7% | 0.010 | 0.748 | 0.662 |
| 2018-03 | 21.1% | 21.2% | 0.193 | 0.819 | 0.647 |
| 2018-06 | 1.4% | 10.0% | 0.465 | 0.667 | 0.646 |
| 2018-07 | 4.3% | 9.7% | 0.199 | 0.658 | 0.604 |
| 2018-08 | 10.3% | 9.5% | 0.242 | 0.710 | 0.642 |

AUC toàn cục chạy từ 0.66 tới 0.82, nhưng AUC trong nhóm đơn đúng hẹn chỉ từ 0.60 tới 0.66. Model
không tệ đi theo kiểu "quan hệ giữa feature và nhãn đã đổi" (concept drift); cái đổi là **tổ hợp**:
tháng nhiều đơn trễ thì dễ phân biệt vì `delay_days` là tín hiệu mạnh. Tách theo giai đoạn cũng thấy
vậy: AUC train / val / test là 0.717 / 0.799 / 0.696, còn trong nhóm đơn trễ là 0.729 / 0.738 /
0.741.

## Khuyến nghị mẫu

> Tháng 6/2018 có PSI `delay_days` 0.65 và PSI của score 0.47, mức "major", nhưng nguyên nhân là
> gần như không đơn nào trễ: drift có lợi cho khách, không phải sự cố. Không retrain chỉ vì cảnh
> báo này. `freight` và `promised_days` trôi kéo dài từ tháng 4 do thay đổi thật của giá cước và
> chính sách hẹn giao; theo dõi tiếp, và đưa dữ liệu 2018 vào lần retrain kế tiếp. AUC toàn cục
> giảm từ tháng 6 chủ yếu do tổ hợp đơn trễ/đúng hẹn; báo cáo AUC tách theo nhóm và theo dõi
> calibration (score trung bình so với tỉ lệ review xấu thật) thay vì một con số AUC. Đề xuất cảnh
> báo hai tầng: PSI từ 0.25 trên feature quan trọng hoặc trên score gửi kênh của team DS để điều tra
> trong tuần; tỉ lệ thiếu dữ liệu hoặc giá trị lạ (lỗi pipeline) gửi on-call ngay. Retrain theo
> lịch hằng quý, sớm hơn nếu AUC trong nhóm (đúng hẹn hoặc trễ) giảm quá 0.03 trong hai tháng liên
> tiếp. Review về sau khi giao khoảng 2 ngày (trung vị; 90% trong vòng 5.3 ngày), nên AUC của một
> tuần chỉ tính được sau khoảng 1 tuần; trong lúc chờ, PSI của feature và score là tín hiệu sớm.

## Rubric cho phần khuyến nghị

| Tiêu chí | Đạt khi |
| --- | --- |
| Phân loại drift | Phân biệt drift có hại / vô hại / có lợi, có lý do từ dữ liệu |
| Mix shift | Nhận ra AUC toàn cục đổi do tổ hợp, dẫn chứng bằng AUC trong nhóm |
| Cảnh báo | Có chỉ số, ngưỡng, người nhận, mức độ khẩn cấp |
| Retrain | Có điều kiện cụ thể, không phải "retrain khi drift" |
| Label delay | Nói được hệ quả: metric hiệu năng đến trễ, cần tín hiệu thay thế |

## Sai lầm hay gặp

- Tự động retrain mỗi khi PSI vượt ngưỡng: tháng 6/2018 sẽ retrain trên một tháng gần như không có
  đơn trễ, model mới kém hơn khi đơn trễ quay lại.
- Giám sát drift trên mọi feature với cùng mức ưu tiên: drift ở feature mà model gần như không dùng
  (hệ số nhỏ) ít quan trọng hơn drift ở `delay_days`.
- Đọc tháng gần nhất như tháng bình thường: đơn mua cuối tháng 8 chỉ có mặt trong bảng nếu đã giao
  xong trước khi dữ liệu bị cắt, nên tháng cuối nghiêng về đơn giao nhanh.
