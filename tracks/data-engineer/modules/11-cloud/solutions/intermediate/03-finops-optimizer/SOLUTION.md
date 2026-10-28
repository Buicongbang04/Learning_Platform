# Lời giải: FinOps cho data lake

## Cách làm

- **`monthly_cost`**: chi phí = lưu trữ + đọc lại. Class lạnh rẻ về lưu trữ nhưng **tính tiền mỗi
  GB đọc ra**; đây là đánh đổi cốt lõi của storage tiering.
- **`best_storage_class`**: duyệt class theo thứ tự nóng → lạnh, lọc bỏ archive khi có đọc (restore
  Deep Archive mất tới 12–48 giờ, không dùng được cho dữ liệu còn được truy vấn), rồi `min`.
  `min` giữ phần tử đầu khi hoà nên tự ưu tiên class nóng hơn.
- **`scanned_gb`**: hai đòn bẩy độc lập. Partition pruning cắt theo **dòng** (chỉ đọc 30/730
  partition), định dạng cột cắt theo **cột** (chỉ đọc 4/20 cột). CSV không có lợi ích thứ hai.
  Ví dụ trong test: 730 GB → 30 GB (chỉ partition) → 6 GB (partition + Parquet), giảm 120 lần.
- **`query_cost`**: BigQuery on-demand tính theo byte quét, tối thiểu 10 MB mỗi bảng được tham chiếu.
- **`savings_report`**: làm tròn ở lớp báo cáo, lọc dataset có tiết kiệm, sắp xếp giảm dần để
  đội data ưu tiên việc đáng tiền nhất.

## Ngoài bài: bẫy chi phí thực tế

| Bẫy | Vì sao | Cách tránh |
| --- | --- | --- |
| Phí tối thiểu thời gian lưu | IA 30 ngày, Glacier IR 90 ngày, Deep Archive 180 ngày: xoá sớm vẫn trả đủ | Chỉ chuyển dữ liệu chắc chắn giữ lâu |
| Object nhỏ | IA/Glacier IR tính tối thiểu 128 KB mỗi object; Glacier thêm metadata ~40 KB | Compaction file nhỏ trước khi chuyển |
| Phí request | PUT/GET/LIST và **phí transition** lifecycle tính theo số object | Ít object lớn tốt hơn nhiều object nhỏ |
| Không biết mẫu truy cập | Đoán sai thì tiering làm tăng chi phí | S3 Intelligent-Tiering, GCS Autoclass, Azure lifecycle theo last access time |
| `SELECT *` trên warehouse | Quét mọi cột | Chọn cột, partition + cluster, `require_partition_filter`, dry run ước tính byte |

Tương đương: S3 Standard/IA/Glacier IR/Deep Archive ≈ Azure Blob Hot/Cool/Cold/Archive ≈
GCS Standard/Nearline/Coldline/Archive.
