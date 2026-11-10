# Postmortem: ETA ở queens dài gấp 2.5 lần sau khi feature `zone_speed_15m` ngừng cập nhật (2019-11-14)

Trạng thái: đã review. Mức độ: SEV1. Không đổ lỗi: tài liệu nói về hệ thống và quy trình, người được gọi theo vai trò.

## 1. Tóm tắt

Chiều 2019-11-14, từ 15:50 tới 17:00, market queens trả ETA dài khoảng 2.5 lần thời gian thật cho gần như mọi chuyến. Model
`v42`, đưa lên queens lúc 13:05 với 100% traffic, đọc feature online `zone_speed_15m`. Consumer của partition queens dừng lúc
15:20 vì một message không deserialize được; online store giữ giá trị cuối thêm 30 phút (TTL) rồi trả null, và `v42` điền null
bằng 0 nên tỉ số tốc độ chạm trần 2.5. Đội support phát hiện trước mọi alert (16:21). Rollback queens về `v41` lúc 17:00 chấm dứt
tác động; feature tươi lại lúc 18:27 sau khi bỏ qua offset hỏng. Manhattan và brooklyn không bị ảnh hưởng.

## 2. Tác động

| Chỉ số | Giá trị | Cách tính |
| --- | --- | --- |
| Request bị ảnh hưởng | 1242 | Request queens có `ts` trong [15:50, 17:00) |
| Dự đoán tệ | 1176 (94.7%) | Sai số tuyệt đối lớn hơn 30% thời gian thật cộng 300 giây |
| Budget chất lượng 30 ngày đã tiêu | 2.51% | 1176 / (10% × 30 × 15 631 request/ngày của queens) |
| Phút feature cũ hơn 900 giây | 172 | Từ 15:35 tới 18:26, theo `freshness.csv` |
| Budget freshness 30 ngày đã tiêu | 39.81% | 172 / 432 phút |

Ngoài số: tài xế ở JFK và LGA báo khách huỷ chuyến vì ETA quá dài. Budget chất lượng chỉ tiêu 2.51% vì queens nhỏ so với cả tháng,
nhưng trong 70 phút **cả market** nhận ETA sai; bảng phân loại xếp SEV1 theo số khung 5 phút hỏng, không theo phần trăm budget,
đúng vì người dùng không thấy "trung bình 30 ngày". Tỉ lệ dự đoán tệ thường ngày của queens khoảng 6%, nên phần tệ "thừa" do sự cố
là khoảng 1176 - 6% × 1242 ≈ 1100 dự đoán.

## 3. Dòng thời gian

Giờ New York, như trong mọi log của sự cố.

| Thời điểm | Sự kiện |
| --- | --- |
| 09:58 | Partition brooklyn của `zone_speed_15m` lag 23 phút, tự hồi sau rebalance (không liên quan, không ảnh hưởng chất lượng) |
| 13:05 | `mdl-731`: queens lên `v42` ngay 100% traffic, bỏ canary vì cửa sổ hotfix |
| 14:31 | `cfg-514`: bật debug log `/predict` ở queens (không liên quan) |
| 15:20 | Consumer partition queens chết ở một message hỏng; không alert nào theo dõi việc này |
| 15:35 | Feature queens cũ quá 900 giây; SLO freshness bắt đầu bị đốt |
| 15:48 | `cfg-515`: tăng timeout feature store ở brooklyn (không liên quan) |
| 15:50 | Hết TTL 30 phút, online store trả null, `v42` điền 0: **bắt đầu tác động** |
| 16:21 | Đội support báo tài xế JFK/LGA thấy ETA gấp hai, gấp ba: **phát hiện** |
| 16:25 | On-call giao vai trò IC; IC giao comms, cập nhật mỗi 20 phút |
| 16:27 | Giả thuyết đầu tiên: `cfg-515`. IC yêu cầu xem theo market; brooklyn bình thường nên loại |
| 16:32 | Kỹ sư feature pipeline thấy consumer queens chết từ 15:20 |
| 16:40 | Restart consumer queens; chết lại ở cùng offset sau 3 phút, không có tác dụng |
| 16:56 | IC quyết định rollback queens về `v41` (không đọc `zone_speed_15m`) |
| 17:00 | `mdl-733` xong, request mới của queens dùng `v41`: **hết tác động** |
| 17:18 | Alert `ETAQualityFastBurn` của queens bắn, sau rollback 18 phút, vì nhãn về lúc trả khách |
| 18:27 | Bỏ qua offset hỏng (`ops-77`), giữ message để phân tích; feature queens tươi lại |
| 18:31 | Alert resolved, đóng sự cố |

## 4. Nguyên nhân

Chuỗi nhân quả: một message hỏng làm consumer dừng; không ai biết vì không có SLO freshness; feature hết TTL và code điền giá trị
không an toàn; thay đổi đã đưa phụ thuộc này lên toàn bộ traffic queens mà không qua canary.

- `stale_feature`: feature `zone_speed_15m` của queens ngừng cập nhật từ 15:20 tới 18:27. Consumer không có dead-letter queue nên
  một message hỏng chặn cả partition; restart không giúp vì offset không đổi.
- `unsafe_default`: khi feature null, `v42` dùng `fillna(0)` rồi chặn mẫu số ở 1 mph, nên tỉ số tốc độ luôn chạm trần 2.5. Giá trị
  mặc định đúng phải là "không chỉnh" (tỉ số 1, tức `v41`) hoặc tốc độ điển hình của zone và giờ. Model không có test cho trường hợp
  feature thiếu.
- `skipped_canary`: `mdl-731` lên 100% traffic. Canary 10% sẽ giới hạn tác động ở khoảng 125 request thay vì 1242, và một cổng canary
  có điều kiện freshness của feature mới sẽ chặn bản đó khi partition chết.
- `missing_freshness_alert`: `zone_speed_15m` là feature view mới, không có SLO freshness. Feature cũ quá 15 phút từ 15:35, alert
  burn rate freshness (14.4 lần trên 1h và 5m) sẽ bắn khoảng 15:45, trước khi người dùng bị ảnh hưởng 5 phút. Alert chất lượng có
  sẵn chỉ bắn lúc 17:18 vì nhãn về lúc trả khách: tín hiệu chất lượng luôn trễ bằng thời gian chuyến.

Đã loại: `config_change` (`cfg-515` chỉ ở brooklyn, brooklyn không đổi chất lượng; `cfg-514` chỉ đổi log level, tác động bắt đầu
80 phút sau đó), `model_regression` (13:05–15:20 `v42` có tỉ lệ tệ ngang `v41` buổi sáng), `traffic_spike` (request queens theo phút
không bất thường), `label_delay` (nhãn về đúng lúc trả khách), `upstream_data_change` (dữ liệu chuyến không đổi).

## 5. Điều làm tốt và điều may mắn

- On-call giao vai trò IC ngay để giữ tay cho việc debug; comms cập nhật đều cho support.
- IC chặn giả thuyết `cfg-515` bằng một câu hỏi theo market thay vì rollback một thay đổi không liên quan.
- Khi restart không có tác dụng, đội chọn rollback model, việc đảo ngược được và không cần hiểu hết nguyên nhân.
- May mắn: `v41` vẫn còn trong registry và không đọc feature hỏng; sự cố rơi vào chiều chứ không phải giờ cao điểm sáng.

## 6. Hành động

| Hành động | Loại | Chủ sở hữu | Hạn | Cách kiểm |
| --- | --- | --- | --- | --- |
| SLO freshness và alert burn rate theo market cho mọi feature view online | phát hiện | Đội nền tảng ML | 2019-11-22 | `promtool test rules` có ca partition kẹt 40 phút, alert bắn trước 10 phút |
| Cổng rollout: model mới không qua canary 10% ít nhất 1 giờ thì không lên 100% | ngăn chặn | Đội nền tảng ML | 2019-11-29 | CD từ chối `mdl-*` thiếu bước canary, có test trong CI |
| Feature thiếu thì model dùng tỉ số 1 (hành vi `v41`) và đếm metric `feature_missing_total` | giảm thiệt hại | Đội model ETA | 2019-11-20 | Unit test với feature null cho ETA bằng `v41`; metric có trên dashboard |
| Dead-letter queue cho consumer `zone_speed_15m`, không để một message chặn partition | ngăn chặn | Đội feature pipeline | 2019-12-06 | Test tích hợp gửi message hỏng, consumer chạy tiếp, DLQ có 1 message |
| Kênh support có nút "báo sự cố ETA theo market" gửi thẳng tới on-call | phát hiện | Đội support và on-call | 2019-12-13 | Diễn tập: báo cáo giả tới on-call trong dưới 2 phút |
| Runbook: feature online hỏng thì rollback model về bản không đọc feature đó trước khi sửa pipeline | giảm thiệt hại | Đội nền tảng ML | 2019-11-22 | Game day: kẹt partition ở staging, thời gian tới rollback dưới 15 phút |
