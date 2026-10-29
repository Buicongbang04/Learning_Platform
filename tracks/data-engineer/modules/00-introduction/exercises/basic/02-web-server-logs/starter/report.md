# Báo cáo: NASA KSC HTTP access log, tháng 7/1995

## Bộ dữ liệu

TODO: nguồn, giấy phép, kích thước (dòng, MB gzip), khoảng thời gian thật sự có trong log, mỗi dòng gồm gì.

## Làm sạch

TODO: bao nhiêu dòng hỏng và trông thế nào; xử lý `-` ở cột bytes, múi giờ, `host_type`; vì sao không dedup.
Dữ liệu sạch ghi ở đâu, bao nhiêu MB so với tệp gốc.

## Insight

TODO: ít nhất 3 phát hiện, mỗi phát hiện có số và một câu giải thích (ngày đỉnh và lý do, nhịp trong ngày,
ngày thường vs cuối tuần, 404, khoảng lặng dài nhất, ai tải nhiều byte nhất).

## Giới hạn

TODO: điều bộ dữ liệu không cho biết (người dùng thật hay proxy/cache? log dừng sớm?), và điều cần thận trọng khi kết luận.
