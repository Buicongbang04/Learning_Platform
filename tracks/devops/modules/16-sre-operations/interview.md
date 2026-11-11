# Câu hỏi phỏng vấn: SRE và vận hành

## SRE khác DevOps thế nào?

DevOps là văn hoá và tập thực hành: phá bức tường giữa người viết code và người vận hành, tự động hoá, đo, chia sẻ trách nhiệm. SRE (Site
Reliability Engineering, từ Google) là **một cách cụ thể** để làm DevOps: dùng kỹ năng kỹ sư phần mềm để giải bài toán vận hành, với các
công cụ định lượng là SLO, error budget, trần toil 50%, postmortem không đổ lỗi. Google tóm lại "class SRE implements interface DevOps".
Trên thực tế, chức danh khác nhau theo công ty: team DevOps/platform thường xây công cụ và pipeline, team SRE thường sở hữu độ tin cậy
của dịch vụ production và on-call. Trả lời tốt nêu được điểm chung (tự động hoá, đo lường, chia sẻ trách nhiệm) và điểm SRE thêm vào
(con số cho độ tin cậy, ngân sách rủi ro).

## Giải thích SLI, SLO, SLA bằng một ví dụ.

Với trang tra đơn của Olist:

- **SLI**: tỉ lệ request `GET /orders/{id}` không trả 5xx, đo ở load balancer.
- **SLO**: 99,5% trong 30 ngày trượt. Team cam kết với chính mình và product.
- **SLA**: hợp đồng với đối tác bán hàng: availability theo giờ từ 99,0% trở lên, thấp hơn thì trả 10% credit; giờ bảo trì báo trước
  không tính.

SLA lỏng hơn SLO để còn thời gian sửa trước khi mất tiền. SLO đo cả latency và tính cả bảo trì vì khách vẫn bị ảnh hưởng; SLA thường chỉ
đo thứ dễ chứng minh. Bài Basic 01 cho thấy một tháng mà SLO đã cạn budget nhưng SLA chỉ mất 10% credit.

## Làm sao chọn SLI tốt cho một dịch vụ mới?

1. Liệt kê hành trình quan trọng của khách (tra đơn, đặt hàng, thanh toán), không liệt kê endpoint.
2. Với mỗi hành trình chọn loại SLI: availability (thành công), latency (đủ nhanh), freshness (dữ liệu đủ mới), correctness.
3. Đo ở chỗ gần khách nhất mà đáng tin: load balancer, gateway, hay probe tổng hợp; metric trong pod bỏ sót lúc pod chết.
4. Viết dạng tỉ lệ sự kiện tốt trên tổng, định nghĩa rõ "hợp lệ" (bỏ 4xx do khách gửi sai?).
5. Đặt SLO theo dữ liệu lịch sử và nhu cầu thật, thấp hơn 100%, xem lại mỗi quý.

CPU, RAM, số pod là nguyên nhân, dùng cho dashboard chẩn đoán, không làm SLI.

## Error budget dùng để làm gì? Khi budget cạn thì sao?

Error budget là phần không đáng tin cậy được phép: SLO 99,9% cho 0,1% request lỗi, khoảng 43 phút mỗi 30 ngày. Nó biến tranh luận "nhanh
hay ổn định" thành con số chung: còn budget thì release, thử nghiệm, chấp nhận rủi ro; budget cạn thì chuyển sức sang độ tin cậy. Chính
sách error budget ký trước quy định hành động: ví dụ dưới 25% thì dừng feature, cạn thì chỉ rollback và vá bảo mật, postmortem bắt buộc,
ngoại lệ do VP Engineering duyệt. Luôn giữ đường cho rollback, vì đóng băng cả rollback làm sự cố dài thêm. Sự cố do bên ngoài (cổng
thanh toán) vẫn tiêu budget nhưng action item chuyển sang timeout, fallback, hợp đồng.

## Burn rate là gì? Vì sao alert theo nhiều cửa sổ?

Burn rate là tỉ lệ lỗi chia phần được phép lỗi: SLO 99,9% mà lỗi 1,44% là burn rate 14,4, tiêu 2% budget 30 ngày mỗi giờ. Alert một
ngưỡng cố định vừa ồn (một phút lỗi lẻ cũng page) vừa bỏ sót lỗi rỉ rả. SRE Workbook đề xuất bốn mức: page khi 14,4 trên 1h và 5m, hay 6
trên 6h và 30m; ticket khi 3 trên 1d và 2h, hay 1 trên 3d và 6h. Cửa sổ dài đảm bảo sự cố đủ lớn; cửa sổ ngắn (khoảng 1/12) đảm bảo nó
còn đang diễn ra để alert tắt nhanh khi hết. Mỗi SLO một bộ recording rule theo cửa sổ, alert đọc lại; sinh từ tệp SLO (Sloth, Pyrra, hay
script như Basic 02) và test bằng `promtool test rules`. Traffic thấp cần điều kiện số request tối thiểu.

## Làm sao giữ on-call bền vững?

- Primary và secondary mỗi ca, người mới làm shadow trước, không ai trực nhiều tuần liền, follow-the-sun nếu có nhiều múi giờ.
- Page budget, ví dụ tối đa 2 sự cố mỗi ca 12 giờ; vượt thì team dừng feature để sửa alert và hệ thống.
- Mọi page phải hành động được; alert không cần làm gì thì xoá hay thành ticket. Alert theo burn rate thay cho ngưỡng CPU.
- Runbook cho mỗi alert, bàn giao ca có ghi chép, leo thang có thời hạn.
- Chế độ bù: phụ cấp, nghỉ bù sau đêm bị đánh thức. Đo số page, số page ban đêm, thời gian ack, và review hằng tuần.

Kiệt sức của người trực là rủi ro độ tin cậy: người mệt ra quyết định tệ.

## Bạn là incident commander của một sự cố SEV1. Bạn làm gì trong 15 phút đầu?

1. Nhận vai rõ ràng ("tôi là IC"), mở kênh sự cố, chỉ định ops lead (người duy nhất chạm hệ thống) và communications lead.
2. Xác nhận tác động bằng SLI: route nào, bao nhiêu khách, từ lúc nào.
3. Hỏi "cái gì vừa thay đổi?" (deploy, cấu hình, traffic, phụ thuộc). Ưu tiên giảm thiểu: rollback, tắt feature flag, chuyển traffic, scale.
4. Đặt nhịp cập nhật (trang trạng thái 30 phút một lần), giữ timeline cho postmortem.
5. Không tự gõ lệnh, không đi tìm người có lỗi; quyết định dựa trên số và bàn giao vai IC nếu sự cố kéo dài.

## Postmortem không đổ lỗi là gì? Có phải không ai chịu trách nhiệm?

Postmortem không đổ lỗi hỏi "hệ thống nào cho phép lỗi này xảy ra và lan tới khách", không hỏi "ai sai". Người làm hệ thống sẽ luôn mắc
lỗi; nếu bị phạt, họ giấu thông tin và tổ chức mất bài học. Không đổ lỗi không phải là giấu: vẫn ghi đủ lệnh đã chạy, quyết định, thời
điểm. Trách nhiệm nằm ở action item: cụ thể, có người, có hạn, sửa hệ thống (guardrail, review, tự động hoá, alert). "Nhắc kỹ sư cẩn thận
hơn" không phải action item. Một postmortem tốt có tóm tắt, tác động có số (khách, đơn, budget), timeline, nhiều yếu tố góp phần, điều làm
tốt và chưa tốt, action item.

## Toil là gì và bạn giảm toil thế nào?

Toil là việc tay, lặp lại, tự động hoá được, mang tính phản ứng, không tạo giá trị lâu dài và tăng theo quy mô dịch vụ: restart tay
worker mỗi tuần, tạo tài khoản bằng tay, xoá log cũ. Google SRE đặt trần khoảng 50% thời gian cho toil. Cách giảm: đo (gắn nhãn ticket, hỏi
team), chọn việc tốn nhiều giờ nhất, sửa nguyên nhân thay vì tự động hoá triệu chứng (worker hay đầy hàng đợi thì sửa backpressure trước
khi viết script restart), tự phục vụ (self-service) cho việc người khác hay nhờ. Viết postmortem hay thiết kế lại kiến trúc không phải toil.

## Chaos engineering khác "phá thử" thế nào? Bạn bắt đầu ra sao?

Chaos engineering là thí nghiệm có giả thuyết: viết ra trạng thái ổn định bằng SLI, đoán rằng nó vẫn đúng khi có lỗi X (container chết, mạng
chậm, đĩa đầy, phụ thuộc mất), chạy với blast radius nhỏ, có điều kiện dừng và hoàn tác tự động, rồi so kết quả với giả thuyết. Bắt đầu
ở lab hay staging với một service, chạy game day có người trực thật để kiểm cả alert, runbook và vai trò; viết postmortem cho mọi điểm mù
tìm thấy. Chỉ đưa vào production khi đã có SLO, alert đáng tin, rollback nhanh, và tăng dần (một phần traffic, giờ thấp điểm). Công cụ:
`tc netem`, Toxiproxy, Chaos Mesh, LitmusChaos, AWS Fault Injection Service.

## Dùng định luật Little để ước lượng capacity như thế nào?

L bằng lambda nhân W: số việc trong hệ thống bằng tốc độ đến nhân thời gian ở lại. API 400 request/giây, latency trung bình 50 ms thì
khoảng 20 request đang xử lý cùng lúc: cần khoảng 20 kết nối database (cộng headroom) chia cho các replica, và `max_connections` của database
phải đủ cho mọi replica lúc scale tối đa. Ngược lại, pool 10 kết nối với latency 50 ms chỉ phục vụ tối đa 200 request/giây; vượt thì hàng
đợi dài ra và latency tăng vọt. Trong load test, đo knee (bậc tải cao nhất còn đạt SLO) của một replica rồi tính số replica cho đỉnh dự
báo cộng headroom và N+1. Throughput cao nhất ở bậc đã vỡ SLO không phải công suất dùng được.

## Hoá đơn cloud tăng 40% tháng này. Bạn điều tra và giảm thế nào?

1. Phân bổ: chi phí theo dịch vụ, team, môi trường (tag, label); tăng ở đâu, từ ngày nào, có trùng deploy hay thay đổi traffic không.
2. So với unit economics: chi phí mỗi 1000 đơn có tăng không? Tăng vì kinh doanh tăng thì không phải vấn đề.
3. Thủ phạm hay gặp: môi trường preview không xoá, request Kubernetes quá rộng, log hay metric cardinality cao, truyền dữ liệu qua NAT hay
   giữa AZ, snapshot và volume mồ côi.
4. Giảm: xoá tài nguyên rỗi, rightsizing (CPU theo p95, RAM theo mức cao nhất cộng headroom) kèm autoscaler bớt node, cam kết (Savings
   Plans) cho phần nền, spot cho batch và CI, tắt dev ngoài giờ.
5. Phòng: budget alarm, bắt buộc nhãn team, Infracost trong pull request, review chi phí hằng tháng với team.

## Bảo mật pipeline CI/CD: bạn làm những gì đầu tiên?

- Quét secret trước khi push và quét lịch sử; key đã lọt thì thu hồi ngay.
- Credential ngắn hạn qua OIDC thay cho key dài hạn, role giới hạn theo repo và nhánh; `permissions` tối thiểu cho token của workflow.
- Ghim action và image bên thứ ba theo SHA hay digest; review cập nhật phụ thuộc.
- SBOM cho mỗi image, quét CVE, ký digest (cosign) và đính provenance (SLSA); cluster chỉ nhận image có chữ ký hợp lệ.
- Không chạy workflow có secret cho pull request từ fork; tách runner deploy khỏi runner build chung.

Giải thích theo mối đe doạ: key lộ, action bị chiếm, image bị thay, job bị chiếm quyền.

## Thiết kế hệ thống: Olist chuẩn bị cho đợt 11/11, traffic đặt hàng gấp 8 lần bình thường. Bạn chuẩn bị gì?

- **Yêu cầu và số**: đỉnh dự báo (ví dụ 800 đơn/phút), SLO checkout (99,9%, p95 dưới 300 ms), thời gian đỉnh.
- **Capacity**: load test bậc thang trên staging giống production, tìm knee mỗi replica, tính replica cho đỉnh cộng headroom 30% và N+1; kiểm
  giới hạn phụ thuộc (kết nối database theo định luật Little, quota của cổng thanh toán, rate limit).
- **Chỗ hỏng**: hàng đợi cho việc không cần đồng bộ (gửi email, tính lại doanh thu), timeout và circuit breaker cho cổng thanh toán,
  rate limit và trang chờ khi vượt công suất, feature flag tắt tính năng phụ.
- **Vận hành**: đóng băng thay đổi rủi ro trước đợt, game day mô phỏng phụ thuộc chậm, burn-rate alert, war room với vai trò rõ, runbook,
  scale trước (không chờ autoscaler) vì pod mới cần thời gian.
- **Chi phí**: scale lên trước đợt và xuống sau, ước tính chi phí, theo dõi chi phí mỗi đơn.

## Câu sự cố: khách báo trang tra đơn chậm, dashboard tỉ lệ lỗi vẫn xanh. Bạn làm gì?

1. Xác nhận bằng SLI latency: p95, p99 theo route, từ lúc nào, mọi khách hay một vùng. Lỗi vẫn xanh nghĩa là cần nhìn latency, không chỉ lỗi.
2. Hỏi cái gì thay đổi: deploy, cấu hình, traffic tăng, phụ thuộc.
3. Thu hẹp: route nào chậm, route nào không. Route chỉ dùng Postgres chậm còn route dùng Redis bình thường thì nghi Postgres hay đường của
   API tới nó.
4. Mở trace chậm (Jaeger): thời gian nằm trong span DB (query chậm, khoá), giữa các span (CPU, GC, mạng của API), hay chờ pool kết nối.
5. Kiểm USE của tài nguyên liên quan (CPU throttle, pool đầy, mạng), log lỗi timeout.
6. Giảm thiểu (rollback, scale, chuyển traffic), xác nhận p95 về ngưỡng bằng số, rồi postmortem và thêm alert latency theo burn rate nếu
   thiếu.

## Câu hành vi: kể về một lần bạn gây ra sự cố.

Dùng STAR và thành thật. Ví dụ khung: **Situation**: tôi đổi cấu hình pool kết nối của API trong đợt tối ưu. **Task**: tôi sở hữu thay
đổi đó và là người trực tuần ấy. **Action**: khi tỉ lệ lỗi tăng sau deploy, tôi rollback trong 6 phút, báo kênh sự cố, rồi dẫn
postmortem: canary 5 phút với traffic tối không đủ phát hiện; tôi thêm phân tích canary theo SLO và test tải cho mọi thay đổi pool.
**Result**: khoảng 600 đơn lỗi, tiêu 30% budget tháng; ba tháng sau không có sự cố cùng loại, quy trình canary được cả công ty dùng.
Người phỏng vấn tìm: bạn nhận phần của mình, không đổ lỗi, phản ứng có trật tự, và sửa hệ thống chứ không chỉ sửa lần đó.

## Bạn sẽ làm gì trong 90 ngày đầu với vai trò SRE ở một team chưa có SLO?

- **Tháng 1**: hiểu hệ thống và người dùng; đọc postmortem và lịch sử page; tham gia on-call như shadow; đo toil và page hiện tại.
- **Tháng 2**: cùng product chọn 2 tới 3 SLI cho hành trình quan trọng, đặt SLO từ dữ liệu lịch sử, dựng dashboard budget, thay vài alert
  ồn nhất bằng burn-rate alert; viết runbook cho alert còn lại.
- **Tháng 3**: thống nhất chính sách error budget, chạy game day đầu tiên ở staging, chọn một nguồn toil lớn nhất để tự động hoá, báo cáo
  kết quả bằng số (page giảm bao nhiêu, budget còn bao nhiêu).

Ý chính: đo trước, thay đổi nhỏ có số liệu, và làm cùng team chứ không áp đặt.
