# Câu hỏi phỏng vấn: Observability

## Monitoring khác observability thế nào? Metrics, log, trace mỗi thứ trả lời câu hỏi gì?

Monitoring là tập câu hỏi đã biết trước, viết thành dashboard và alert ("tỉ lệ lỗi có quá 5% không"). Observability là thuộc tính của hệ
thống: dữ liệu nó phát ra đủ giàu để trả lời câu hỏi **chưa** biết trước mà không phải deploy thêm code ("vì sao chỉ khách ở bang BA chậm
từ 21:00").

- Metrics: số đã gộp theo thời gian, rẻ, giữ lâu; trả lời "bao nhiêu, có tệ hơn không". Hợp cho alert và xu hướng.
- Log: sự kiện rời rạc có ngữ cảnh; trả lời "chuyện gì đã xảy ra với request này, lỗi nói gì".
- Trace: cây span của một request qua nhiều service; trả lời "request đi đâu, chậm ở bước nào".
- Profiles (tín hiệu thứ tư): CPU, bộ nhớ theo dòng code.

Điểm mạnh là nối chúng: metric báo lỗi tăng, exemplar dẫn tới trace lỗi, `trace_id` dẫn tới dòng log.

## RED, USE và Four Golden Signals khác nhau ở đâu? Áp cho Olist Shop thế nào?

- RED cho service xử lý request: Rate, Errors, Duration. API Olist: request/giây theo route, tỉ lệ 5xx, p95 thời gian xử lý.
- USE cho tài nguyên: Utilization, Saturation, Errors. Pool kết nối Postgres: tỉ lệ kết nối đang dùng, số request đang chờ kết nối, lỗi
  timeout lấy kết nối.
- Four Golden Signals (Google SRE): latency, traffic, errors, saturation, nhìn từ người dùng. Thêm saturation cho worker: độ dài hàng đợi,
  tuổi job cũ nhất.

RED/Golden Signals dùng cho alert page (triệu chứng), USE dùng để chẩn đoán (nguyên nhân).

## Vì sao phải `rate()` trước rồi mới `sum()`? Và vì sao không lấy trung bình p95 của các replica?

`rate` hiểu counter reset trên **từng series**: một pod restart, counter của nó về 0, `rate` nhận ra và không tính giá trị âm. Nếu `sum`
trước, tổng tụt xuống khi một pod restart và `rate` hiểu là reset của cả tổng, cho ra một đỉnh giả rất lớn. Vậy luôn
`sum by (...) (rate(x_total[5m]))`.

Quantile không cộng hay lấy trung bình được: trung bình của mười p95 không phải p95 của toàn bộ request (một replica nhận 90% traffic thì
nó phải nặng hơn). Dùng histogram: cộng bucket của mọi replica rồi `histogram_quantile(0.95, sum by (le) (rate(..._bucket[5m])))`.
Summary tính quantile ở client nên không gộp được.

## Cardinality là gì? Kể một lần nó gây sự cố và cách phòng.

Cardinality là số series: mỗi tổ hợp nhãn khác nhau là một series, Prometheus giữ series đang hoạt động trong RAM. Một nhãn có tập giá trị
không bị chặn (id người dùng, email, id phiên, id request) làm số series tăng theo dữ liệu chứ không theo số thứ cần đo; RAM tăng mãi, khởi
động lại chậm vì WAL dài, query dashboard timeout.

Phòng: review nhãn mới như review schema ("bao nhiêu giá trị, có chặn không"); `sample_limit` và `label_limit` ở scrape config để target
vượt giới hạn bị từ chối thay vì làm sập cả Prometheus; alert về `prometheus_tsdb_head_series` tăng bất thường; chi tiết từng request để
cho log và trace, nối bằng exemplar. Chẩn đoán: `topk(10, count by (__name__) ({__name__=~".+"}))`, rồi đếm giá trị từng nhãn của metric
đứng đầu, hay trang `Status → TSDB Status`.

## Recording rule dùng để làm gì? Đặt tên thế nào và test ra sao?

Recording rule tính trước biểu thức theo lịch và lưu thành series mới: dashboard chạy query đắt liên tục, nhiều alert dùng chung một biểu
thức, cần dashboard và alert dùng đúng một định nghĩa. Tên theo `level:metric:operations`, ví dụ `job:http_requests_errors:ratio_rate5m`:
nhìn tên biết còn nhãn `job`, là tỉ lệ, cửa sổ 5 phút.

Test bằng `promtool test rules`: khai chuỗi thời gian đầu vào (`0+60x20`), thời điểm, giá trị mong đợi cho recording rule và tập alert
mong đợi. Unit test chỉ chứng minh rule đúng với dữ liệu tự viết, nên thêm: mỗi alert có ca **phải bắn**, kiểm rule ra số trên Prometheus
staging với dữ liệu thật, và nếu muốn chắc test đủ chặt thì thử làm hỏng rule (đột biến) xem test có fail không.

## `for` trong alert rule làm gì? Đặt bao lâu là hợp lý?

Alert ở trạng thái `pending` cho tới khi biểu thức đúng liên tục đủ thời gian `for`, rồi mới `firing` và gửi Alertmanager. Một lần đánh giá
sai là quay về `inactive` và đếm lại. `for` lọc dao động ngắn nhưng làm phát hiện trễ đúng bằng nó (cộng thời gian để `rate` có đủ mẫu).

Page: thường 2 tới 5 phút với cửa sổ 5 phút. Ticket: 15 tới 60 phút. Quá dài (1 giờ cho page) nghĩa là khách phát hiện trước. Với tín hiệu
dao động mạnh, alert có thể không bao giờ đủ `for`; khi đó dùng cửa sổ dài hơn trong `rate` thay vì kéo `for`, hay `keep_firing_for` để
tránh flapping khi hết.

## Vì sao nên alert theo triệu chứng thay vì nguyên nhân? Có ngoại lệ không?

Triệu chứng (lỗi, chậm, không đặt được hàng) là thứ người dùng thấy; một alert triệu chứng phủ mọi nguyên nhân, kể cả nguyên nhân chưa nghĩ
tới. Alert nguyên nhân (CPU 90%, một pod restart) hay báo giả và không nói người dùng có bị gì không; người trực bị đánh thức vì nó vài lần
sẽ quen bỏ qua mọi page.

Ngoại lệ: nguyên nhân báo trước đủ lâu để xử lý trong giờ làm, như đĩa đầy trong 3 ngày (`predict_linear`), chứng chỉ hết hạn trong 14 ngày,
backup thất bại. Chúng là ticket, không phải page. Và alert về chính hệ thống alert (Watchdog, scrape lỗi).

## Alertmanager xử lý một alert thế nào? Grouping, inhibition, silence khác nhau ra sao?

Alert tới → kiểm inhibit và silence (bị chặn thì `suppressed`) → đi cây route, khớp route con đầu tiên → gom nhóm theo `group_by`, chờ
`group_wait` → gửi receiver; cập nhật nhóm mỗi `group_interval`, nhắc lại mỗi `repeat_interval`.

- Grouping: gộp nhiều alert cùng nhóm thành một thông báo (mười pod lỗi thành một tin).
- Inhibition: luật cố định, một alert nguồn đang firing chặn alert đích; `equal` liệt kê nhãn phải trùng giữa nguồn và đích. Dùng cho quan
  hệ phụ thuộc lâu dài ("service down" chặn "error rate cao" cùng service).
- Silence: tắt tạm theo matcher, có người tạo, lý do và hạn; dùng cho việc có kế hoạch hay đang xử lý.

`amtool config routes test` kiểm route nhưng không mô phỏng inhibition; muốn chắc phải gửi alert giả vào một Alertmanager thật.

## Làm sao biết chính hệ thống alert còn sống?

Một hệ thống alert hỏng trông giống hệt lúc mọi thứ ổn. Các lớp:

- Watchdog: rule luôn bắn, route tới dịch vụ heartbeat bên ngoài; heartbeat ngừng thì dịch vụ đó page qua kênh khác. Nó chứng minh
  Prometheus đánh giá rule và Alertmanager gửi được, không chứng minh mọi alert tới đúng người.
- Alert về lỗi đánh giá rule, thông báo gửi lỗi, target `up == 0`, số alert bị suppress kéo dài.
- Test rule và cấu hình trong CI, kiểm rule ra số trên dữ liệu thật, diễn tập page định kỳ (gửi alert thử, xác nhận pager rung).
- Đo: sự cố khách báo trước alert là "alert bỏ sót", mỗi lần phải có action item.

## Bạn đưa dashboard Grafana vào Git như thế nào? Lỗi hay gặp là gì?

Provisioning: datasource và provider dashboard khai trong YAML ở `/etc/grafana/provisioning/`, dashboard JSON trong thư mục provider quét;
`allowUiUpdates: false` để mọi thay đổi đi qua PR. Dự án lớn sinh JSON bằng Grafonnet, Foundation SDK hay Terraform provider `grafana`.

Lỗi hay gặp: JSON export có `${DS_PROMETHEUS}` (chỉ thay khi import tay) nên panel báo không có datasource; `uid` datasource khác giữa môi
trường; cửa sổ `rate` ghi cứng `[5m]` thay vì `$__rate_interval`; counter vẽ thô; panel "No data" vì sai tên nhãn, chỉ phát hiện khi sự cố.
Kiểm trong CI: dựng Grafana, chạy từng query qua `/api/ds/query`, đòi có dữ liệu trên môi trường test.

## Loki khác Elasticsearch ở đâu? Khi nào chọn cái nào?

Loki chỉ index nhãn của stream, nội dung nén thành chunk trên object storage; query lọc theo nhãn rồi quét chunk. Elasticsearch/OpenSearch
index toàn văn mọi trường. Hệ quả: Loki rẻ hơn nhiều lần về đĩa và RAM, vận hành đơn giản hơn, hợp khi log đọc khi có sự cố và lọc theo
service, thời gian, `trace_id`. Elasticsearch nhanh khi tìm chuỗi bất kỳ trên phạm vi rộng, aggregation phức tạp, SIEM, nhưng tốn tài nguyên
và vận hành cluster khó (shard, heap, mapping).

Nhãn Loki cũng phải ít và chặn được như Prometheus; `trace_id`, `request_id` để trong nội dung hay structured metadata, không làm nhãn stream.

## Đi từ một khiếu nại "đơn của tôi lỗi lúc 21:15" tới nguyên nhân, bạn làm gì?

1. Lấy `request_id` (trả về trong header `X-Request-ID`) hay id đơn, khoảng thời gian.
2. LogQL: `{service_name="olist-shop-api"} | json | request_id = "..."` (so đúng giá trị, không `|=` vì khớp chuỗi con). Đọc `status`,
   `trace_id`.
3. Mở trace theo `trace_id` trong Jaeger (Grafana có derived field làm link): span nào lỗi, span nào chậm, có span DB không.
4. Nếu request đi qua hàng đợi: lọc log worker theo `trace_id`, không theo `request_id` (worker có id riêng).
5. Từ trường hợp đơn lẻ lên tổng thể: metric RED của route đó quanh 21:15, có phải nhiều người cùng bị không; deploy nào gần đó.

## OpenTelemetry Collector làm gì mà app không tự gửi thẳng tới backend?

Collector tách app khỏi backend: app chỉ biết OTLP và địa chỉ Collector. Collector làm việc chung cho mọi service: batch và retry, giới hạn
bộ nhớ, gắn attribute môi trường, xoá trường nhạy cảm, tail sampling, biến trace thành metric (spanmetrics), gửi song song nhiều backend khi
chuyển vendor. Pipeline gồm receiver, processor (theo thứ tự, `memory_limiter` đầu, `batch` cuối), exporter, và connector nối pipeline.
Triển khai agent (cạnh app) cộng gateway (trung tâm, nơi tail sampling) là mô hình phổ biến.

## Head sampling và tail sampling khác nhau thế nào? Thiết kế sampling cho API 5.000 request/giây.

Head sampling quyết ở span gốc, trước khi biết request lỗi hay chậm: rẻ, nhất quán (`ParentBased`), nhưng giữ 1% là mất 99% trace lỗi.
Tail sampling quyết ở Collector sau khi trace xong: giữ mọi trace lỗi, chậm, và một tỉ lệ trace thường; đổi lại Collector giữ span trong RAM
chờ `decision_wait`, và mọi span của một trace phải tới cùng Collector.

Thiết kế: SDK gửi 100% (hay head 20% nếu chi phí mạng là vấn đề) tới tầng Collector thứ nhất, exporter `loadbalancing` theo `traceID` tới
tầng gateway chạy `tail_sampling`: policy giữ status ERROR, latency trên 1 giây, 1% probabilistic. Spanmetrics tính ở tầng thứ nhất, trước
sampling, để RED không lệch. Theo dõi RAM của gateway và số trace bị bỏ vì quá `num_traces`.

## Trace bị đứt giữa api và worker. Bạn tìm nguyên nhân ở đâu?

Trace "đứt" nghĩa là span của worker có `trace_id` mới thay vì là con của span bên api. Context không tự đi qua hàng đợi: HTTP có header
`traceparent`, còn message trong Redis, Kafka, SQS phải được code ghi context vào (header của message, hay một trường trong payload) và bên
consume phải đọc ra làm parent. Kiểm: payload trong hàng đợi có `traceparent` không; propagator hai bên có cùng định dạng (W3C, B3) không;
bên consume có tạo span với parent đã extract không, hay tạo span mới; có thư viện nào bọc client mà mất context (thread pool, async) không.
Với job xử lý theo lô, dùng span link thay vì quan hệ cha con.

## PII trong log: bạn xử lý thế nào ở một hệ thống đã chạy ba năm?

1. Tìm: quét log hiện có tìm mẫu email, số điện thoại, số thẻ; liệt kê nguồn (logger nào, trường nào).
2. Chặn ở nguồn: sửa code log id nội bộ thay vì PII; che hay băm có muối khi cần đối chiếu; formatter loại trường nhạy cảm.
3. Lưới an toàn: processor ở Collector (`attributes`, `transform`, `redaction`) xoá hay che trường đã biết; không thay được bước 2.
4. Dữ liệu cũ: retention theo loại (log debug vài ngày), xoá có chủ đích nếu luật yêu cầu; giới hạn ai query được stream nhạy cảm, có audit.
5. Chống tái diễn: test hay lint chặn log trường nhạy cảm, review logging trong PR.

## Công ty 40 service, không có team platform, đang cân nhắc Datadog và tự dựng stack Grafana. Bạn tư vấn thế nào?

Hỏi trước: bao nhiêu host, GB log mỗi ngày, số series, ai sẽ vận hành, dữ liệu có ràng buộc pháp lý không. Không có người vận hành thì tự
dựng Prometheus HA, Loki, Tempo, Mimir là một dự án lớn và rủi ro; SaaS (Datadog, New Relic, Grafana Cloud) cho giá trị nhanh. Đổi lại là
hoá đơn theo host, sản phẩm, custom metric, GB log, dễ tăng ngoài dự tính.

Khuyến nghị: instrument bằng OpenTelemetry và đi qua Collector ngay từ đầu, để đổi vendor hay quay về tự host chỉ là đổi exporter. Ước tính
chi phí với số liệu thật, đặt hạn mức ingest, lọc log và nhãn ở Collector. Xem lại sau 12-18 tháng khi quy mô và đội ngũ đã rõ.
