# Đánh giá M13: tháng dữ liệu lạ 2019-10

## Tóm tắt

Tệp 2019-10 nhận về có ba lỗi dữ liệu chồng lên nhau, không có thay đổi hành vi đi lại nào: một phần chuyến bị đảo pickup
và dropoff (`clock_error`), khoảng cách bị ghi bằng km thay vì dặm (`unit_change`), và cả hai cột thời gian bị ghi theo
UTC thay vì giờ New York (`timezone_shift`). Champion (version 1, train trên 2019-08) có MAE 308.0 s trên tháng này, so
với 204.0 s của 2019-09, bias đổi dấu từ -72 s sang +163 s. Khi đảo ngược hai lỗi khoảng cách và giờ trên một bản sao
của tháng, MAE về 198.9 s: model không hỏng, dữ liệu hỏng.

Quyết định: `keep` champion, `quarantine: true` cho tháng 2019-10 (không dùng để train, không dùng để đánh giá promotion,
không đưa vào bảng drift tham chiếu), mở sự cố với nhóm nguồn dữ liệu kèm ba bằng chứng bên dưới.

## Cách điều tra

Theo khung của module 10: phát hiện, xác minh, đo tác động, rồi mới quyết định. Mọi số dưới đây chạy lại được bằng
`make assessment` (cấu hình `params.assessment.yaml`: train trên 2019-08, mẫu 50 000 chuyến, `seed=0`, `max_iter=100`).

1. Cổng dữ liệu của M03, chạy trước mọi thứ khác:

   ```bash
   python -m eta.cli prepare --config params.assessment.yaml --month 2019-10 --out data/assessment-interim/2019-10.parquet
   python -m eta.cli validate data/assessment-interim/2019-10.parquet --month 2019-10
   ```

   Kết quả: exit 1, `FAIL ... <dataframe>: negative_duration_share > 1%`. Trong pipeline DVC, tháng này đã bị chặn trước
   bước train; đây là tín hiệu đầu tiên, nhưng validation chỉ nói "có ít nhất một lỗi", không nói "chỉ có một lỗi".

2. Phát lại có tháng trước và tháng sau làm đối chứng (M05 và M10):

   ```bash
   python -m eta.cli replay --config params.assessment.yaml --start 2019-09 --end 2019-11 --out reports/assessment/replay
   ```

   | Tháng | PSI `trip_distance` | KS `trip_distance` | PSI giờ đón | PSI `eta_s` | MAE (s) | bias (s) |
   | --- | --- | --- | --- | --- | --- | --- |
   | 2019-09 | 0.0016 | 0.017 | 0.0005 | 0.0048 | 204.0 | -72.2 |
   | 2019-10 | 0.2646 | 0.223 | 0.3310 | 0.1361 | 308.0 | +163.2 |
   | 2019-11 | 0.0045 | 0.029 | 0.0003 | 0.0076 | chưa có nhãn | |

   Tháng sau trở lại bình thường ngay: đây không phải xu hướng mà là một tháng hỏng.

3. Xác minh từng giả thuyết trên mẫu thô (cùng `load_month` với `sample_rows=50000`, `seed=0`), so với 2019-09: median
   khoảng cách, giờ có nhiều chuyến nhất, tỉ lệ chuyến ngoài tháng, chuyến sớm nhất của ngày 1, và cột `VendorID` của các
   dòng thời lượng âm (đọc thẳng tệp parquet, vì `load_month` chỉ giữ 5 cột).

4. Đo tác động từng lỗi bằng cách đảo ngược nó trên một bản sao tháng rồi phát lại:

   | Bản sao | MAE (s) | bias (s) |
   | --- | --- | --- |
   | Tháng lạ nguyên trạng | 308.0 | +163.2 |
   | Chỉ sửa khoảng cách | 261.9 | -134.2 |
   | Chỉ sửa giờ | 318.4 | +242.0 |
   | Sửa cả hai | 198.9 | -75.1 |
   | Tháng thật 2019-10 (đối chứng) | 197.8 | -73.3 |

   Hai lỗi kéo bias theo hai hướng ngược nhau và che bớt nhau: chỉ nhìn bias +163 s dễ kết luận "đường chậm hơn", một
   nguyên nhân hành vi không có thật.

## Phát hiện

- **`clock_error`**: 3.59% chuyến có dropoff trước pickup (2019-09: 0%), tất cả thuộc `VendorID == 1`, nằm trong ba ngày
  15 tới 17/10. Validate chặn đúng. Đây là lỗi thiết bị của một hãng, không phải lỗi của cả tệp.
- **`unit_change`**: PSI `trip_distance` 0.265 (ngưỡng thường dùng 0.1, các tháng khác dưới 0.005); median 2.67 so với
  1.68, tỉ lệ 1.59, khớp 1.609 km mỗi dặm. Model hiểu "chuyến 2.67 dặm" nên đoán dài hơn: PSI `eta_s` 0.136.
- **`timezone_shift`**: PSI giờ đón 0.331; giờ đông nhất dời từ 18 sang 22 (đúng 4 giờ, độ lệch UTC của EDT); chuyến sớm
  nhất trong mẫu ngày 1/10 lúc 03:49 và 0.67% chuyến rơi sang ngày 1/11 (2019-09: 0.006%). Validate không chặn vì 0.67%
  vẫn dưới ngưỡng 1% của check "pickup ngoài tháng": ngưỡng đủ cho rác ngẫu nhiên, không đủ cho lệch có hệ thống.
- Đã loại: `outside_month` (chuyến ngoài tháng chỉ nằm trong 4 giờ đầu ngày 1/11, hệ quả của lệch giờ, không phải chuyến
  của tháng khác), `concept_drift` và `seasonal_drift` (sửa dữ liệu thì MAE về mức tháng thật), `duplicate_rows` (0.004%
  như nhiễu thường), `missing_zone` và `truncated_month` (đủ 31 ngày, tỉ lệ zone lớn như tháng trước).

## Quyết định

`keep` champion, `quarantine: true`. Train lại sẽ đưa đơn vị km và giờ UTC vào model; rollback không có nghĩa vì
champion không đổi suốt phát lại và vẫn đúng trên dữ liệu đúng (198.9 s). Trong lúc chờ tệp sửa, API realtime không bị ảnh
hưởng vì yêu cầu realtime không đi qua tệp này; chỉ batch tháng 2019-10 và báo cáo chất lượng bị hoãn.

## Phòng ngừa

- Thêm vào schema Pandera của M03: median `trip_distance` trong khoảng 1.2 tới 2.2 dặm, tỉ lệ chuyến trong 6 giờ đầu ngày 1
  của tháng, và PSI giờ đón so với tháng tham chiếu dưới 0.1 trước khi cho train.
- Tách ngưỡng theo hãng (`VendorID`): lỗi của một hãng 34% số chuyến bị pha loãng khi tính trên cả tệp.
- Alert `EtaPredictionShift` của M09 (dịch chuyển phân phối `eta_s`) sẽ bắn nếu tháng này đi qua API; runbook cần một nhánh "kiểm dữ liệu đầu vào trước khi nghi
  model" với đúng ba lệnh ở mục Cách điều tra.
- Không bao giờ tự sửa dữ liệu nguồn trong pipeline mà không có xác nhận của nhóm nguồn: bản sao đảo ngược ở trên chỉ để
  đo tác động.
