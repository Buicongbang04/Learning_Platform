# Câu hỏi phỏng vấn: streaming feature và real-time ML

## Event time và processing time khác nhau thế nào, và feature của bạn nên tính theo cái nào?

Event time là lúc sự kiện xảy ra (ghi trong payload), processing time là lúc hệ thống xử lý nó. Feature cho model nên tính theo event
time: kết quả xác định, phát lại cho ra cùng giá trị, và khớp với cách tính offline khi huấn luyện. Tính theo processing time thì
consumer chết rồi đọc dồn backlog là cửa sổ phình to, cửa sổ lúc chết rỗng, và mọi lần replay ra số khác. Cái giá của event time là
phải chọn chờ sự kiện muộn bao lâu (watermark, allowed lateness) và xử lý sự kiện đến sau đó.

## Watermark là gì? Chọn allowed lateness thế nào?

Watermark là ước lượng của hệ thống rằng mọi sự kiện có event time nhỏ hơn mức đó đã đến; cửa sổ đóng khi `window_end <= watermark`.
Heuristic phổ biến là `max event time - lateness`. Chọn lateness từ phân phối thật của `ingestion time - event time` (ví dụ p99 hoặc
p99.9), đối chiếu với SLO freshness: lateness cộng thẳng vào độ trễ của feature cửa sổ. Sự kiện muộn hơn thế thì đếm, đưa ra side output
và backfill vào offline store để dữ liệu huấn luyện vẫn đủ.

## Một feature online đứng yên dù topic vẫn có dữ liệu và consumer lag gần 0. Bạn chẩn đoán thế nào?

Lag gần 0 nghĩa là consumer đọc kịp, vấn đề nằm sau bước đọc: sự kiện bị bỏ hoặc cửa sổ không đóng. Tôi xem bộ đếm sự kiện bị bỏ vì trễ,
lỗi parse, trùng; xem độ trễ của watermark so với đồng hồ thật (âm hoặc nhảy bậc là có sự kiện "từ tương lai" kéo watermark lên, ví dụ
timestamp mili giây hiểu thành giây, hay offset múi giờ bị ghi đè); với nhiều partition, xem có partition rảnh giữ watermark của job đứng
yên không; cuối cùng xem phía ghi: online store có từ chối ghi vì timestamp cũ hơn giá trị đã có không. Phòng ngừa: loại sự kiện có event
time vượt ingestion time quá ngưỡng, cảnh báo độ trễ watermark và tỉ lệ bị bỏ.

## Tumbling, sliding, session window: cho ví dụ feature dùng từng loại.

Tumbling: số chuyến mỗi 15 phút của zone, mỗi sự kiện vào đúng một cửa sổ, rẻ nhất. Sliding: số giao dịch của thẻ trong 10 phút gần nhất
cập nhật mỗi phút, một sự kiện vào `size / step` cửa sổ nên tốn state và ghi hơn. Session: số trang xem và thời lượng của một phiên duyệt
web, cửa sổ dài thay đổi theo khoảng lặng `gap`. Với feature "N phút gần nhất" thật sự liên tục, nhiều hệ thống dùng sliding với bước nhỏ
hoặc lưu sự kiện thô và tính lúc đọc.

## Làm sao để sự kiện trùng không làm sai feature?

Ba lớp: producer idempotent (và transaction nếu cần exactly-once trong Kafka) để retry không ghi hai lần; `event_id` gắn ở nguồn và
consumer bỏ id đã gặp trong một khoảng state có hạn; ghi feature idempotent theo khoá `(thực thể, cửa sổ)` bằng upsert để xử lý lại một
đoạn không cộng dồn. Chống trùng chạy trước kiểm tra trễ để đếm đúng loại lỗi.

## Feast push source dùng để làm gì, khác materialize thế nào?

Materialize đọc offline store theo lịch rồi ghi online, hợp với feature batch nhưng làm feature cũ bằng chu kỳ lịch. Push source cho job
stream ghi thẳng DataFrame vào online, offline hoặc cả hai ngay khi tính xong. Ghi cả offline là quan trọng: dữ liệu huấn luyện lấy đúng
những giá trị đã phục vụ, với cùng timestamp, nên join point-in-time không lệch. Push không làm thay phần tính toán: cửa sổ, watermark,
trùng lặp vẫn là việc của engine stream.

## Nêu các nguồn skew giữa train và serve đặc thù cho feature stream.

Timestamp của dòng feature (phải là `window_end`; dùng `window_start` là nhìn thấy tương lai khi huấn luyện); ghi đè online bằng giá trị cũ
khi replay hay late firing (online store phải giữ timestamp lớn nhất); khác kiểu dữ liệu (float32 với float64) hay khác cách tính (có bỏ
trùng hay không, biên cửa sổ); feature của chính request không có trong stream lúc serving nhưng có trong offline. Cách bắt: job đối soát so
giá trị online với tính batch trên cùng dữ liệu, và log feature lúc serving để huấn luyện (log-and-wait).

## Freshness của feature đo thế nào cho đúng? Nêu một cách đo sai phổ biến.

Freshness là thời gian từ event time tới lúc giá trị đọc được trong online store, báo theo phân vị (p50, p95), tốt nhất đo ở phía đọc: mỗi
lần serving đọc feature, ghi `now - event_timestamp`. Cách đo sai phổ biến: đo từ lúc consumer nhận tới lúc push xong, bỏ sót mạng tới
broker, consumer lag và nhất là thời gian chờ cửa sổ đóng; trong bài thực hành, cách đo đó cho số đẹp gần gấp bốn lần thực tế. Với cửa sổ
15 phút, freshness tối thiểu đã là nửa cửa sổ cộng lateness.

## Khi nào bạn dùng online learning, khi nào không?

Dùng khi nhãn về nhanh, drift nhanh và liên tục, rủi ro mỗi quyết định thấp, và có cổng chặn dữ liệu bẩn. Không dùng khi nhãn về chậm
(online thực ra học quá khứ xa), khi quyết định cần giải trình hay kiểm toán, khi dữ liệu có thể bị đầu độc, hoặc khi huấn luyện lại theo
lịch kèm cổng đánh giá đã đủ. Luôn đánh giá bằng prequential (test-then-train). Cách dùng an toàn phổ biến: model batch làm chính, model
online chạy shadow làm chỉ báo drift.

## Model chống gian lận chặn giao dịch, và tỉ lệ gian lận trong dữ liệu huấn luyện giảm dần mỗi tháng. Đó là tin tốt không?

Chưa chắc. Giao dịch bị chặn không có nhãn, nên dữ liệu chỉ chứa giao dịch đã được cho qua; model chặn càng nhiều thì tỉ lệ quan sát
càng thấp dù gian lận thật không đổi, và huấn luyện lại trên đó làm model mù dần với vùng rủi ro cao. Kiểm bằng một nhóm exploration (cho
qua ngẫu nhiên một phần nhỏ giao dịch bị chặn, ghi propensity lúc quyết định) và so ước lượng IPW với tỉ lệ ngây thơ. Không có exploration
thì không đo được, và phải nói thẳng là không đo được.

## Chọn Flink, Spark Structured Streaming hay Bytewax cho một pipeline feature mới?

Theo đội và yêu cầu, không theo độ nổi tiếng. Flink khi cần độ trễ mili giây, state lớn (cửa sổ cho hàng chục triệu thẻ), event time đầy đủ
và exactly-once, và đội vận hành được JVM. Spark Structured Streaming khi đã có Spark, chấp nhận độ trễ micro-batch vài trăm ms tới vài
giây, và muốn dùng chung code với feature batch. Bytewax hay consumer Python có checkpoint khi đội nhỏ, Python, tải vừa; đo rồi mới mở
rộng. Câu trả lời tốt nói rõ ngưỡng chuyển: tải, state, độ trễ, người vận hành.

## Consumer lag của pipeline feature tăng lúc 2 giờ sáng. Bạn làm gì trong 15 phút đầu?

Đánh giá tác động trước: lag theo thời gian (không theo message) và freshness hiện tại, đã vi phạm SLO chưa, model đang dùng feature cũ bao
lâu. Rồi xem lag từng partition: đều mọi partition và lưu lượng vào tăng là tải thật (thêm consumer tới tối đa số partition); đều nhưng tốc
độ xử lý giảm là phía ghi chậm; răng cưa là rebalance liên tục; dồn một partition là key nóng hoặc message độc. Trong lúc chờ, bảo vệ model
bằng fallback theo tuổi feature. Nhảy offset hay bỏ message độc là hành động mất dữ liệu, cần người có thẩm quyền duyệt và lên lịch backfill.

## Thiết kế feature "số giao dịch của thẻ trong 1 phút" cho chống gian lận dưới 100 ms. Stream có đủ nhanh không?

Phụ thuộc SLO freshness. Pipeline stream có freshness vài giây tới vài chục giây; một cuộc tấn công thử thẻ 50 lần trong 10 giây sẽ lọt
trước khi feature kịp cập nhật. Với feature cần tươi tuyệt đối, đếm đồng bộ trên đường request: bộ đếm nguyên tử theo thẻ trong store
nhanh (Redis `INCR` với TTL theo bucket thời gian), đọc và tăng trong cùng lời gọi. Feature dài hơn (10 phút, 1 giờ) đi qua stream. Nói rõ
đánh đổi: đếm đồng bộ thêm một lần ghi trên đường nóng và phải tự xử lý trùng khi cổng retry.

## Nhiều partition làm watermark phức tạp hơn thế nào?

Mỗi partition có watermark riêng (sự kiện trong một partition gần đúng thứ tự, giữa các partition thì không), và watermark của operator là
nhỏ nhất qua các partition đầu vào. Một partition không có sự kiện (key thưa, producer chết) giữ watermark của cả job đứng yên, mọi cửa sổ
không đóng. Flink xử lý bằng đánh dấu nguồn rảnh (`withIdleness`) sau một khoảng; cái giá là sự kiện đến sau đó từ partition ấy có thể
thành trễ. Khi gỡ lỗi "feature không cập nhật", luôn xem watermark theo từng partition.
