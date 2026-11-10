# Hướng làm và rubric: data contract cho feed ETA

## Hướng làm

1. **Ngược từ sự cố.** Ba thay đổi: đổi đơn vị (semantic breaking, schema không đổi), thêm cột kiểu chuỗi (thường non-breaking nhưng kiểu
   `object` làm hỏng ghi Parquet ở downstream), và lỗi không bị phát hiện vì job huấn luyện chỉ kiểm "chạy xong", không kiểm số liệu.
2. **Schema chính xác tới đơn vị.** Ví dụ `trip_distance: float64, dặm (mile), > 0, không null`; `tpep_pickup_datetime: timestamp, giờ địa phương New York, không null, trong tháng của partition`;
   `PULocationID: int, 1..265, không null`; `passenger_count: float, nullable (tỉ lệ null ≤ 5%)`. Đổi đơn vị là breaking dù tên và kiểu không đổi: ghi hẳn vào contract.
3. **Phân loại thay đổi.** Breaking: đổi đơn vị/ngữ nghĩa, đổi tên hay xoá cột, siết nullable, đổi kiểu hẹp hơn, đổi múi giờ. Non-breaking: thêm cột nullable có tài liệu, nới
   khoảng giá trị có báo. Quy trình breaking: phiên bản mới `v2` chạy song song với `v1` tối thiểu 30 ngày, thông báo ≥ 14 ngày, consumer xác nhận.
4. **Hai lớp thực thi.** (a) Phía nhà cung cấp, trong CI của đội data: test schema, đơn vị (so phân phối `trip_distance` với tháng trước, trung vị lệch > 30% thì chặn), tỉ lệ dòng lỗi; thay đổi
   không qua thì không merge. (b) Phía người dùng, ở cửa vào pipeline ML: schema Pandera (ghim phiên bản contract), chặn huấn luyện nếu vi phạm nặng, cách ly dòng lỗi nhẹ.
   Một lớp không đủ: lớp (a) bỏ sót lỗi nguồn ngoài; lớp (b) báo sau khi lỗi đã phát hành.
5. **SLA đo được.** Ví dụ: dữ liệu ngày D có mặt trước 06:00 D+1 (≥ 99% số ngày/tháng); dòng vi phạm luật cứng ≤ 1% mỗi partition; đo bằng cùng bộ luật ở CI.
6. **Sở hữu.** Mỗi bảng có owner (đội), người ký contract (lead data), kênh trực; vi phạm SLA: owner phản hồi trong 1 giờ làm việc, rollback về phiên bản trước trong 4 giờ. Consumer đăng ký trong
   registry để owner biết ai bị ảnh hưởng khi đổi.
7. **Công cụ.** Pandera cho kiểm trong code Python của pipeline ML; GE hoặc test dbt cho phía data khi nguồn là SQL/Spark và cần báo cáo cho người không code. Lý do chọn, không "vì quen".

## Rubric (tối đa 20 điểm)

| Mục | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Schema | 4 | đơn vị cho mọi cột số, nullable rõ, miền giá trị, múi giờ |
| Ngữ nghĩa và SLA | 3 | có độ trễ, tỉ lệ lỗi chấp nhận và cách đo, không chỉ "dữ liệu sạch" |
| Quy tắc thay đổi | 4 | định nghĩa breaking có ví dụ taxi, versioning, báo trước, chạy song song |
| Thực thi hai lớp | 4 | có kiểm phía nhà cung cấp trước khi phát hành và phía người dùng, hành vi khi vi phạm |
| Sở hữu và leo thang | 2 | tên vai trò, thời gian phản hồi |
| Truy ngược sự cố | 3 | chỉ rõ từng thay đổi trong sự cố bị chặn ở bước nào |

Trừ điểm: hợp đồng chỉ nói "đội data sẽ thông báo" không có cơ chế (−2); thực thi chỉ ở phía ML (−3); không nhắc đổi đơn vị là breaking (−2).
Mức đạt: 14/20.
