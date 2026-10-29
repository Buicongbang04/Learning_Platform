# Báo cáo: NYC Yellow Taxi 2019 với Spark

## Bộ dữ liệu

- Nguồn: NYC Taxi & Limousine Commission, trang TLC Trip Record Data (dữ liệu mở của thành phố New York,
  dùng tự do). Bộ `nyc-tlc` ghim 12 tệp `yellow_tripdata_2019-01..12.parquet` (1,24 GB, nén GZIP) và
  `taxi_zone_lookup.csv` (265 zone, kèm borough và `service_zone`).
- 84 598 444 chuyến Yellow Taxi, mỗi dòng là một chuyến do máy tính tiền trên xe ghi: giờ đón/trả (giờ đồng
  hồ New York, không kèm múi giờ), quãng đường (dặm), zone đón/trả, cách trả tiền, cước, tip, tổng tiền.
  Tệp gốc có 19 cột, bài dùng 10.
- Mỗi tệp tháng chỉ có **một row group** (~100 MB): Spark đọc mỗi tệp bằng đúng một task, nên 12 tệp cho
  17 partition đầu vào dù máy có 16 nhân. Muốn đọc song song hơn phải ghi lại với row group nhỏ hơn.

## Làm sạch

- Loại 1 215 835 chuyến (1,44%), mỗi chuyến một lý do, luật đứng trước thắng:
  - `bad_distance` 677 276 (0,80%): gần như toàn bộ là quãng đường bằng 0 (đồng hồ bật rồi huỷ, hoặc GPS hỏng);
  - `bad_duration` 302 998 (0,36%): trả khách trước hoặc đúng lúc đón, hoặc chuyến dài hơn 3 giờ (quên tắt đồng hồ);
  - `bad_amount` 161 874 (0,19%): cước âm là các giao dịch hoàn tiền/huỷ ghi thành dòng riêng, cước 0, hoặc trên 500 USD;
  - `too_fast` 72 245 (0,085%): nhanh hơn 80 dặm/giờ, vd. 5 dặm trong 1 phút;
  - `out_of_period` 1 442: chuyến "năm 2001", "2008" (202), "2009" (402), "2018" (366), "2020" (428), thậm chí "2090".
- 3 973 chuyến năm 2019 nằm trong tệp của **tháng khác** (bản ghi gửi trễ: tệp tháng 2 có chuyến của 31/01 và
  của tháng 3–9). Vì vậy partition theo `pickup_date` tính từ dữ liệu, không theo tên tệp; và ghi đè cả thư mục
  đầu ra (không ghi đè từng tháng một cách ngây thơ, sẽ mất các chuyến trễ đó).
- Không dedup: chuyến không có khoá, chỉ có 50 dòng trùng hệt nhau trên 84,6 triệu, mà `dropDuplicates` trên cả
  bộ tốn ~1 phút shuffle. Thiếu `passenger_count` (444 383 chuyến) không phải lý do loại vì không dùng cột này.
- Dữ liệu sạch: 83 382 609 chuyến ở `data/clean/nyc-tlc/yellow_2019/`, partition theo `pickup_date`:
  365 thư mục, đúng 365 tệp, 1,48 GB. Lớn hơn tệp gốc dù ít cột hơn vì Spark mặc định nén Snappy (giải nén nhanh)
  còn TLC nén GZIP (nhỏ hơn); muốn nhỏ thì đặt `compression="zstd"`.

## Insight

1. **Giờ cao điểm là 18h**: 5 478 973 chuyến cả năm (6,6% tổng số), giờ vắng nhất là 4h với 637 354 chuyến,
   chênh 8,6 lần. Ngày thường có hai đỉnh (8h: ~12 457 chuyến/ngày, 18h: ~15 853), cuối tuần lệch hẳn sang đêm:
   lúc 2h sáng cuối tuần có ~6 938 chuyến/ngày, gần 4 lần ngày thường (~1 775). Taxi Manhattan ngày thường
   chở người đi làm, cuối tuần chở người đi chơi về.
2. **Tip tiền mặt không được ghi lại**: chuyến trả thẻ có tip trung bình 22,77% tiền cước và 96,3% chuyến có tip;
   chuyến tiền mặt (22,5 triệu chuyến, 27% tổng) có `tip_amount` bằng 0 ở 99,99% chuyến. Đây là lỗi
   **thu thập dữ liệu**, không phải hành vi: mọi phân tích tip phải lọc chuyến thẻ, nếu không tỉ lệ tip tính trên mọi chuyến chỉ còn 16,48%,
   thấp hơn thực tế hơn một phần tư.
3. **Tip theo borough nơi đón (chuyến thẻ)**: Manhattan 23,46%, Queens 20,73% (88% chuyến thẻ đón ở Queens là đón ở JFK/LaGuardia), Brooklyn 14,14%,
   Staten Island 3,62%, Bronx chỉ 2,71%. Manhattan chiếm 55,2 triệu / 60,1 triệu chuyến thẻ; Yellow Taxi gần
   như là dịch vụ của Manhattan; ở Bronx và Staten Island số chuyến thẻ quá ít (76 nghìn, 2 nghìn) để so sánh nhiều.
4. **Sân bay**: 6 418 240 chuyến (7,7%) đón hoặc trả ở JFK, LaGuardia hoặc Newark, cước trung bình 40,07 USD,
   gấp 3,6 lần chuyến thường (11,01 USD). Số chuyến ít nhưng chiếm 23,3% tổng tiền cước.
5. **Tối ưu đo được** (một lần chạy, máy 16 nhân):
   - broadcast bảng zone: 1,4 giây so với 7,0 giây khi ép sort-merge join (shuffle 60 triệu chuyến thẻ), nhanh 5 lần;
   - ghi tháng 1 từ dữ liệu rải 64 partition: cách ngây thơ sinh 1 984 tệp cho 31 ngày (64 tệp/ngày), `repartition`
     theo ngày chỉ 31 tệp và ghi nhanh gần 3 lần (2,4 so với 6,9 giây); đọc lại cũng nhanh hơn ~6 lần;
   - partition pruning: đếm chuyến ngày 04/07 (121 564 chuyến) mất 13,3 giây từ tệp gốc (quét 12 tháng),
     0,04 giây từ dữ liệu đã partition. Đây là tối ưu lớn nhất, và nó đến từ thiết kế layout, không phải từ code truy vấn.

## Giới hạn

- Chỉ là Yellow Taxi: Uber/Lyft (dữ liệu FHV) chở nhiều chuyến hơn Yellow Taxi từ 2019 và không có ở đây, nên
  "giờ cao điểm" hay "tip theo borough" là của taxi vàng, không phải của toàn bộ đi lại ở New York.
- Tip tiền mặt không quan sát được, tip theo borough chỉ đại diện cho chuyến trả thẻ.
- Các ngưỡng 3 giờ, 100 dặm, 500 USD, 80 dặm/giờ là lựa chọn của bài, đổi ngưỡng sẽ đổi vài chục nghìn chuyến;
  một pipeline thật nên lưu chuyến bị loại kèm lý do (bảng quarantine) thay vì bỏ hẳn.
- Zone 264/265 ("Unknown", "N/A") chứa ~500 nghìn chuyến thẻ không rõ vị trí; giờ là giờ đồng hồ New York nên hai
  đêm đổi giờ mùa hè có giờ thiếu/giờ lặp.
- Thời gian ở mục 5 phụ thuộc máy và cache của hệ điều hành; so sánh tương đối mới có ý nghĩa, và test chấm bằng plan
  và số tệp, không bằng đồng hồ.
