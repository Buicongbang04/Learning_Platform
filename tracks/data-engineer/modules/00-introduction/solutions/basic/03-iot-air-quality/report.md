# Báo cáo: UCI Air Quality, cảm biến khí ở Ý (03/2004 - 04/2005)

## Bộ dữ liệu

- Nguồn: UCI Machine Learning Repository #360 (De Vito và cộng sự), giấy phép CC BY 4.0.
- 9 357 dòng theo giờ, từ 2004-03-10 18:00 tới 2005-04-04 14:00, không thiếu giờ nào trong chuỗi thời gian.
- Mỗi dòng: 5 cảm biến oxit kim loại giá rẻ (`s1_co` ... `s5_o3`, tín hiệu thô), 5 nồng độ "ground truth"
  từ máy phân tích chuẩn (CO, NMHC, C6H6, NOx, NO2), nhiệt độ và độ ẩm. Trạm đặt ở mặt đường, một thành phố Ý.

## Làm sạch

- Tệp CSV kiểu châu Âu: `;` phân cách, dấu phẩy thập phân, ngày và giờ (`18.00.00`) tách hai cột,
  2 cột rỗng thừa và 114 dòng rỗng cuối tệp: bỏ.
- `-200` là giá trị thiếu: thay bằng null **chỉ đúng giá trị đó** (nhiệt độ âm mùa đông là thật).
- Thiếu có cấu trúc, không ngẫu nhiên:
  - `nmhc_gt` thiếu **90,2%**: máy phân tích NMHC chỉ chạy tới 2004-05-01, sau đó cột này vô dụng;
  - `co_gt` thiếu 18,0%, `nox_gt`/`no2_gt` 17,5%: máy phân tích hỏng theo đợt, nặng nhất 10/2004 (47% giờ thiếu CO);
  - 3,9% giờ (366 giờ, 16 đợt) **cả 5 cảm biến cùng mất**: thiết bị mất điện/kết nối, dài nhất 76 giờ từ 2005-02-08 17:00.
- Kết quả: `data/clean/air-quality-uci/hourly.parquet`, 9 357 dòng, ~0,3 MB.

## Insight

1. **Ô nhiễm theo giờ đi làm**: CO trung bình thấp nhất lúc **5h (0,71 mg/m³)**, vọt lên **2,97 lúc 9h** và
   đỉnh **3,73 lúc 19h**. Hai đỉnh trùng giờ cao điểm giao thông: nguồn chính là xe cộ.
2. **Cuối tuần sạch hơn ~30%**: CO trung bình thứ 2–6 là **2,36**, thứ 7–CN **1,65** mg/m³ (thấp hơn 29,9%).
3. **Tháng 8 sạch nhất**: CO **1,28** mg/m³, thấp nhất trong các tháng đủ dữ liệu, NOx cũng giảm còn ~76 ppb.
   Đó là kỳ nghỉ Ferragosto, thành phố Ý vắng xe.
4. **NOx nhảy bậc từ 09/2004**: trung bình 122 ppb tháng 6 lên 281 tháng 9 và **424 tháng 11** (gấp 3,5 lần),
   trong khi CO chỉ tăng từ 1,9 lên 2,7. Một phần là mùa đông (sưởi, nghịch nhiệt), nhưng bước nhảy đột ngột
   đúng lúc máy phân tích có đợt thiếu dài gợi ý **hiệu chuẩn lại máy NOx**: cần hỏi chủ nguồn trước khi so sánh hai giai đoạn.
5. **Cảm biến rẻ bám theo máy chuẩn nhưng không theo một hệ số cố định**: tương quan `s1_co` với `co_gt` là 0,88,
   nhưng tỉ số tín hiệu/nồng độ theo tháng đi từ ~395 (12/2004) tới ~766 (08/2004). Một phần do đáp ứng phi tuyến
   ở nồng độ thấp, một phần do trôi theo nhiệt độ, độ ẩm và tuổi cảm biến: muốn dùng cảm biến rẻ thay máy chuẩn
   phải hiệu chuẩn định kỳ.

## Giới hạn

- Chỉ một trạm, một thành phố: không khái quát cho đô thị khác.
- Tệp không ghi múi giờ; giờ mùa hè (CEST) có thể làm lệch một giờ ở hai ngày đổi giờ.
- 18% giờ thiếu CO ground truth và thiếu không ngẫu nhiên (theo đợt hỏng máy): trung bình theo tháng 10/2004 kém tin cậy.
- Thay đổi NOx có thể do thiết bị, không chỉ do môi trường; dữ liệu không ghi lịch bảo trì.
