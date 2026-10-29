# Lời giải: Spark trên NYC Yellow Taxi 2019

Lời giải đầy đủ là `nyc_taxi.ipynb` (chạy cả notebook khoảng 2 phút trên máy 16 nhân, 31 GB RAM), báo cáo mẫu
là `report.md`.

## Cách làm

1. **load_trips**: `spark.read.parquet(*paths)` một lần cho cả 12 tệp (một DataFrame, một plan), rồi một `select`
   duy nhất với `F.col(src).cast(typ).alias(dst)`. Parquet là columnar nên Spark chỉ đọc 10/19 cột
   (**column pruning**; `ReadSchema` trong plan chỉ có 10 cột).
2. **flag_rejects**: viết điều kiện **chuyến tốt** cho từng luật trong một `dict`, rồi dựng cột lý do bằng
   `F.when` lồng nhau, duyệt `REASONS` từ cuối lên để luật đầu nằm ngoài cùng và thắng. Mỗi điều kiện bọc
   `F.coalesce(ok, F.lit(False))`: so sánh với `null` ra `null`, mà `F.when(null)` coi là sai, nên không bọc thì
   chuyến thiếu `dropoff_at` lọt vào dữ liệu sạch. Thời gian dùng `timestampdiff(SECOND, ...)` vì cột là
   `TIMESTAMP_NTZ` (không `cast("long")` được).
3. **clean_trips** dùng lại `flag_rejects` (một nguồn sự thật cho luật), lọc `isNull`, rồi thêm cột. Mọi thứ
   lazy: chưa có action thì chưa đọc byte nào.
4. **write_clean**: `repartition("pickup_date")` trước `partitionBy("pickup_date")`. Hash theo cột partition đưa
   mọi dòng của một ngày về một task, nên mỗi thư mục ngày có đúng một tệp. `mode("overwrite")` làm job
   idempotent.
5. **Phân tích**: một `groupBy` cho mỗi câu hỏi; `tip_rate_by_borough` lọc chuyến thẻ **trước** join (ít dòng phải
   join hơn) và `F.broadcast(zones)`; `airport_summary` `collect()` 3 id sân bay (bảng nhỏ) rồi tính 4 con số
   trong **một** `agg`, một lần quét.
6. Notebook ghi dữ liệu sạch rồi phân tích trên `spark.read.parquet(CLEAN)`, như job downstream thật: không
   làm sạch lại 84 triệu dòng cho mỗi câu hỏi.

## Vì sao như vậy

- **Luật có tên, mỗi chuyến một lý do** thay vì một `where` dài: đếm được mỗi luật loại bao nhiêu, phát hiện ngay
  khi một luật bỗng loại gấp mười (nguồn đổi định dạng). Pipeline thật ghi các dòng bị loại ra bảng quarantine.
- **Broadcast tường minh** thay vì trông vào `autoBroadcastJoinThreshold`: ước lượng kích thước sau filter/aggregate
  có thể sai, và cấu hình cluster có thể tắt auto-broadcast. Test tắt nó (`-1`) để chắc hint có mặt. Không broadcast
  thì Spark shuffle 60 triệu chuyến thẻ để join với 265 dòng: chậm ~5 lần.
- **Một tệp mỗi ngày**: ~4 MB/tệp ở đây (với dữ liệu lớn hơn thì vài trăm MB/tệp là đẹp). Không `repartition`, dữ liệu
  đang ở 64 partition sau shuffle sinh 64 tệp/ngày, ~23 nghìn tệp/năm: list chậm, mở tệp chậm, metadata phình.
  `coalesce(1)` cũng ra một tệp mỗi ngày nhưng dồn cả năm vào một task.
- **Partition theo ngày đón khách, không theo tháng của tệp**: tệp tháng 2 chứa chuyến của 31/01 và tháng 3–9
  (bản ghi gửi trễ). Truy vấn theo ngày đọc đúng một thư mục (`PartitionFilters` trong plan): 0,04 giây so với
  13 giây khi quét tệp gốc.
- **Cả 12 tháng**: máy 16 nhân, 31 GB chạy cả notebook ~2 phút, nên không cần chọn tháng con. Heap driver 8 GB
  trong notebook (4 GB trong test): mỗi tệp TLC là **một row group ~100 MB**, reader Parquet giữ cả column chunk
  trong bộ nhớ, 16 task song song với heap mặc định 1 GB sẽ `OutOfMemoryError`.

## Con số tham chiếu (bộ thật, 12 tháng 2019)

| Đại lượng | Giá trị |
| --- | --- |
| Chuyến gốc / sạch / bị loại | 84 598 444 / 83 382 609 / 1 215 835 (1,44%) |
| `bad_distance`, `bad_duration`, `bad_amount`, `too_fast`, `out_of_period` | 677 276, 302 998, 161 874, 72 245, 1 442 |
| Giờ cao điểm / vắng nhất | 18h (5 478 973) / 4h (637 354) |
| `tip_by_payment` card | 60 053 968 chuyến, `tip_rate` 0,2277, `tipped_share` 0,9631 |
| `tip_by_payment` cash / other | 22 510 014, 0,0, 0,0001 / 818 627, 0,0010, 0,0030 |
| `tip_rate_by_borough` | Manhattan 0,2346 · Unknown 0,2197 · Queens 0,2073 · EWR 0,1645 · N/A 0,1520 · Brooklyn 0,1414 · Staten Island 0,0362 · Bronx 0,0271 |
| `airport_summary` | 6 418 240 chuyến, share 0,077, cước 40,07 vs 11,01 |
| Dữ liệu sạch | 365 thư mục `pickup_date=`, 365 tệp, 1,48 GB (Snappy; gốc 1,24 GB GZIP) |
| Tháng 2 một mình (test ghi) | 6 966 272 chuyến sạch, 86 thư mục ngày |

## Rubric cho báo cáo

| Mức | Bộ dữ liệu | Làm sạch | Insight | Giới hạn |
| --- | --- | --- | --- | --- |
| Đạt | Nguồn, giấy phép, số chuyến, số tệp/GB | Số chuyến loại theo từng lý do | 3 con số đúng (giờ cao điểm, tip thẻ vs tiền mặt, sân bay hoặc borough) | 1 giới hạn |
| Tốt | Thêm: một row group mỗi tệp và hệ quả cho song song | Thêm: vì sao không dedup, nơi ghi, số tệp, chuyến trễ tháng | Nhận ra tip tiền mặt là lỗi thu thập, không phải hành vi; có kết quả đo ở mục 5 | Chỉ Yellow Taxi, ngưỡng là tuỳ chọn |
| Xuất sắc | | Đề xuất bảng quarantine, so sánh nén Snappy vs GZIP/zstd | Chỉ ra tối ưu lớn nhất là layout (partition pruning), giải thích bằng plan | Nêu dữ liệu cần thêm để trả lời (FHV, tip tiền mặt khảo sát) |
