# Câu hỏi phỏng vấn: Giới thiệu DevOps & SRE

## DevOps là gì? Trả lời trong hai phút cho một người không làm kỹ thuật.

DevOps là cách làm việc để đưa thay đổi phần mềm tới người dùng **nhanh và an toàn cùng lúc**. Trước đây người viết code
(Dev) và người vận hành (Ops) có mục tiêu ngược nhau: Dev muốn thay đổi nhiều, Ops muốn thay đổi ít. Kết quả là release
lớn, hiếm, và mỗi lần release là một lần căng thẳng. DevOps cho hai bên chung một mục tiêu (dịch vụ chạy tốt cho người
dùng), chung trách nhiệm (ai viết thì cũng chịu khi nó hỏng), và dùng tự động hoá để mỗi thay đổi đủ nhỏ, đủ thường
xuyên, nên dễ kiểm tra và dễ quay lại.

Ứng viên senior nói thêm hai ý: DevOps không phải một chức danh hay một bộ công cụ, và nó đo được bằng DORA metrics
(lead time, deployment frequency, change failure rate, recovery time). Nghiên cứu của DORA cho thấy tốc độ và độ ổn định
không đánh đổi nhau: team giỏi nhất vừa deploy nhiều nhất vừa ít hỏng nhất.

## Giải thích CALMS. Trụ cột nào quan trọng nhất và vì sao?

| Trụ cột | Ý chính | Dấu hiệu thiếu |
| --- | --- | --- |
| Culture | Chung trách nhiệm, học từ lỗi | Postmortem đổ lỗi, dev không xem log production |
| Automation | Build, test, deploy, hạ tầng, rollback tự động | Rollback tay theo runbook |
| Lean | Batch nhỏ, giảm hàng đợi, giới hạn WIP | Release train gom hàng chục thay đổi |
| Measurement | Đo luồng và độ ổn định | Không có SLO, đo số ticket thay vì kết quả |
| Sharing | Chia sẻ kiến thức và công cụ | Bus factor 1, mỗi team tự viết lại pipeline |

Culture quan trọng nhất vì nó quyết định automation có được dùng đúng không: tự động hoá trong một tổ chức vẫn ném việc
qua tường chỉ làm việc ném nhanh hơn. Nhưng trong thực tế không "sửa văn hoá" trực tiếp được; văn hoá đổi khi cấu trúc
và động lực đổi. Ví dụ: cho dev trực on-call service của mình, postmortem blameless, đo bằng DORA thay vì số ticket. Câu
trả lời tốt nối mỗi trụ cột với một thay đổi cụ thể, không dừng ở định nghĩa.

## Định nghĩa bốn DORA key metrics. Bạn đo chúng thế nào trong một công ty có GitLab, Jenkins và PagerDuty?

- **Change lead time**: từ lúc commit tới lúc chạy trên production. Lấy thời điểm commit từ GitLab, thời điểm deploy từ
  Jenkins; pipeline phải ghi danh sách SHA của mỗi lần deploy.
- **Deployment frequency**: số deploy production mỗi ngày/tuần, từ log Jenkins, chỉ đếm production, không đếm rollback.
- **Change failure rate**: tỉ lệ deploy production cần can thiệp ngay (rollback, hotfix, fix forward). Cần khoá nối:
  incident trên PagerDuty ghi deploy gây ra nó, hoặc deploy ghi `rollback_of`.
- **Failed deployment recovery time**: từ lúc deploy hỏng tới lúc khôi phục (rollback xong hoặc incident đóng).

Các quyết định phải nói rõ: dùng median (không dùng mean) cho thời gian; lead time kết thúc ở deploy không bị rollback;
mỗi deploy hỏng đếm một lần dù sinh nhiều alert; thời điểm luôn có múi giờ; tuần không deploy có change failure rate
"không xác định", không phải 0. Thêm reliability (đo bằng SLO) như DORA khuyên từ 2021, và rework rate (2024) nếu đánh
dấu được hotfix. Việc đầu tiên thường không phải mua dashboard DORA mà là sửa quy trình để dữ liệu có khoá nối.

## Change failure rate của cụm "high" trong báo cáo DORA 2024 là 20%, cao hơn cụm "medium" (10%). Giải thích.

Các mức của DORA là kết quả **phân cụm** câu trả lời khảo sát, không phải ngưỡng thiết kế. Cụm high deploy thường xuyên
hơn và lead time ngắn hơn medium, nhưng đổi lại có tỉ lệ hỏng cao hơn; cụm elite thì tốt cả hai. Hệ quả thực tế:

- Không xếp mức một metric đứng riêng bằng ngưỡng cứng; chọn cụm có giá trị gần nhất và ghi rõ cách làm.
- Luôn ghi năm báo cáo: 2022 không có elite, 2023 có bộ giá trị khác, 2025 bỏ bốn mức để dùng team archetype.
- Dùng bảng làm mốc tham chiếu, không làm mục tiêu. Mục tiêu đúng là xu hướng của chính team qua từng quý.

## CTO muốn đặt KPI "mọi team deploy ít nhất một lần mỗi ngày" và thưởng theo đó. Bạn tư vấn thế nào?

Tôi đồng ý mục tiêu (batch nhỏ, deploy thường xuyên) nhưng không đồng ý biến metric thành KPI thưởng phạt. Định luật
Goodhart: team sẽ chia nhỏ thay đổi giả, deploy khi không có gì mới, hoặc tránh nhận service rủi ro. Tệ hơn, nếu change
failure rate đang cao, ép deploy nhiều hơn là ép nhiều sự cố hơn.

Đề xuất thay thế:

1. Dùng DORA để mỗi team so với chính nó, nhìn throughput và instability cùng nhau.
2. Đặt mục tiêu theo năng lực, không theo con số: "rollback một lệnh dưới 5 phút", "test tự động đủ để bỏ regression
   tay".
3. Gỡ rào cản thay vì đặt chỉ tiêu: nút thắt thường là review chờ, CAB, release train; deployment frequency tăng là
   hệ quả.

## DevOps, SRE và Platform Engineering khác nhau thế nào?

- **DevOps** là triết lý và tập thực hành: phá bức tường dev và ops, chung trách nhiệm, tự động hoá, đo lường.
- **SRE** là một cách hiện thực DevOps cụ thể của Google: dùng kỹ sư phần mềm làm vận hành, quản reliability bằng SLO
  và error budget, giới hạn toil dưới 50%, postmortem blameless. "class SRE implements interface DevOps".
- **Platform Engineering** đưa DevOps lên quy mô nhiều team: một team xây sản phẩm nội bộ (golden path, self-service)
  để team sản phẩm tự deploy, tự tạo hạ tầng mà không cần ticket.

Chúng không loại trừ nhau. Một công ty 60 kỹ sư hợp lý có thể có team sản phẩm tự vận hành (DevOps), một platform team
nhỏ, và vài SRE làm việc cùng các service đắt nhất. Sai lầm hay gặp là dùng ba tên này như ba chức danh có cùng một việc
là "nhận ticket deploy".

## Error budget là gì? Khi error budget hết giữa tháng, chuyện gì xảy ra?

Error budget là phần được phép không đạt SLO trong cửa sổ đo:

$$
\text{error budget} = (1 - \text{SLO}) \times \text{cửa sổ}
$$

SLO 99,9% trên 30 ngày cho khoảng 43 phút. Khi budget hết, **error budget policy** đã ký trước giữa engineering và
product quyết định: thường là dừng release tính năng (trừ bản sửa lỗi và bảo mật), dồn sức vào nguyên nhân gốc của các
sự cố đã tiêu budget, và chỉ mở lại khi budget hồi.

Điểm senior: policy phải có **trước** sự cố, có chữ ký của lãnh đạo product, nếu không nó sẽ bị bỏ qua đúng lúc cần
nhất. Không hạ SLO giữa chừng để "đạt"; SLO chỉ xem lại theo chu kỳ dựa trên mức người dùng thật sự cần. Ngược lại,
budget luôn còn dư nhiều là dấu hiệu SLO quá lỏng hoặc team đang quá thận trọng, có thể deploy nhanh hơn.

## Tình huống: 21h tối thứ Sáu, sau một deploy, tỉ lệ lỗi 5xx của API thanh toán tăng từ 0,1% lên 8%. Bạn đang trực. Bạn làm gì?

Thứ tự ưu tiên: **giảm tác động trước, tìm nguyên nhân sau**.

1. **Xác nhận và tuyên bố incident** (1–2 phút): kiểm dashboard xem lỗi có thật, phạm vi bao nhiêu; mở kênh incident,
   nhận vai incident commander hoặc gọi thêm người theo quy trình. Ghi timeline ngay từ đầu.
2. **Giảm tác động** (5–10 phút): thay đổi gần nhất là nghi phạm số một. Nếu deploy mới trùng thời điểm lỗi tăng,
   **rollback ngay**, không debug trên production lúc người dùng đang mất tiền. Nếu có feature flag cho tính năng mới,
   tắt flag còn nhanh hơn rollback.
3. **Xác minh khôi phục**: tỉ lệ 5xx về mức nền, không chỉ "pod đã chạy lại". Theo dõi thêm 15–30 phút.
4. **Truyền thông**: cập nhật trạng thái cho support, product, và trang status nếu ảnh hưởng khách hàng, theo nhịp cố
   định (ví dụ 30 phút một lần) kể cả khi chưa có gì mới.
5. **Sau sự cố**: postmortem blameless trong vài ngày. Câu hỏi không phải "ai deploy" mà "vì sao canary hoặc test không
   bắt được", "vì sao deploy tối thứ Sáu", "rollback mất bao lâu và có thể nhanh hơn không". Action item có người nhận.

Nếu rollback không hết lỗi: thay đổi không phải nguyên nhân (hoặc có migration không đảo ngược được). Khi đó xem phụ
thuộc (DB, nhà cung cấp thanh toán), metric hạ tầng, và cân nhắc giảm tải (tắt tính năng không thiết yếu) trong lúc
điều tra. Trong DORA, deploy này là một failed change; thời gian khôi phục tính từ lúc deploy xong, không từ lúc alert.

## Vì sao track này chọn GitHub Actions để dạy CI/CD mà không chọn Jenkins, dù Jenkins phổ biến ở doanh nghiệp?

Lý do chọn để học (và cũng là lý do hay gặp khi chọn ở công ty nhỏ, vừa):

- **Không phải vận hành server CI**: runner do GitHub quản lý; Jenkins cần người vá core và plugin, sao lưu cấu hình,
  quản agent. Với team nhỏ, chi phí vận hành đó lớn hơn license.
- **Pipeline as code mặc định**, nằm cạnh code, review qua PR; Jenkins làm được với Jenkinsfile nhưng nhiều hệ thống cũ
  còn cấu hình qua UI.
- **Chạy được local bằng `act`**, nên bài tập không phụ thuộc mạng hay tài khoản.
- Khái niệm chuyển được: job, step, artifact, cache, secret, environment, matrix có ở mọi hệ CI.

Khi nào Jenkins thắng: phải chạy on-prem không ra Internet, pipeline rất đặc thù cần plugin riêng, đã có đầu tư lớn
và đội ngũ vận hành nó. GitLab CI thắng khi code đã ở GitLab tự host. Câu trả lời tốt luôn nối lựa chọn với ràng buộc,
không nói "X tốt hơn Y" chung chung.

## Toil là gì? Cho một ví dụ toil ở Olist Shop và cách loại bỏ nó.

Theo Google SRE, toil là việc vận hành thủ công, lặp lại, tự động hoá được, mang tính phản ứng, không để lại giá trị lâu
dài, và tăng tuyến tính theo quy mô dịch vụ. Toil không phải "việc chán": viết postmortem hay họp kiến trúc không phải
toil.

Ví dụ ở Olist Shop: mỗi sáng người trực phải xem hàng đợi `olist:jobs` và restart worker khi nó kẹt. Cách xử lý theo
thứ tự:

1. Đo: bao nhiêu lần mỗi tuần, mất bao lâu, do đâu.
2. Tự động hoá phát hiện: alert khi độ dài hàng đợi tăng mà `jobs_processed_total` không tăng.
3. Tự phục hồi: liveness probe hoặc restart policy dựa trên tín hiệu đúng.
4. Sửa gốc: vì sao worker kẹt (timeout kết nối DB, job lỗi không được đưa ra hàng đợi lỗi). Bước này mới loại toil
   hẳn; tự động hoá restart chỉ che triệu chứng.

Google giới hạn toil dưới 50% thời gian của SRE, vì nếu không, team chỉ còn làm việc tay và không bao giờ có thời gian
làm việc giảm toil.

## Thiết kế: công ty có 60 kỹ sư, 8 team sản phẩm và một "DevOps team" 4 người nhận mọi ticket deploy. Bạn tổ chức lại thế nào?

Chẩn đoán trước: vấn đề không phải thiếu người vận hành mà là **một hàng đợi duy nhất** cho 8 team, và rủi ro con người
(4 người trực cho toàn hệ thống). Thêm người vào hàng đợi không xoá được hàng đợi.

Đề xuất (theo Team Topologies):

| Team | Loại | Việc |
| --- | --- | --- |
| 8 team sản phẩm | stream-aligned | Sở hữu service từ code tới production, tự deploy, tự trực service của mình |
| Platform (4–6 người, phần lớn từ DevOps team cũ) | platform | Golden path: pipeline mẫu, base image đã vá, module IaC, cluster, observability stack. Đo bằng adoption, không bằng ticket |
| SRE (2–3 người) | enabling | Làm cùng checkout và payment (phần lớn doanh thu): SLO, error budget policy, game day, capacity |

Chuyển đổi từng bước: thí điểm golden path với một team, chuyển on-call của team đó (giờ hành chính trước, có runbook và
alert đã dọn, team cũ làm tầng hai), đo lại, rồi nhân rộng. Điều kiện chuyển bước phải đo được (team tự deploy 4 tuần
không cần ticket, page ngoài giờ ổn định). Rủi ro chính: team sản phẩm quá tải on-call, và platform team biến thành hàng
đợi mới; theo dõi bằng số page mỗi người mỗi tuần và thời gian chờ việc của platform.

## Một team muốn chuyển lên Kubernetes "để deploy nhanh hơn". Lead time của họ là 19 ngày, regression test làm tay mất 3 ngày. Bạn phản hồi thế nào?

Tôi hỏi lead time 19 ngày nằm ở đâu trước. Với regression tay 3 ngày, release train hai tuần và CAB hằng tuần, thời gian
gần như toàn bộ là **chờ**, không phải thời gian deploy. Kubernetes rút một lần deploy từ 20 phút xuống 5 phút, tức là
gần như không đổi lead time, nhưng thêm một hệ thống phức tạp mà team chưa biết vận hành.

Cách làm có số liệu: vẽ value stream (commit, PR, review, merge, deploy), tìm stage có median lớn nhất, tác động vào đó
(test tự động cho luồng chính, rollback tự động, CAB chỉ cho thay đổi rủi ro cao). Kubernetes là lựa chọn đúng khi có
lý do của nó: nhiều team, nhiều service, cần autoscale, cần chuẩn hoá cách chạy. Nói "chưa" kèm điều kiện để nói "có"
thuyết phục hơn nói "không".

## Bạn vào một công ty mới làm DevOps/SRE. 30 ngày đầu bạn làm gì?

- **Tuần 1–2: nghe và đo**. Gặp từng team sản phẩm, ops, product. Lấy DORA metrics thô từ Git, pipeline, incident; đọc
  postmortem 6 tháng gần nhất; đi một thay đổi từ commit tới production cùng một dev. Ghi danh sách rủi ro "sắp nổ"
  (backup chưa từng thử khôi phục, chứng chỉ sắp hết hạn, script chỉ một người hiểu).
- **Tuần 3: sửa rủi ro khẩn, rẻ**. Thử khôi phục backup một lần, đưa script bus factor 1 vào Git và pipeline, alert cho
  chứng chỉ.
- **Tuần 4: đề xuất**. Đánh giá theo CALMS có bằng chứng, 3 việc cho 90 ngày, mỗi việc gắn một metric và cách đo, kèm
  danh sách việc **không** làm (thường là "chuyển công cụ lớn").

Điều tránh: đề xuất viết lại toàn bộ hạ tầng trong tuần đầu khi chưa hiểu vì sao nó như hiện nay.

## Reliability nên đo bằng gì? Vì sao ping `/healthz` mỗi phút không đủ?

Reliability nên đo theo trải nghiệm người dùng: SLI dạng tỉ lệ request tốt trên tổng request (không `5xx` và đủ nhanh),
cho từng luồng quan trọng (xem đơn, thanh toán), lấy từ metric ứng dụng hoặc log của load balancer.

Ping `/healthz` không đủ vì:

- `/healthz` của Olist Shop cố ý không chạm DB (là liveness), nên DB sập mà ping vẫn xanh.
- Lỗi một phần (3% request thanh toán thất bại trong 2 giờ) không làm ping đỏ, nhưng người dùng chịu thật.
- Ping mỗi phút bỏ sót sự cố ngắn và không thấy độ trễ.

Ping từ bên ngoài vẫn có ích để bắt lỗi DNS, TLS, mạng mà metric nội bộ không thấy. Hệ thống trưởng thành dùng cả hai:
synthetic check bên ngoài và SLI theo request bên trong. Khi tính availability từ incident, nhớ gộp các alert chồng nhau
(một lần DB sập sinh alert từ mọi service) và cắt theo cửa sổ báo cáo.
