# Câu hỏi phỏng vấn: Giới thiệu và vòng đời Data Engineering

## Data Engineering là gì? Giải thích cho một người không làm kỹ thuật.

Data Engineering là xây và vận hành "đường ống" đưa dữ liệu từ nơi nó sinh ra (app, database, cảm
biến, đối tác) tới nơi người khác dùng (dashboard, model, ứng dụng), sao cho dữ liệu **đúng, đủ, đúng
giờ và an toàn**, mỗi ngày, không cần ai ngồi canh.

Ví dụ: ở một sàn thương mại điện tử như Olist, mỗi đơn hàng nằm trong database của ứng dụng. Data
Engineer lấy đơn mới mỗi đêm, làm sạch, ghép với thông tin khách và người bán, lưu vào warehouse để
sáng hôm sau đội kinh doanh mở dashboard thấy doanh thu hôm qua. Khi một ngày dữ liệu thiếu, DE là
người phát hiện trước người dùng, tìm nguyên nhân và chạy bù.

Câu trả lời tốt nhấn vào **hệ thống và độ tin cậy**, không chỉ "di chuyển dữ liệu".

## Data Engineer, Data Scientist và Data Analyst khác nhau thế nào? Bạn từng làm DA/DS, vì sao chuyển?

| | DA | DS | DE |
| --- | --- | --- | --- |
| Sản phẩm | Báo cáo, dashboard | Model, thí nghiệm | Pipeline, bảng tin cậy, nền tảng |
| Thành công | Insight dẫn tới quyết định | Model tốt hơn baseline và được dùng | SLA đạt, không mất dữ liệu, chi phí kiểm soát |
| Người dùng chính | Business | Business, product | DA, DS, ứng dụng |

DE là **người cung cấp** cho hai vai trò còn lại; DA và DS phụ thuộc vào chất lượng việc DE làm.

Gợi ý trả lời phần "vì sao chuyển": nói một vấn đề có thật bạn gặp khi làm DA/DS (ví dụ: dashboard
sai vì đơn bị trùng do pipeline chạy lại, mất hai ngày truy lỗi), và bạn muốn giải quyết gốc vấn đề
thay vì vá ở phía cuối. Lợi thế của bạn: hiểu người dùng dữ liệu cần gì, biết dữ liệu xấu trông thế
nào. Thừa nhận điều cần học: kỷ luật vận hành, distributed systems, hạ tầng.

## Kể các giai đoạn của vòng đời Data Engineering. Giai đoạn nào khó nhất?

Theo Reis & Housley: **Generation → Ingestion → Storage → Transformation → Serving** (roadmap.sh gộp
Transformation vào Serving, nên còn 4). Storage xuyên suốt, vì dữ liệu được lưu ở nhiều điểm.

Không có giai đoạn "khó nhất" chung, nhưng câu trả lời mạnh thường là **Generation/Ingestion**: DE
không kiểm soát hệ thống nguồn. Nguồn đổi schema không báo, xoá bản ghi cứng, API đổi version, event
mobile đến trễ ba ngày. Mọi lỗi ở đầu vòng đời lan xuống toàn bộ phía sau ("garbage in, garbage out").
Đó là lý do cần data contract và validation ngay khi ingest.

## "Undercurrents" của vòng đời Data Engineering là gì? Cho ví dụ cụ thể.

Là những mối quan tâm xuyên suốt mọi giai đoạn, không thuộc riêng bước nào:

- **Security**: credential trong secret manager, least privilege, mã hoá. Ví dụ: tài khoản ingest
  chỉ có quyền `SELECT` trên read replica.
- **Data Management**: quality, lineage, catalog, governance. Ví dụ: test `order_id` unique, not null.
- **DataOps**: monitoring, alert, CI/CD cho pipeline. Ví dụ: cảnh báo khi số đơn hôm nay thấp hơn 50%
  trung bình 7 ngày.
- **Data Architecture**: thiết kế tổng thể, khả năng tiến hoá. Ví dụ: medallion bronze/silver/gold.
- **Orchestration**: phụ thuộc giữa các bước, retry, lịch. Ví dụ: Airflow DAG.
- **Software Engineering**: Git, test, code review, infrastructure as code.

Ý cần nói: một pipeline "chạy được" nhưng thiếu undercurrent thì chưa phải production.

## Kể các loại nguồn dữ liệu phổ biến. Mỗi loại có rủi ro gì riêng?

| Nguồn | Rủi ro đặc trưng | Cách xử lý |
| --- | --- | --- |
| Database OLTP | Query nặng làm chậm production; incremental bỏ sót delete | Đọc read replica; CDC (Debezium) |
| API | Rate limit (429), phân trang, đổi version, timeout | Backoff + jitter, lưu response thô, validate schema |
| Logs | Định dạng bán cấu trúc, dòng hỏng, khối lượng lớn | Parse streaming, reject table, theo dõi tỉ lệ lỗi |
| Mobile apps | Event đến trễ, đồng hồ máy sai, nhiều version schema, trùng | Event time vs ingestion time, `event_id` dedup, schema tương thích ngược |
| IoT | Giá trị sentinel (`-200`), drift cảm biến, mất kết nối | Đổi sentinel thành null, kiểm khoảng hợp lệ, xử lý khoảng trống thời gian |

Ví dụ thật: bộ UCI Air Quality mã hoá giá trị thiếu là `-200`; lấy trung bình thẳng sẽ kéo số đo xuống
sai rõ rệt.

## Trước khi xây pipeline cho một nguồn mới, bạn hỏi những gì?

Nhóm câu hỏi theo các "data collection considerations":

1. **Volume**: bao nhiêu dữ liệu mỗi ngày, tổng lịch sử, tốc độ tăng.
2. **Velocity và độ mới cần thiết**: người dùng cần dữ liệu mới tới mức nào, trễ 1 giờ thì có hậu quả gì.
3. **Schema**: khoá chính, bản ghi có bị update/delete không, có `updated_at` tin được không, ai đổi
   schema và báo trước bao lâu.
4. **Giới hạn nguồn**: rate limit, giờ cấm query, có read replica không.
5. **Privacy và pháp lý**: có PII không, ai được đọc, giấy phép dữ liệu, thời gian lưu giữ.
6. **Chi phí**: phí API theo call, egress, lưu trữ.
7. **Chất lượng**: giá trị thiếu, trùng, sentinel; dữ liệu đến trễ tối đa bao lâu.

Và luôn xin **100 dòng dữ liệu thật** chứ không chỉ đọc tài liệu. Câu trả lời bằng văn bản cho các
câu hỏi trên là bản nháp của data contract.

## Batch hay streaming? Bạn quyết định thế nào?

Quyết định theo **yêu cầu latency được nói bằng con số** và chi phí sai lệch, không theo sở thích:

- Dashboard doanh thu xem lúc 9h sáng: batch hằng ngày là đủ. Streaming ở đây chỉ thêm chi phí vận hành.
- Phát hiện gian lận thanh toán, cập nhật tồn kho khi bán flash sale: cần giây, streaming có lý.
- Ở giữa (vài phút): micro-batch thường là thoả hiệp tốt.

Câu hỏi then chốt cho stakeholder: "Nếu dữ liệu trễ 1 giờ thì bạn mất gì?" Phần lớn yêu cầu
"realtime" biến mất sau câu hỏi này. Streaming đòi hỏi xử lý event time, late data, exactly-once,
và vận hành Kafka 24/7; chỉ trả giá đó khi lợi ích rõ ràng.

## Full load, incremental hay CDC: chọn thế nào khi lấy dữ liệu từ database?

- **Full snapshot**: đơn giản, tự bắt được delete, nhưng chi phí tăng theo kích thước bảng. Hợp với
  bảng nhỏ, bảng danh mục.
- **Incremental theo watermark** (`updated_at > last_run`): rẻ, nhưng không thấy hard delete, phụ
  thuộc ứng dụng cập nhật `updated_at` đúng, cần lookback window cho bản ghi commit trễ.
- **CDC từ WAL/binlog**: thấy mọi insert/update/delete, gần realtime, không tải query lên DB, nhưng
  phải vận hành Debezium + Kafka và xử lý snapshot ban đầu.

Câu trả lời tốt nêu điều kiện chuyển: bắt đầu incremental; chuyển CDC khi nguồn có hard delete quan
trọng, khi cần latency thấp, hoặc khi query incremental bắt đầu làm chậm DB nguồn.

## Bạn gọi một API công khai để lấy dữ liệu lịch sử 5 năm. Thiết kế việc thu thập thế nào?

- **Chia nhỏ**: theo cửa sổ thời gian (tháng) hoặc theo cursor; mỗi phần là một đơn vị có thể chạy lại
  độc lập (idempotent).
- **Tôn trọng rate limit**: throttle chủ động dưới ngưỡng, retry với exponential backoff + jitter khi
  gặp 429/5xx, có timeout cho mọi request.
- **Lưu thô trước**: ghi response JSON nguyên bản theo phân vùng (`raw/weather/year=2018/month=01.json`)
  trước khi parse. Sửa logic parse thì chạy lại từ file, không gọi API lần nữa.
- **Checkpoint**: ghi lại phần nào đã xong để job bị ngắt có thể tiếp tục, không làm lại từ đầu.
- **Validate**: kiểm schema response, số bản ghi kỳ vọng (ví dụ 24 giờ × số ngày), cảnh báo nếu thiếu.
- **Ghi nguồn và giấy phép**, tuân điều khoản sử dụng.

Ví dụ Open-Meteo Historical: lấy theo từng tháng, kiểm mỗi ngày đủ 24 giá trị theo giờ.

## Một file log có 2% dòng không parse được. Bạn làm gì?

Không để pipeline sập, cũng không lặng lẽ bỏ qua:

1. Tách dòng lỗi ra **reject file/table** kèm lý do và số dòng gốc.
2. Đo **tỉ lệ lỗi** mỗi lần chạy, so với ngưỡng (ví dụ 2% bình thường, trên 5% thì fail job và alert).
3. Xem mẫu dòng lỗi để phân loại: request bị cắt, trường byte là `-`, encoding lạ. Nhiều loại sửa được
   bằng cách nới regex hoặc xử lý giá trị đặc biệt.
4. Ghi lại quyết định (dòng loại nào bỏ, loại nào sửa) để người dùng số liệu hiểu.

Với NASA HTTP log tháng 7/1995, trường byte có giá trị `-` cho response không có body: đó không phải
lỗi mà là dữ liệu hợp lệ cần ánh xạ sang 0 hoặc null, tuỳ ý nghĩa.

## Bạn sẽ chọn công nghệ thế nào cho một nền tảng dữ liệu mới?

Bắt đầu từ yêu cầu, không phải từ công cụ:

1. **Yêu cầu**: volume, latency, người dùng, ràng buộc pháp lý.
2. **Ràng buộc**: số người trong đội, kỹ năng hiện có, ngân sách (tính cả giờ công vận hành, không chỉ
   license).
3. **Tiêu chí**: time to value, interoperability (chuẩn mở như SQL, Parquet, S3 API), build vs buy,
   managed vs self-hosted, khả năng đảo ngược quyết định.
4. **Ma trận quyết định**: liệt kê 2–3 phương án, chấm theo tiêu chí có trọng số, viết ra để người khác
   phản biện.
5. **Ưu tiên quyết định đảo ngược được** và công cụ nhàm chán đã chứng minh (boring technology).

Nêu rõ cạm bẫy **resume-driven development**: chọn Kafka + Spark + Kubernetes cho dữ liệu vài GB vì
muốn có trong CV.

## Startup có 1 Data Engineer, ~100 nghìn đơn hàng, cần dashboard hằng ngày. Bạn đề xuất stack gì?

Đề xuất đơn giản, ít thành phần phải vận hành:

- **Ingestion**: script Python incremental (hoặc một managed connector) đọc từ read replica, chạy hằng đêm.
- **Storage**: PostgreSQL riêng cho analytics hoặc DuckDB/Parquet trên object storage; dữ liệu cỡ này
  vừa một máy thoải mái.
- **Transform**: SQL với dbt (test, tài liệu, lineage miễn phí).
- **Orchestration**: cron lúc đầu, chuyển Airflow/Prefect/Dagster khi có nhiều phụ thuộc.
- **Serving**: Metabase trên bảng mart.
- **Undercurrents**: dbt test cho quality, alert khi job fail hoặc số dòng bất thường, secret không
  nằm trong code, mọi thứ trong Git.

Nói rõ khi nào nâng cấp: dữ liệu vượt khả năng một máy → Spark hoặc warehouse cloud; cần latency
giây → streaming. Và vì sao **không** dùng Kafka/Spark ngay: chi phí vận hành vượt xa lợi ích với một
người.

## Thiết kế thu thập dữ liệu cảm biến chất lượng không khí từ 10 000 thiết bị trong thành phố.

Các điểm cần đề cập:

- **Truyền**: thiết bị gửi qua MQTT tới broker/gateway (nhẹ, chịu mạng kém), gateway đẩy vào Kafka
  hoặc dịch vụ stream được quản lý (Kinesis, Pub/Sub).
- **Volume**: 10 000 thiết bị × 1 bản ghi/phút ≈ 14,4 triệu bản ghi/ngày, mỗi bản ghi nhỏ. Lưu dạng
  Parquet partition theo ngày (và có thể theo vùng), nén tốt vì time series.
- **Thời gian**: dùng event time của thiết bị nhưng đồng bộ đồng hồ (NTP) và ghi thêm ingestion time;
  chấp nhận dữ liệu đến trễ khi thiết bị mất mạng rồi gửi bù (watermark, cập nhật partition cũ).
- **Chất lượng**: đổi sentinel (kiểu `-200` của UCI) thành null, kiểm khoảng vật lý hợp lệ, phát hiện
  thiết bị "im lặng" (không gửi quá N phút) và drift so với trạm chuẩn.
- **Serving**: bảng tổng hợp theo giờ/khu vực cho dashboard; cảnh báo gần realtime khi chỉ số vượt
  ngưỡng (đây là phần thật sự cần streaming); dữ liệu thô lâu năm chuyển sang storage rẻ.
- **Undercurrents**: định danh thiết bị và xác thực (chứng chỉ), quyền truy cập, chi phí lưu trữ dài hạn.

## Thu thập dữ liệu có chứa thông tin cá nhân: bạn cần lưu ý gì về pháp lý và đạo đức?

- **Có cơ sở pháp lý và mục đích rõ ràng** để thu thập; chỉ lấy dữ liệu cần thiết (data minimization).
- **Nắm luật áp dụng**: GDPR (người dùng EU), LGPD (Brazil, ví dụ dữ liệu như Olist), ở Việt Nam là
  Nghị định 13/2023/NĐ-CP và Luật Bảo vệ dữ liệu cá nhân. Luật áp dụng theo người dùng, không chỉ theo
  nơi đặt server.
- **Bảo vệ kỹ thuật**: mask/hash/tokenize PII ngay khi ingest, tách cột nhạy cảm, phân quyền theo cột,
  mã hoá at rest và in transit.
- **Quyền của chủ thể dữ liệu**: phải xoá được dữ liệu của một người khi được yêu cầu, kể cả trong
  bản sao thô và backup. Thiết kế điều này từ đầu rẻ hơn nhiều so với làm sau.
- **Retention**: xoá theo lịch khi hết mục đích.
- **Dữ liệu công khai**: tuân điều khoản, `robots.txt`, rate limit, giấy phép (ví dụ CC BY 4.0 yêu cầu
  ghi nguồn). "Lấy được" không có nghĩa là "được phép".

## Stakeholder yêu cầu "dashboard realtime" cho doanh thu. Bạn phản hồi thế nào?

Không nói "không" ngay, cũng không nhận ngay. Làm rõ nhu cầu:

1. "Bạn xem dashboard lúc nào, và quyết định gì từ nó?" Thường là họp sáng hoặc theo dõi chiến dịch.
2. "Nếu số liệu trễ 15 phút, hay 1 giờ, thì có quyết định nào sai không?"
3. Trình bày trade-off bằng con số: batch hằng giờ có chi phí và độ phức tạp X; streaming có chi phí Y,
   cần vận hành 24/7, và số liệu "realtime" sẽ chưa khớp với số đối soát cuối ngày (đơn huỷ, hoàn tiền).

Thường kết quả là micro-batch 15–60 phút, hoặc realtime cho một chỉ số hẹp (số đơn trong flash sale)
còn doanh thu chính thức vẫn hằng ngày. Ghi lại thoả thuận thành SLA. Câu trả lời này cho thấy bạn hiểu
DE là nghề của **trade-off có giải thích**, không phải của công cụ.
