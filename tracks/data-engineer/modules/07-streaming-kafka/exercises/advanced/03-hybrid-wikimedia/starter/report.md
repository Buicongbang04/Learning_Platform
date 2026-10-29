# Báo cáo: Wikimedia EventStreams `recentchange`, hybrid stream + batch

## Bộ dữ liệu

TODO: nguồn, giấy phép, bạn ghi lúc nào (UTC) và bao lâu, bao nhiêu tệp/dòng/MB, mỗi dòng gồm gì
(`received_at` + event nguyên bản), event time và ingestion time là trường nào.

## Làm sạch

TODO: bao nhiêu dòng bị bỏ và vì sao (dòng hỏng, canary), bao nhiêu bản trùng, khoá dedup là gì và vì sao
không dùng `event.id`; kiểu dữ liệu, múi giờ; dữ liệu sạch ghi ở đâu, bao nhiêu MB so với tệp raw.

## Insight

TODO: ít nhất 4 phát hiện có số: sửa đổi mỗi phút, tỉ lệ bot, wiki sôi động nhất (và wiki nhiều sửa đổi
của người nhất), độ trễ p50/p95, tỉ lệ late với `allowed_lateness = 10` giây và mức cần để dưới 1%,
kết quả đối soát stream với batch (bao nhiêu window lệch, lệch vì đâu).

## Giới hạn

TODO: vài phút ghi đại diện được tới đâu (giờ trong ngày, ngày trong tuần), phút đầu/cuối bị cắt, trường
`bot` chỉ là cờ tài khoản, `timestamp` làm tròn tới giây; và lựa chọn Lambda hay Kappa cho nguồn này, vì sao.
