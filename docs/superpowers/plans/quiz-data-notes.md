# Ghi chú số liệu cho câu hỏi dữ liệu (nguồn: report.md lời giải đã xoá ở Task 4)

Mỗi mục: số liệu trên dữ liệu đã ghim, dùng làm đáp án cố định cho câu hỏi `kind: data` (Task 5).
Nguồn gốc: `solutions/<level>/<slug>/report.md` (trước commit Task 4); khôi phục bằng `git show <commit-trước-Task-4>:<đường dẫn>`.

## 00 / basic / 01-api-weather-collection (Open-Meteo ERA5, 2023, TP.HCM + Hà Nội)
- 730 dòng sạch (365 ngày x 2 thành phố); không ngày null/trùng.
- Biên độ nhiệt năm (tháng nóng nhất - tháng lạnh nhất): Hà Nội 13,6 C (17,1 tháng 1 -> 30,8 tháng 7); TP.HCM 3,3 C (26,2 -> 29,5); gấp hơn 4 lần.
- TP.HCM nóng nhất tháng 4 (trước mùa mưa); Hà Nội nóng nhất tháng 7.
- Ngày tmax >= 35 C: Hà Nội 47 ngày, đỉnh 39,8 C ngày 17/05/2023; TP.HCM 7 ngày, cao nhất 36,1 C.
- Mưa tháng 5-10: TP.HCM 82% (1 826 mm/năm), Hà Nội 84% (1 502 mm/năm). Ngày mưa >= 1 mm: TP.HCM 220, Hà Nội 151. Tháng 3 TP.HCM 1,4 mm.
- Kiến thức: lưu response thô trước khi parse; ERA5 là tái phân tích lưới ~25 km, không phải số đo trạm; ô lưới gần nhất (10.75,106.75) và (21.0,105.75).

## 00 / basic / 02-web-server-logs (NASA HTTP log, 07/1995)
- 1 891 715 dòng thô; 6 dòng hỏng; 1 891 709 dòng sạch; 3 604 request không có protocol; 835 dòng trùng hệt (giữ, là request thật).
- Dữ liệu từ 01/07 00:00:01 tới 28/07/1995 13:32:25 (thiếu ~3,4 ngày cuối tháng).
- 13/07/1995 (Discovery STS-70 phóng): 134 203 request so với trung bình 76 237/ngày thường; khoảng lặng dài nhất 22,1 phút từ 19:48:59.
- Giờ đỉnh 14h, đáy 5h (giờ miền Đông; ~122 500 vs ~31 900 request cả tháng). Cuối tuần 45 871 request/ngày, thấp hơn ngày thường 40%.
- 404: 10 845 request (0,6%); đứng đầu `/pub/winvn/readme.txt` 667 lần (~6% lỗi 404).
- 38,7 GB trả về, 81 982 host; host .com 13,2 GB (bốn ISP quay số 4,7 GB), host IP 7,8 GB.
- Kiến thức: timestamp lưu UTC; `bytes = -` thành 0; một host không phải một người (proxy AOL).

## 00 / basic / 03-iot-air-quality (UCI Air Quality #360)
- 9 357 dòng theo giờ, 2004-03-10 18:00 tới 2005-04-04 14:00.
- `-200` là giá trị thiếu (chỉ đúng giá trị đó). Thiếu: nmhc_gt 90,2%; co_gt 18,0%; nox_gt/no2_gt 17,5%; 10/2004 thiếu CO 47% giờ.
- 366 giờ (3,9%, 16 đợt) cả 5 cảm biến cùng mất; dài nhất 76 giờ từ 2005-02-08 17:00.
- CO trung bình: 5h 0,71 mg/m3; 9h 2,97; đỉnh 19h 3,73.
- CO thứ 2-6 2,36; thứ 7-CN 1,65 (thấp hơn 29,9%).
- Tháng 8 sạch nhất: CO 1,28 mg/m3 (Ferragosto), NOx ~76 ppb.
- NOx: 122 ppb (tháng 6) -> 281 (tháng 9) -> 424 (tháng 11), gấp 3,5 lần; CO chỉ 1,9 -> 2,7; nghi hiệu chuẩn lại máy.
- Tương quan s1_co với co_gt 0,88; tỉ số tín hiệu/nồng độ theo tháng ~395 (12/2004) tới ~766 (08/2004).

## 00 / intermediate / 01-paginated-incremental-api (USGS M>=4.5, 2024)
- Lượt 1: 7 trang, 6 397 trận, ~5,0 MB JSON; lượt 2 (updatedafter): 1 trang, 1 bản ghi (đúng ở watermark, vì updatedafter tính cả mốc). Thô 6 398 dòng, 6 397 trận.
- Parquet sạch 0,36 MB từ 5 MB JSON.
- Trung vị `updated - time` 70,8 ngày; 100% bản ghi sửa sau > 30 ngày; 1% sau > 715 ngày; 89 trận 2024 còn sửa trong 2026. Watermark phải theo `updated`.
- Lớn nhất: M7,5 Noto Peninsula 2024-01-01; 10 trận M>=7, 99 trận M>=6, 81 trận cờ tsunami.
- Tháng 4: 705 trận (tháng 1: 623, nhiều thứ hai); 169 trận Đài Loan sau M7,4 Hoa Liên 2024-04-02 UTC.
- Indonesia 605 trận, Philippines 427, Nhật Bản 349 (+186 "Japan region").
- Gutenberg-Richter b ~ 1,13 (~13 lần ít hơn mỗi bậc).

## 00 / intermediate / 02-source-profiling (4 nguồn)
- Bản ghi: NASA 1 891 714; IoT 9 357; USGS 6 398 dòng thô / 6 397 trận; Open-Meteo 730.
- Bản ghi/ngày: NASA 68 629; IoT 24,0; USGS 17,5; Open-Meteo 2,0.
- Khoảng cách trung vị: 1 giây; 3 600 giây; ~51 phút; 1 ngày. Khoảng lặng dài nhất: NASA 1 326 giây (13/07 23:48 UTC); IoT 3 600 giây; USGS 13,7 giờ; Open-Meteo 1 ngày.
- Trùng: NASA 835 dòng; IoT 0; USGS 1 id (lấy lại ở watermark); Open-Meteo 0.
- Thiếu: IoT 16 701 ô `-200`, NMHC(GT) 90,2%.
- Byte/dòng thô -> Parquet: NASA 108 -> 7,9 (x13,7); IoT 84 -> 28 (x3,0); USGS 777 -> 25 (x31); Open-Meteo 38 -> 15 (x2,5).
- Thô mỗi năm: NASA 2,7 GB; IoT 0,7 MB; USGS 5 MB; Open-Meteo 28 KB.
- Khuyến nghị: NASA batch theo giờ; IoT push MQTT micro-batch, khoá (sensor_id, ts); USGS pull hằng đêm incremental theo `updated`, upsert theo `id`; Open-Meteo pull hằng ngày. Không nguồn nào cần streaming theo số đo. Velocity NASA gấp ~2 900 lần IoT.

## 06 / intermediate / 04-nyc-taxi-real (Yellow Taxi 2019)
- Nguồn 12 tệp 1,24 GB GZIP, 84 598 444 chuyến, 265 zone, 19 cột (dùng 10). Mỗi tệp tháng một row group (~100 MB): 12 tệp -> 17 partition đầu vào.
- Loại 1 215 835 chuyến (1,44%): bad_distance 677 276 (0,80%); bad_duration 302 998 (0,36%); bad_amount 161 874 (0,19%); too_fast 72 245 (0,085%); out_of_period 1 442.
- 3 973 chuyến 2019 nằm trong tệp tháng khác (gửi trễ) -> partition theo pickup_date, ghi đè cả thư mục.
- Không dedup: 50 dòng trùng trên 84,6 triệu; passenger_count thiếu 444 383.
- Sạch: 83 382 609 chuyến, 365 thư mục/365 tệp, 1,48 GB (Snappy vs GZIP; zstd nhỏ hơn).
- Giờ cao điểm 18h: 5 478 973 chuyến (6,6%); vắng nhất 4h: 637 354 (chênh 8,6 lần). Ngày thường 8h ~12 457/ngày, 18h ~15 853; 2h sáng cuối tuần ~6 938/ngày vs ~1 775 ngày thường.
- Tip: thẻ trung bình 22,77% cước, 96,3% chuyến có tip; tiền mặt 22,5 triệu chuyến (27%), tip = 0 ở 99,99%; tính trên mọi chuyến chỉ 16,48%.
- Tip theo borough (chuyến thẻ): Manhattan 23,46%; Queens 20,73% (88% là JFK/LGA); Brooklyn 14,14%; Staten Island 3,62%; Bronx 2,71%. Manhattan 55,2 triệu / 60,1 triệu chuyến thẻ.
- Sân bay: 6 418 240 chuyến (7,7%), cước TB 40,07 USD vs 11,01 (gấp 3,6 lần), 23,3% tổng cước.
- Tối ưu (máy 16 nhân, một lần chạy, phụ thuộc máy): broadcast 1,4 s vs 7,0 s sort-merge; ghi tháng 1 naive 1 984 tệp (64 tệp/ngày) vs repartition 31 tệp; pruning ngày 04/07 (121 564 chuyến): 13,3 s từ tệp gốc vs 0,04 s từ dữ liệu partition.
- Zone 264/265 ~500 nghìn chuyến thẻ không rõ vị trí. Chỉ Yellow Taxi, không có FHV (Uber/Lyft).

## 07 / advanced / 03-hybrid-wikimedia (báo cáo mẫu trong SOLUTION.md)
CẢNH BÁO: số liệu là của MỘT lần ghi 5 phút ngày 29/10/2026 (không ghim); KHÔNG dùng làm đáp án cố định cho câu data. Chỉ dùng làm câu kiến thức/khái niệm.
- 11 884 dòng, 18,4 MB raw -> 0,8 MB Parquet; 5 651 edit/new; ~1 134 sửa đổi/phút; categorize 5 435 event (45,7%).
- Bot 48,7% sửa đổi; wikidatawiki 1 830 (32%), commonswiki 1 342, enwiki 565.
- Độ trễ p50 1,9 s, p95 6,2 s, max 52,9 s; allowed_lateness 10 s bỏ 4/5 651 (0,07%), 0 s bỏ 60 (1,06%), >= 30 s không bỏ.
- Đối soát: 4/331 cặp (phút, wiki) lệch, tổng lệch 4 = số event trễ.
- Kiến thức (ổn định): dedup theo `meta.id` chứ không `event.id`; event time là `timestamp`; Last-Event-ID, at-least-once; nhớ id trước khi xét late; EventStreams giữ lịch sử 7-31 ngày nên chọn Kappa có lớp raw.
