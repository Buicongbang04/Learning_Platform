# Hướng làm và rubric: runbook consumer lag

## Runbook mẫu (rút gọn)

**Bước 0. Tác động (5 phút đầu).** Mở dashboard pipeline feature: lag theo thời gian của group `zone-windows` (`now - timestamp của
message cuối đã xử lý` từng partition), freshness p95 đọc từ online store, tỉ lệ request serving dùng fallback. Nếu freshness p95 > 5
phút: đang vi phạm SLO, mở sự cố, báo kênh serving. Nếu lag theo message cao nhưng theo thời gian < 1 phút: lưu lượng tăng, theo dõi 15
phút, không hành động.

**Bước 1. Lag từng partition.**

```bash
kafka-consumer-groups.sh --bootstrap-server $BROKER --describe --group zone-windows
```

| Dấu hiệu | Nguyên nhân khả dĩ | Kiểm tra tiếp |
| --- | --- | --- |
| Lag tăng đều mọi partition, tốc độ vào tăng | lưu lượng thật tăng | `rate(kafka_topic_partition_current_offset[5m])` so tuần trước |
| Lag tăng đều, tốc độ vào bình thường, tốc độ xử lý giảm | phía ghi chậm (Redis, Feast push) | latency push, Redis `SLOWLOG`, CPU Redis |
| Lag răng cưa, consumer đổi liên tục trong `--describe` | rebalance liên tục | pod restart, OOM, log `max.poll.interval.ms` |
| Lag dồn ở 1–2 partition | key nóng | phân phối message theo key trên partition đó |
| Một partition đứng hẳn, offset không tăng, log lặp cùng lỗi | message độc (poison pill) | log consumer, offset kẹt, đọc message tại offset đó |

**Bước 2. Hành động.**

- Lưu lượng tăng: tăng replica tới tối đa số partition (12); quá số đó vô ích vì một partition chỉ một consumer trong group. Cần hơn:
  tăng partition (đổi phân phối key, phải kiểm tra thứ tự theo key) là thay đổi có kế hoạch, không làm lúc 2 giờ sáng.
- Phía ghi chậm: gom push theo batch lớn hơn, giảm tần suất; nếu Redis quá tải thì đó là sự cố của Redis, chuyển runbook.
- Rebalance: tăng `max.poll.interval.ms` hoặc giảm `max.poll.records`, sửa OOM (giới hạn bộ nhớ, state cửa sổ), bật static membership.
- Key nóng: tạm chấp nhận lag ở partition đó nếu feature của key khác vẫn tươi; sửa lâu dài bằng salting key.
- Message độc: chuyển message vào dead letter topic, commit qua offset đó. **Có rủi ro mất dữ liệu: cần on-call lead đồng ý, ghi lại
  offset.**
- Nhảy offset tới cuối (`--reset-offsets --to-latest`): chỉ khi backlog không còn giá trị cho serving và SLO đang vỡ nặng. Feature cửa
  sổ của khoảng bỏ qua sẽ thiếu (giá trị thấp hơn thật) tới hết một chu kỳ cửa sổ lớn nhất. **Cần phê duyệt của chủ sở hữu feature;
  lên lịch backfill offline.**

**Bước 3. Bảo vệ model.** Serving kiểm tuổi feature mỗi request: quá 10 phút thì dùng model dự phòng không dùng feature stream (cờ
`zone_features_stale_fallback`), hoặc giá trị mặc định đã đánh giá. Người quyết định bật cờ thủ công: on-call ML; tự động khi tuổi > 15
phút.

**Bước 4. Phục hồi.** Lag về 0 chưa đủ: kiểm freshness p95 về dưới SLO, so giá trị feature online của vài zone với tính batch trên cùng
khoảng (job đối soát), backfill cửa sổ bị bỏ vào offline store để huấn luyện không bị lỗ.

**Bước 5. Cải tiến.** Cảnh báo theo lag thời gian và burn rate của SLO freshness (module 18), không theo số message; cảnh báo tỉ lệ
`skipped`/`rejected` và độ trễ watermark (Intermediate 03).

## Rubric (100 điểm)

| Mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Phân loại tác động | 15 | Lag theo thời gian, freshness, tác động lên model; ngưỡng mở sự cố |
| Cây chẩn đoán | 25 | Ít nhất năm nguyên nhân, mỗi cái có dấu hiệu và lệnh kiểm tra cụ thể |
| Hành động và giới hạn | 20 | Đúng giới hạn số partition; điều kiện nhảy offset; DLQ |
| Hành động rủi ro có phê duyệt | 10 | Đánh dấu mất dữ liệu, ai duyệt, ghi lại offset |
| Bảo vệ model | 10 | Fallback theo tuổi feature, ai quyết định |
| Phục hồi và xác nhận | 10 | Không dừng ở lag = 0; đối soát và backfill |
| Cải tiến cảnh báo | 10 | Lag thời gian, burn rate freshness, chỉ số watermark |

Trừ điểm: "tăng replica" là hành động duy nhất (-15); không phân biệt lag theo message và theo thời gian (-10); reset offset không cần
phê duyệt (-10).
