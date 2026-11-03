# Câu hỏi phỏng vấn: Monitoring và observability cho ML

## Monitoring khác observability thế nào, và vì sao ML cần cả hai?

Monitoring trả lời những câu bạn đã biết để hỏi trước: tỉ lệ lỗi, độ trễ p95, ngưỡng đã đặt sẵn. Observability là khả năng điều tra câu hỏi chưa
nghĩ tới từ dữ liệu hệ thống đã phát ra (metric, log, trace có ngữ cảnh) mà không phải sửa code và deploy lại. ML cần cả hai vì
lỗi điển hình là lỗi im lặng: HTTP 200, độ trễ đẹp, dự đoán sai. Monitoring bắt cái đã biết (RED, fallback, phiên bản model),
observability giúp điều tra cái chưa biết (vì sao riêng slice sân bay lệch), nhờ log dự đoán có `request_id` và feature.

## RED là gì, và thêm gì cho một service ML?

Rate, Errors, Duration cho mọi service: số yêu cầu, tỉ lệ lỗi, phân phối độ trễ. Với ML thêm ba thứ rẻ: histogram phân phối giá trị dự
đoán (bắt model trả giá trị dồn một chỗ hay sai version), tỉ lệ fallback (service sống nhưng không dùng model), và info metric phiên bản
model đang chạy. Chất lượng thật (MAE) cần nhãn nên đo từ log dự đoán nối với nhãn về muộn; phân phối dự đoán là tín hiệu sớm thay thế.

## Vì sao không đặt `request_id` làm label của metric?

Mỗi tổ hợp giá trị label là một chuỗi thời gian riêng; `request_id` có số giá trị bằng số yêu cầu nên số series tăng vô hạn, Prometheus
hết RAM và truy vấn chậm. Quy tắc: label chỉ có tập giá trị nhỏ, đóng và liệt kê được (mẫu route, phương thức, phiên bản model).
Chi tiết từng yêu cầu thuộc log hoặc trace. Một ca tinh vi: đường dẫn không khớp route mà dùng URL thật làm label, một con bot quét
là đủ làm nổ cardinality; gom về `unmatched`.

## Histogram hay summary cho độ trễ? Vì sao quantile không lấy trung bình được?

Histogram, vì gộp được giữa các instance: cộng bucket rồi `histogram_quantile`. Quantile của summary tính cục bộ trong mỗi
instance, và trung bình của các p95 không phải p95 của toàn bộ (toán học sai). Đổi lại histogram cần chọn bucket sớm (quanh SLO) và
quantile chỉ là ước lượng nội suy trong bucket, độ chính xác phụ thuộc bề rộng bucket. Đổi bucket sau này làm đứt lịch sử.

## Một alert tốt khác một alert tồi ở chỗ nào?

Alert tốt theo triệu chứng người dùng thấy (tỉ lệ lỗi, độ trễ), có `for` để lọc nhiễu, có `severity` để định tuyến và `runbook_url`
để người trực biết bước đầu, và so tỉ lệ thay vì số tuyệt đối. Alert tồi theo nguyên nhân ("CPU 85%"): hoặc nhiễu (CPU cao mà khách
không sao) hoặc im (khách lỗi mà CPU thấp). Mỗi cách hỏng một alert: mất số đo (`absent`) khác với tỉ lệ lỗi cao. Đánh đổi của `for`: dài thì ít nhiễu, phát hiện chậm.

## Bạn kiểm một rule alert như thế nào trước khi tin nó?

`promtool check rules` chỉ kiểm cú pháp. Cái đáng tin là `promtool test rules`: dựng chuỗi thời gian đầu vào rồi khẳng định alert bắn
hay không bắn ở từng thời điểm. Kiểm cả ba nhóm ca: bắn khi đáng bắn (lỗi kéo dài), im khi không (lỗi 1%, không traffic, lỗi ở route khác), tự hết sau khi phục hồi. Ca "im" luôn qua kể cả với
rule hỏng, nên bắt buộc có ca "bắn". Tốt hơn nữa: sinh chuỗi thời gian từ `/metrics` thật của service trong CI.

## Không có traffic thì alert tỉ lệ lỗi nên làm gì?

Không bắn. Tỉ lệ lỗi với mẫu số 0 là không xác định, không phải 100%; PromQL trả vector rỗng nên điều kiện không thoả. Việc "service không còn
nhận yêu cầu" là của một alert khác (`absent()` hoặc `up == 0`, hoặc alert rate dưới ngưỡng so với giờ này tuần trước). Gộp cả hai vào
một biểu thức hay thêm `or vector(0)` cho "có số" là cách làm mất khả năng giải thích alert.

## Hãy kể sự cố: alert không bao giờ kêu dù service lỗi thật. Bạn điều tra thế nào?

Tôi đi theo chuỗi mắt xích và loại trừ từng cái. Lỗi có thật không (log, phản hồi trực tiếp)? Prometheus có scrape và lưu số liệu
không (target `UP`, truy vấn tay)? Rule có được nạp và đánh giá không (trang Rules, trạng thái, thời gian đánh giá)? Từng nửa của biểu
thức trả gì trên dữ liệu thật (chạy riêng và đối chiếu với kết quả tôi mong đợi)? Khi alert `firing`, Alertmanager có nhận không và
route có đúng không? Trạng thái `inactive` kéo dài không chứng minh hệ thống khoẻ, nên bước đầu là chứng minh được alert **có thể** bắn trên đầu ra thật.
Sửa xong tôi thêm một ca "bắn" vào test của rule trong CI để lần sau chuyện này không lặp lại, và cân nhắc alert cho chính việc thiếu số đo.

## Error budget và burn rate là gì? Vì sao cảnh báo bằng hai cửa sổ?

SLO 99.5% trong 30 ngày cho error budget 0.5% (216 phút lỗi toàn phần). Burn rate là tốc độ đốt so với mức "vừa hết đúng cuối kỳ": burn 14.4
trong 1 giờ tiêu 2% budget. Cửa sổ dài một mình giữ alert bắn lâu sau khi đã sửa; cửa sổ ngắn một mình bắn vì spike ngắn; nối bằng `and` (thường
cửa sổ ngắn bằng 1/12 cửa sổ dài) cho alert vừa đáng tin vừa tự tắt nhanh. Nhiều tầng: cháy nhanh đánh thức người trực, cháy chậm chỉ cần ticket.
Budget còn là công cụ chính sách: cạn thì đóng băng thay đổi rủi ro.

## Alertmanager làm gì mà Prometheus không làm? Giải thích route, group, inhibit.

Prometheus chỉ đánh giá rule và sinh alert; Alertmanager lo phần con người: gom (`group_by`) nhiều alert thành một thông báo, định tuyến (`route`) theo
nhãn tới đúng receiver, im lặng (`silence`), và `inhibit` (im alert phụ khi có alert nặng hơn). Ví dụ critical của service ETA im warning của đúng
service ETA nhờ `equal: [service]`; thiếu `equal` thì một critical của bất kỳ service nào làm im mọi warning khác. Thời gian khác nhau theo mức khẩn: `group_wait` ngắn cho critical, dài cho warning.

## Vì sao chọn Prometheus (và Grafana) cho đội này, khi có Datadog hay CloudWatch?

Ràng buộc quyết định: dữ liệu không được rời mạng, ngân sách phần mềm bằng 0, đội có người vận hành, và muốn chuẩn mở (PromQL, OpenMetrics, OpenTelemetry) để có đường thoát.
Đổi lại phải vận hành: lưu trữ dài hạn cần Thanos hoặc Mimir, HA cần tự dựng, và cardinality là việc của mình. Nếu đội nhỏ, đã nằm trên một đám mây và không muốn
vận hành, dịch vụ quản lý hợp lý hơn, chấp nhận chi phí tăng theo số series và khoá nhà cung cấp. Bắt đầu từ ràng buộc, không từ tính năng.

## Dashboard as code là gì và vì sao quan trọng?

Dashboard là JSON, đặt trong Git, nạp vào Grafana bằng provisioning (provider kiểu file, `allowUiUpdates: false`). Lợi ích: review được,
khôi phục được khi mất volume, cùng một dashboard ở mọi môi trường (datasource là biến). Đánh đổi: sửa nhanh bằng chuột không còn, và
JSON export có `id`, uid cứng cần dọn. Kiểm tự động bằng cách đẩy qua API và chạy từng truy vấn qua `/api/ds/query`.

## Thiết kế hệ thống: giám sát một model ETA phục vụ 400 yêu cầu mỗi giây, nhãn về muộn 1 giờ.

Bốn lớp. (1) Service: RED, histogram độ trễ quanh SLO, SLO với burn-rate alert, alert `absent`. (2) Model: histogram phân phối dự đoán, tỉ lệ fallback,
info phiên bản; alert khi trung vị dự đoán lệch so với cùng giờ tuần trước (tín hiệu sớm, nhiều dương tính giả). (3) Chất lượng: log dự đoán JSON có
`request_id`, `model_version`, feature allow-list; nối nhãn khi về để tính MAE theo phiên bản và slice, cảnh báo khi nhãn không về (pipeline nhãn hỏng cũng là sự cố).
(4) Vận hành: ngân sách series tính bằng số, alert có runbook và severity, routing critical tới người trực và warning tới ticket, dashboard as code, trace lấy mẫu theo đuôi.
Rủi ro: cardinality ngầm, mùa vụ làm nhiễu alert so sánh, một Prometheus là điểm hỏng đơn.

## Log dự đoán cần chứa gì và không được chứa gì?

Cần: `ts` UTC, `request_id`, `model_version`, giá trị dự đoán, cờ fallback, các feature cần cho slice và kiểm skew. Không được: PII (số điện thoại, tên
khách) và thân yêu cầu thô; dùng allow-list thay vì deny-list để trường mới không tự lọt vào. Giữ lâu hơn log truy cập để nhãn về muộn vẫn nối được. Ghi đúng một dòng JSON,
`NaN` không hợp lệ phải bị chặn từ đầu.

## Tail-based sampling khác head-based sampling thế nào cho trace?

Head-based quyết định giữ hay bỏ ngay ở đầu trace (ví dụ 5%): rẻ, đơn giản, nhưng bỏ lỡ đúng những trace lỗi và chậm vì chưa biết kết quả. Tail-based đợi
trace hoàn thành rồi mới quyết (giữ 100% lỗi hoặc chậm hơn 1 giây, mẫu nhỏ phần còn lại): chất lượng cao hơn nhưng cần collector giữ trace trong bộ nhớ và phức tạp hơn khi vận hành.
