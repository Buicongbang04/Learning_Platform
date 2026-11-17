# Lời giải: SLO on-prem và chính sách hỗ trợ

## Hướng làm

1. **Bắt đầu từ tín hiệu có thật.** quillo 1.1.0 có `quillo_requests_total{route,status}` (route là mẫu đường dẫn),
   histogram `quillo_ask_seconds` với bucket 0,5/1/2/4/8/15/30/60/120/300 s, `quillo_model_up{kind}`, `quillo_documents`,
   `quillo_chunks` và `/healthz` có `checks`. Không có chỉ số nào đo thời gian từ lúc tệp vào inbox tới lúc nạp xong: SLI
   độ tươi phải đo bằng probe tổng hợp, và ghi khoảng trống đó thành yêu cầu cho đội sản phẩm.
2. **Ai đo thì người đó giữ bằng chứng.** Ở k3s của khách, Prometheus là của khách (scrape Service `quillo-api` cổng
   8080); nhà cung cấp không có VPN thường trực. Vậy SLO tính trên Prometheus của khách, khách xuất báo cáo tháng, hai bên
   cùng đọc một nguồn. Nếu khách không có Prometheus thì phương án tối thiểu là một CronJob probe do bạn viết, chạy trong
   namespace của khách, ghi kết quả vào ConfigMap/tệp mà support bundle thu được.
3. **Số mục tiêu theo phần cứng.** CPU-only, `llm-small` trả lời một câu ~4 s khi rảnh; 300 người, giờ cao điểm có hàng đợi
   (llama.cpp xử lý tuần tự theo slot). Mục tiêu độ trễ đặt ở ngưỡng trùng biên bucket (8 s) để tính chính xác bằng tỉ lệ,
   không phải `histogram_quantile` (nội suy tuyến tính trong bucket 4–8 s cho ra số "đẹp" nhưng không đúng).
4. **Loại trừ phải đi cùng trách nhiệm.** Mỗi thứ loại khỏi SLO (mất điện, đĩa đầy do khách, IdP của khách hỏng, cấu hình
   không được hỗ trợ) phải có bên chịu trách nhiệm và cách phát hiện; nếu không, phụ lục chỉ là danh sách miễn trừ.
5. **Mức độ theo ảnh hưởng**, không theo thành phần: "không ai hỏi đáp được" là S1 dù nguyên nhân là embed hay ACL.

## Bài mẫu (đạt 20/20)

```markdown
# Phụ lục: mục tiêu chất lượng dịch vụ và chính sách hỗ trợ quillo tại Công ty Luật X

## 1. Phạm vi và định nghĩa

Áp dụng cho quillo 1.1.x chạy trên cụm k3s do Công ty Luật X (khách) vận hành, namespace `quillo`. Giờ làm việc: 8:00–19:00
thứ Hai–thứ Sáu (giờ Việt Nam), trừ ngày nghỉ lễ. "Cửa sổ đo" là một tháng dương lịch, chỉ tính giờ làm việc. Bảo trì đã
thông báo trước ≥ 3 ngày làm việc và nằm ngoài giờ làm việc không tính vào SLO.

## 2. SLI và SLO

Nguồn đo: Prometheus của khách scrape `quillo-api:8080/metrics` mỗi 30 s và blackbox exporter probe
`http://quillo-api:8080/healthz` mỗi 60 s. Mọi biểu thức dưới đây chạy trên recording rule chỉ giữ mẫu trong giờ làm việc
(`hour()`, `day_of_week()` theo múi giờ UTC+7); quy tắc này nằm trong `slo-rules.yaml` gửi kèm.

| SLI | Công thức | Cửa sổ | Nơi đo, ai chạy | Mục tiêu |
| --- | --- | --- | --- | --- |
| Sẵn sàng (probe) | số probe `/healthz` trả 200 / tổng số probe | tháng, giờ làm việc | blackbox exporter của khách | ≥ 99,0% |
| Hỏi đáp thành công | `sum(increase(quillo_requests_total{route=~"/api/ask\|/ui/ask",status!~"5.."}[30d])) / sum(increase(quillo_requests_total{route=~"/api/ask\|/ui/ask"}[30d]))` | tháng, giờ làm việc | Prometheus của khách | ≥ 99,0% |
| Độ trễ hỏi đáp | `sum(increase(quillo_ask_seconds_bucket{le="8"}[30d])) / sum(increase(quillo_ask_seconds_count[30d]))` | tháng, giờ làm việc | Prometheus của khách | ≥ 95% câu trả lời ≤ 8 s |
| Độ tươi dữ liệu | probe: mỗi giờ làm việc, CronJob thả một tệp mẫu vào inbox và đo tới khi nó xuất hiện trong `GET /api/documents` | tháng | CronJob `quillo-freshness` (nhà cung cấp viết, chạy trong namespace của khách) | ≥ 95% probe ≤ 10 phút |

Vì sao hai SLI sẵn sàng: bộ đếm request chỉ thấy request **tới được** api; khi api chết, nó không ghi lỗi nào. Probe bắt
trường hợp đó, bộ đếm bắt lỗi chỉ xảy ra với câu hỏi thật (embed quá tải, LLM lỗi).

Vì sao 99,0% chứ không 99,9%: 99,0% giờ làm việc là ~2,3 giờ/tháng. Một node, CPU-only, nâng cấp và khởi động lại do khách
thực hiện; 99,9% (~14 phút/tháng) không đạt được mà không có HA, thứ hợp đồng này không bao gồm.

Vì sao 8 s: đo ở buổi nghiệm thu, p95 lúc rảnh 4–5 s với `llm-small` trên 2 vCPU của node k3s; 8 s là biên bucket gần nhất trên mức đó,
nên tỉ lệ tính chính xác, không phải ước lượng nội suy.

Độ trễ chỉ đúng với câu trả lời thành công; câu lỗi tính ở SLI thành công. Câu hỏi giống hệt nhau trả nhanh hơn (cache
prompt của llama.cpp), nên acceptance test dùng bộ câu hỏi đa dạng.

## 3. Ngân sách lỗi

Ngân sách = 1% số probe (hoặc câu hỏi) trong giờ làm việc của tháng. Khi tiêu quá 50% trước ngày 15: nhà cung cấp gửi
phân tích nguyên nhân trong 5 ngày làm việc và hai bên hoãn thay đổi không khẩn cấp (nâng cấp tính năng, đổi cấu hình)
tới tháng sau. Khi vượt 100%: họp kỹ thuật hai bên trong 10 ngày làm việc với kế hoạch khắc phục có hạn và người chịu
trách nhiệm; nếu nguyên nhân thuộc phần mềm, nhà cung cấp ưu tiên bản vá trước mọi việc khác cho khách này. Vi phạm do
loại trừ ở mục 4 không tiêu ngân sách.

## 4. Ranh giới trách nhiệm và loại trừ

| Việc | Khách | Nhà cung cấp |
| --- | --- | --- |
| Phần cứng, OS, k3s, lưu trữ, mạng, điện | vận hành, vá | khuyến nghị cấu hình tối thiểu (REQUIREMENTS.yaml) |
| Backup database hằng ngày, giữ 30 ngày, diễn tập restore mỗi quý | chạy (`ops/backup.sh --kubectl`), giữ bản sao | cung cấp script, có mặt ở buổi diễn tập |
| Nâng cấp quillo | duyệt CAB, chạy theo runbook | phát hành, viết runbook có rollback, hỗ trợ trong cửa sổ |
| SSO (Keycloak), nhóm người dùng | cấu hình IdP, mapper nhóm | tài liệu claim cần thiết, chẩn đoán phía quillo |
| Chứng chỉ TLS, reverse proxy | cấp, gia hạn | — |
| Prometheus, blackbox exporter, cảnh báo | vận hành | cung cấp rule, dashboard, CronJob độ tươi |
| Lỗi phần mềm quillo, model đi kèm | báo, cung cấp support bundle | sửa theo mức độ ở mục 5 |

Loại trừ (không tính vào SLO): sự cố hạ tầng của khách (điện, mạng, node, đĩa đầy, k3s), IdP của khách không phản hồi
(quillo trả 503 "IdP không phản hồi" có trong log), thay đổi cấu hình không theo tài liệu hay chưa báo nhà cung cấp, bản
phát hành ngoài danh sách hỗ trợ, tải vượt mức đã thống nhất (> 30 câu hỏi/phút kéo dài 15 phút). Mỗi loại trừ phải có
bằng chứng trong log hoặc chỉ số khi áp dụng; không có bằng chứng thì tính vào SLO.

## 5. Chính sách hỗ trợ

Kênh: cổng ticket (chính), điện thoại trực cho S1. Giờ hỗ trợ: giờ làm việc; S1 thêm 19:00–22:00 các ngày làm việc,
người trực theo lịch luân phiên công bố hằng tháng. Ngoài khung đó, S1 được phản hồi đầu giờ làm việc kế tiếp.

| Mức độ | Định nghĩa (ảnh hưởng) | Ví dụ với quillo | Phản hồi đầu | Cập nhật |
| --- | --- | --- | --- | --- |
| S1 | Không ai dùng được chức năng chính, hoặc nghi lộ dữ liệu | `/api/ask` lỗi với mọi người; người dùng thấy tài liệu của nhóm khác | 30 phút | mỗi 1 giờ |
| S2 | Chức năng chính suy giảm nặng, có workaround thủ công | nạp tài liệu dừng; độ trễ > 30 s phổ biến | 2 giờ làm việc | mỗi ngày |
| S3 | Lỗi ảnh hưởng một phần, không cấp bách | một loại PDF không trích được chữ | 1 ngày làm việc | mỗi tuần |
| S4 | Câu hỏi, yêu cầu tính năng | thêm loại tệp | 3 ngày làm việc | khi có tiến triển |

Truy cập và dữ liệu: nhà cung cấp không có truy cập thường trực. Chẩn đoán qua support bundle (`quillo-support.sh`, đã che
secret, không chứa nội dung tài liệu) hoặc phiên chia sẻ màn hình do IT khách điều khiển. Không bản dump, tài liệu, câu
hỏi hay câu trả lời nào rời hạ tầng của khách; khi cần tái hiện, nhà cung cấp dùng dữ liệu giả ở lab.

## 6. Bản phát hành được hỗ trợ và nâng cấp

Hỗ trợ bản minor hiện tại và bản trước đó (N, N−1); bản vá bảo mật cho N−1 trong 6 tháng sau khi N ra. Nâng cấp minor tối
đa mỗi quý, trong cửa sổ bảo trì do CAB của khách duyệt, theo runbook có backup trước, kiểm sau, và rollback đã diễn tập.
Migration của bản minor luôn tương thích ngược để rollback chỉ đổi image; bản nào có migration không quay lại được sẽ được
ghi rõ trong ghi chú phát hành và cần backup + restore làm đường lui.

## 7. Báo cáo hằng tháng

IT khách xuất từ Prometheus bảng 4 SLI (giá trị, mục tiêu, ngân sách đã tiêu) bằng dashboard nhà cung cấp cung cấp, kèm
danh sách sự cố đã áp loại trừ và bằng chứng. Nhà cung cấp gửi lại trong 5 ngày làm việc: ticket theo mức độ, thời gian
phản hồi thực tế, bản phát hành đang chạy so với danh sách hỗ trợ, và các khuyến nghị.
```

## Rubric chi tiết

- **SLI đo được (5)**: 5 khi mọi SLI có biểu thức chạy được trên chỉ số thật của quillo (đúng tên, đúng nhãn `route`,
  `status`, `le`) và nêu nơi đo; trừ 2 nếu SLI sẵn sàng chỉ dựa vào bộ đếm request (không thấy lúc api chết); trừ 2 nếu
  có SLI dựa vào chỉ số không tồn tại (vd. "thời gian nạp" từ `/metrics`) mà không nói cách đo khác.
- **Mục tiêu có lý do (3)**: trừ 1 nếu dùng `histogram_quantile` mà không nói nó là ước lượng nội suy; trừ 2 nếu chép 99,9%
  không giải thích.
- **Ngân sách lỗi (2)**, **trách nhiệm (3)**, **mức độ (3)**, **dữ liệu/truy cập (2)**, **phát hành (2)**: như bảng
  trong README bài; điểm tối đa khi có ví dụ cụ thể của quillo và hệ quả cho cả hai bên.

Bài mẫu đáp ứng đủ: bốn SLI có biểu thức và nguồn, hai SLI sẵn sàng bù nhau, độ trễ tính bằng tỉ lệ ở biên bucket, độ tươi
đo bằng probe vì sản phẩm không có chỉ số, loại trừ đi kèm bằng chứng, không cam kết 24/7.
