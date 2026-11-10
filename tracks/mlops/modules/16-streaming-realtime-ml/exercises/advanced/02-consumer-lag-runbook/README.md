---
title: Runbook khi consumer lag của pipeline feature tăng
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Viết runbook cho người trực khi cảnh báo consumer lag của pipeline feature realtime kêu lúc 2 giờ sáng: các bước chẩn đoán theo thứ
tự, lệnh và dashboard cụ thể, cây quyết định giữa "chờ", "mở rộng", "bỏ qua backlog", "rollback", và cách bảo vệ model trong lúc
feature cũ đi.

## Đề bài

**Bối cảnh.** Pipeline từ bài Intermediate 01 và 02 đã lên production: topic `trips` 12 partition, consumer group `zone-windows` chạy 4
pod trên Kubernetes, ghi feature qua Feast push vào Redis online store. SLO freshness: p95 dưới 5 phút. Cảnh báo hiện có:
`kafka_consumergroup_lag_sum{group="zone-windows"} > 50000` trong 10 phút.

Nộp `RUNBOOK.md` (tối đa 3 trang) gồm:

1. Phân loại tác động trong 5 phút đầu: lag bao nhiêu giây (không phải bao nhiêu message), freshness hiện tại, model đang dùng feature
   cũ bao lâu, có vi phạm SLO chưa.
2. Cây chẩn đoán phân biệt ít nhất năm nguyên nhân: lưu lượng vào tăng thật; consumer chậm do online store chậm; rebalance liên tục (pod
   restart, `max.poll.interval.ms`); một partition nóng (key lệch); consumer kẹt vì một message độc (poison pill) hay lỗi lặp lại. Mỗi
   nguyên nhân có dấu hiệu nhận biết và lệnh kiểm tra (`kafka-consumer-groups.sh --describe`, metric, log).
3. Hành động cho từng nhánh, và giới hạn: vì sao thêm pod quá số partition không giúp; khi nào được phép nhảy offset tới cuối (và feature
   nào sẽ sai, sai bao lâu); dead letter queue cho message độc.
4. Bảo vệ model trong lúc chờ: feature cũ quá ngưỡng thì serving làm gì (giá trị mặc định, model dự phòng không dùng feature stream, cờ
   tắt), và ai quyết định.
5. Phục hồi và xác nhận: lag về 0 chưa đủ, kiểm freshness và giá trị feature so với tính batch; backfill cửa sổ bị bỏ.
6. Cải tiến cảnh báo: lag tính theo thời gian, cảnh báo burn rate của SLO freshness thay cho ngưỡng message.

Không có test tự động. Tự chấm bằng rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Đạt ít nhất 70/100 điểm rubric.
- Runbook làm theo được bởi người chưa từng thấy hệ thống: mỗi bước có lệnh hay đường dẫn dashboard, có điều kiện chuyển bước.
- Có ít nhất một hành động có rủi ro mất dữ liệu được đánh dấu rõ và cần ai phê duyệt.

## Gợi ý

### Gợi ý 1

Lag theo message đánh lừa: 50 000 message lúc thấp điểm có thể là 20 phút, lúc đỉnh là 30 giây. Tính lag theo thời gian bằng timestamp
của message cuối đã xử lý so với hiện tại, hoặc dùng exporter có sẵn chỉ số này.

### Gợi ý 2

Xem lag từng partition trước khi nhìn tổng. Lag dồn ở một partition gợi ý key nóng hoặc message độc; lag đều mọi partition gợi ý lưu
lượng hoặc phía ghi chậm.
