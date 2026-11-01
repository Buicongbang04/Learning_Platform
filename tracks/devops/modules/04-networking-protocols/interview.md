# Câu hỏi phỏng vấn: Networking & protocols

## Gõ `https://shop.olist-shop.com.br` vào trình duyệt rồi Enter. Chuyện gì xảy ra, và mỗi bước hỏng thì trông thế nào?

1. **DNS**: trình duyệt và hệ điều hành xem cache, rồi hỏi recursive resolver; resolver đi từ root tới `.br` tới
   authoritative nếu chưa có trong cache. Hỏng: `NXDOMAIN` (tên sai, bản ghi chưa tạo, negative cache), `SERVFAIL` (DNSSEC
   sai, authoritative chết), hoặc trả IP cũ (TTL chưa hết).
2. **TCP** tới IP đó cổng 443 (hoặc QUIC trên UDP 443 nếu đã biết server có HTTP/3). Hỏng: `connection refused` (không
   ai nghe cổng), timeout (firewall, security group, route).
3. **TLS**: `ClientHello` có SNI và ALPN, server trả cert theo SNI, client kiểm chuỗi tới root, kiểm SAN, kiểm hạn, rồi
   hai bên có khoá phiên. Hỏng: cert thiếu intermediate, sai tên, hết hạn, không có phiên bản/cipher chung.
4. **HTTP**: request qua CDN, LB, reverse proxy tới app; mỗi chặng có thể trả lỗi riêng (403 của WAF, 502/504 của
   proxy, 500 của app) hoặc trả bản cache.
5. **Render**: HTML kéo theo CSS, JS, ảnh, lặp lại các bước trên với connection reuse và HTTP/2 multiplexing.

Ở mức senior, điểm cần nói thêm là **nhiều tầng cache** (trình duyệt, OS, resolver, CDN) và câu hỏi "ai bị, ai không":
sự cố chỉ một phần người dùng gặp gần như luôn nằm ở thứ khác nhau giữa hai nhóm.

## Ngày mai bạn chuyển `api.olist-shop.com.br` sang load balancer mới. Bản ghi A đang có TTL 86400. Kế hoạch DNS của bạn?

Hôm nay (ít nhất một TTL cũ trước giờ chuyển) hạ TTL xuống 60–300. Dựng LB mới chạy song song, kiểm bằng
`curl --resolve api.olist-shop.com.br:443:<IP mới>` để không phụ thuộc DNS. Giờ chuyển: đổi bản ghi, theo dõi lưu lượng ở
**cả hai** LB; LB cũ phải giảm về gần 0. Giữ LB cũ ít nhất thêm một TTL cũ, lâu hơn với client không tôn trọng TTL (JVM
cache, app mobile tự cache, IoT). Ổn định rồi nâng TTL lại 3600 để giảm tải và chịu được sự cố của nhà cung cấp DNS.

Nếu tên miền ở apex và LB cho tên chứ không cho IP (ALB, CDN), không dùng CNAME ở apex: dùng alias/ANAME/CNAME
flattening. Kiểm từ nhiều resolver (`dig @1.1.1.1`, `@8.8.8.8`, resolver của VPC) và hỏi thẳng authoritative
(`dig +norecurse @ns1...`) để phân biệt "bản ghi chưa đổi" với "cache chưa hết".

## NXDOMAIN và NODATA khác nhau thế nào? Negative caching gây sự cố ra sao?

`NXDOMAIN` là tên không tồn tại; NODATA là `NOERROR` không có câu trả lời, tức tên có nhưng không có loại bản ghi được hỏi
(có `A` mà không có `AAAA`). Cả hai mang SOA của zone trong phần AUTHORITY, và resolver cache câu trả lời phủ định trong
`min(TTL của SOA, MINIMUM của SOA)` (RFC 2308).

Sự cố điển hình: pipeline deploy chạy health check tới `api-v2.olist-shop.com.br` **trước** khi tạo bản ghi, resolver
nhớ NXDOMAIN; tạo bản ghi xong, dịch vụ vẫn "không tồn tại" với một phần người dùng tới hết negative TTL. Nếu MINIMUM để
86400 thì là một ngày. Phòng: tạo bản ghi trước khi ai đó hỏi, giữ MINIMUM 300–3600, và khi gỡ lỗi nhìn SOA trong
output `dig` để biết còn phải chờ bao lâu. Một bẫy khác: CNAME tới tên không tồn tại cho `NXDOMAIN` dù tên bạn hỏi có
tồn tại (dangling CNAME, cũng là rủi ro subdomain takeover).

## HTTP/1.1, HTTP/2, HTTP/3: bạn bật gì ở chặng nào?

HTTP/2 multiplex nhiều stream trên một kết nối TCP, nén header, nhưng vẫn bị head-of-line blocking ở TCP: một gói mất làm
mọi stream chờ. HTTP/3 chạy trên QUIC (UDP), mỗi stream độc lập, bắt tay 1 RTT (0-RTT khi nối lại), giữ phiên khi đổi
mạng, nên có lợi nhất với mobile và mạng mất gói.

Quyết định theo chặng: client → CDN/edge bật cả HTTP/2 và HTTP/3 (gần như miễn phí trên CDN, client tự rơi về TCP khi UDP
bị chặn). Edge/LB → backend thường để HTTP/1.1 keep-alive: đơn giản, dễ quan sát, ít lợi ích từ multiplexing trong mạng
nội bộ có độ trễ thấp. Ngoại lệ là gRPC, cần HTTP/2 cả đường, nên LB phải hỗ trợ HTTP/2 tới backend (ALB target group
gRPC, Envoy). Cái giá của HTTP/3: CPU cao hơn ở server, công cụ quan sát yếu hơn, firewall doanh nghiệp hay chặn.

## API trả 502, 503, 504 khác nhau thế nào? Bạn đọc gì đầu tiên?

Cả ba thường do **proxy** sinh ra (Nginx, ALB, Envoy), nghĩa là proxy còn sống và đang báo về upstream của nó. 502: upstream
trả thứ proxy không hiểu hoặc đóng kết nối (app crash, cổng sai, protocol sai như HTTP vào cổng gRPC, keep-alive bị
upstream đóng trước). 503: không có upstream khoẻ (health check fail hết, pool rỗng khi deploy) hoặc app tự báo quá tải.
504: upstream không trả lời trong timeout của proxy (query chậm, deadlock, timeout proxy ngắn hơn thời gian xử lý).

Đọc đầu tiên: log của proxy với `upstream_addr`, `upstream_status`, `upstream_response_time`, `request_time`, để biết
upstream nào và hỏng ở bước kết nối hay đọc. Rồi mới tới log app. Một cặp hay gặp: 499 trong log Nginx (client bỏ cuộc)
cùng 504 ở LB phía trước: chuỗi timeout không giảm dần từ ngoài vào trong.

## Sự cố: sau khi thay cert, trình duyệt vào bình thường nhưng app Android, đối tác dùng Java và worker Python báo lỗi TLS. Bạn xử lý thế nào?

Triệu chứng "trình duyệt được, client khác không" gần như luôn là **chuỗi thiếu intermediate**. Trình duyệt desktop và iOS
tự bù intermediate (tải theo AIA, cache), OpenSSL, Java, OkHttp thì không. Xác nhận trong một phút:
`openssl s_client -connect api...:443 -servername api... -showcerts` và đếm cert trong `Certificate chain`: chỉ có `0`
là thiếu; lỗi `unable to get local issuer certificate`.

Khắc phục: trỏ `ssl_certificate` về `fullchain.pem` (leaf + intermediate), reload, kiểm lại bằng `curl` và một client Java,
xác nhận lỗi giảm theo từng loại client. Sau đó postmortem: vì sao thay cert là việc tay, vì sao kiểm bằng trình duyệt,
vì sao synthetic chỉ xem ngày hết hạn. Việc cần làm: ACME tự động xuất fullchain, CI kiểm chuỗi bằng `openssl verify`,
synthetic check bằng client nghiêm ngặt. Đồng thời kiểm hai nghi phạm khác cho "một phần client lỗi": client không gửi
SNI nhận cert `default_server`, và client cũ không có root mới.

## TLS 1.2 và TLS 1.3 khác nhau ở đâu mà người vận hành cần quan tâm?

TLS 1.3 bắt tay 1 RTT (1.2 cần 2), có 0-RTT khi nối lại, chỉ dùng trao đổi khoá (EC)DHE nên luôn có forward secrecy,
bỏ hết cipher yếu (còn 5 suite AEAD), mã hoá cả cert trong bắt tay. Với vận hành: độ trễ thấp hơn cho người dùng xa,
cấu hình cipher gần như không còn gì để sai, nhưng 0-RTT có thể bị replay nên chỉ cho request idempotent (Nginx
`ssl_early_data` kèm kiểm header `Early-Data` ở app).

Vẫn bật TLS 1.2 vì client cũ (Java 8 bản cũ, thiết bị nhúng, một số thư viện trên Android cũ). Tắt 1.0 và 1.1. Một hệ quả
ít người nghĩ tới: vì cert được mã hoá trong TLS 1.3, middlebox kiểm tra TLS kiểu cũ không đọc được tên server qua cert
nữa, chỉ còn SNI (và ECH đang che nốt SNI).

## Vì sao chọn Let's Encrypt và ACME thay vì mua cert một năm? Khi nào không dùng được?

Cert miễn phí không phải lý do chính. Lý do là **tự động hoá**: cert 90 ngày buộc team gia hạn bằng máy, nên quy trình gia
hạn chạy hằng tháng và luôn được kiểm, thay vì một năm một lần do một người nhớ (và một ngày người đó nghỉ việc). Cert ngắn
còn giảm thiệt hại khi khoá lộ, vì thu hồi (CRL, OCSP) vốn không đáng tin. CA/Browser Forum đã thông qua lộ trình rút thời
hạn tối đa của cert công khai xuống 47 ngày vào 2029, nên tự động hoá là bắt buộc dù dùng CA nào.

Chọn challenge: HTTP-01 cho web server công khai; DNS-01 cho wildcard và máy nội bộ (cần API DNS, phải bảo vệ khoá API đó
và giới hạn quyền chỉ cho `_acme-challenge`). Không dùng được hoặc không hợp: cần cert OV/EV vì yêu cầu hợp đồng, tên nội
bộ không công khai (dùng CA riêng như step-ca, Vault PKI, AWS Private CA), thiết bị không chạy được client ACME (dùng LB
hoặc CDN kết thúc TLS thay). Ở Kubernetes, cert-manager; ở edge, CDN tự quản lý cert.

## Agent forwarding nguy hiểm thế nào? Bạn thiết kế truy cập SSH vào máy production ra sao?

`ssh -A` tạo một socket agent trên máy đích; bất kỳ ai có root ở đó dùng socket đó để xác thực bằng khoá của bạn tới mọi
máy khác trong lúc phiên còn mở. Bastion bị chiếm cộng agent forwarding là kẻ tấn công đi được tới mọi nơi bạn đi được.

Thiết kế: không ai SSH thẳng từ Internet. Ưu tiên công cụ không mở cổng 22 và có audit (SSM Session Manager, Teleport, IAP,
Tailscale SSH) với đăng nhập SSO. Nếu dùng bastion SSH: `ProxyJump` thay agent forwarding, bastion cấm agent forwarding và
chỉ cho port forwarding cần thiết, chỉ nhận kết nối từ VPN. Danh tính bằng **SSH certificate** sống vài giờ do CA cấp sau
khi đăng nhập SSO, server tin CA (`TrustedUserCAKeys`), principal tách quyền (deploy, dba). Host certificate để người dùng
không phải chấp nhận host key mù. Phía server: không root login, không mật khẩu, `MaxAuthTries` thấp, log phiên tập trung.

## Đối tác cần gửi file cho bạn mỗi ngày. FTP, FTPS hay SFTP? Vì sao?

Mặc định là **SFTP**: chạy trong SSH, một kết nối, một cổng, mã hoá, xác thực bằng khoá nên script cron không chứa mật
khẩu, giới hạn được tài khoản vào một thư mục (`ChrootDirectory`, `ForceCommand internal-sftp`). Muốn khỏi vận hành máy
chủ: AWS Transfer Family đưa thẳng vào S3, hoặc bỏ hẳn giao thức tệp bằng pre-signed URL S3 nếu đối tác gọi được HTTPS.

FTP thường gửi mật khẩu và dữ liệu dạng rõ, chỉ chấp nhận trong mạng kín với hệ thống cũ không đổi được. FTPS khi đối tác
(ngân hàng, EDI) bắt buộc: mã hoá được nhưng giữ cấu trúc hai kênh của FTP; kênh dữ liệu dùng cổng động mà firewall/NAT
không đọc được vì lệnh đã mã hoá, nên phải cố định dải passive và mở đúng dải đó. Triệu chứng kinh điển: đăng nhập được
nhưng `LIST` treo.

## Thư đặt lại mật khẩu của Olist Shop bắt đầu vào spam ở Gmail. Bạn điều tra thế nào?

Lấy một thư thật trong Gmail, "Show original": đọc `Authentication-Results` để thấy SPF, DKIM, DMARC pass hay fail và
**aligned** với tên miền nào. Các nguyên nhân hay gặp, theo thứ tự kiểm:

1. DMARC fail: DKIM ký bằng tên miền của ESP chứ không phải `olist-shop.com.br`, và SPF aligned gãy (đổi ESP, đổi
   Return-Path); hoặc selector DKIM bị gỡ khỏi DNS khi xoay khoá.
2. Reputation: Google Postmaster Tools xem domain và IP reputation, spam rate (giữ dưới 0,1%, không chạm 0,3%). Nếu thư
   marketing gửi cùng tên miền và cùng IP với thư giao dịch, một chiến dịch bị báo spam kéo cả thư đặt lại mật khẩu xuống.
3. Hạ tầng: PTR không khớp HELO, IP mới chưa warm-up, IP vào blacklist (kiểm Spamhaus), thiếu TLS.
4. Nội dung và hành vi: link rút gọn, HTML hỏng, thiếu `List-Unsubscribe` cho thư hàng loạt.

Sửa lâu dài: DKIM aligned cho mọi nguồn, tách thư giao dịch và marketing (tên miền con, IP hoặc ESP riêng), báo cáo DMARC
`rua` vào dashboard có cảnh báo, Postmaster Tools theo dõi hằng tuần.

## SPF pass, DKIM pass, nhưng DMARC fail. Có thể không? Giải thích.

Có, vì DMARC đòi pass **và aligned** với tên miền trong `From`. SPF kiểm tên miền của envelope sender (`Return-Path`), DKIM
kiểm tên miền `d=` trong chữ ký; cả hai có thể là tên miền của người khác. Ví dụ: thư `From: suporte@olist-shop.com.br`
gửi qua ESP với `Return-Path: bounce@esp-mail.example` và chữ ký `d=esp-mail.example`: SPF pass cho `esp-mail.example`,
DKIM pass cho `esp-mail.example`, không cái nào aligned với `olist-shop.com.br`, DMARC fail.

Trường hợp tinh tế hơn: strict alignment (`adkim=s`, `aspf=s`) với `From: pay.olist-shop.com.br` trong khi chữ ký mang
`d=olist-shop.com.br`: relaxed thì aligned, strict thì không. Và chiều ngược lại: tên miền na ná `olist-shop-br.com` có
đủ SPF, DKIM, DMARC cho chính nó nên **pass**: DMARC không chống lookalike. Organizational domain tính theo Public Suffix
List, không phải "hai nhãn cuối", nếu không mọi tên miền dưới `.com.br` sẽ được coi là cùng tổ chức.

## Thiết kế: cấu hình email cho tên miền mới có Google Workspace, SES cho thư giao dịch, một ESP marketing và Zendesk.

Bắt đầu bằng kiểm kê: với mỗi nguồn, `From`, `Return-Path`, `d=` của DKIM. Mục tiêu: **mọi nguồn ký DKIM aligned** (chân
sống sót qua forward), SPF aligned là lớp thứ hai.

- Apex: MX của Google; SPF chỉ gồm Google và Zendesk (đếm cả lượt lồng, dưới 10), `-all` khi đã chắc, `~all` trong lúc
  kiểm kê.
- SES: custom MAIL FROM `mail.<domain>` (MX + SPF riêng), Easy DKIM 3 CNAME. ESP: tên miền con `news.<domain>` để tách
  reputation, domain authentication (CNAME DKIM, Return-Path `em.news.`). Zendesk: CNAME DKIM.
- DMARC: `p=none; rua=...` 4 tuần, đọc báo cáo tới khi 99% thư hợp lệ pass và không còn nguồn lạ hợp lệ; rồi
  `p=quarantine` với `pct` tăng dần; cuối cùng `p=reject`. TTL `_dmarc` thấp để lùi được nhanh. `sp=` hoặc bản ghi riêng
  cho `news.`.
- Thêm: MTA-STS (`testing` rồi `enforce`) và TLS-RPT; `List-Unsubscribe` một chạm cho marketing; xoay khoá DKIM bằng
  selector mới, giữ selector cũ một thời gian; CAA cho cert của `mta-sts.`.
- Giám sát: parsedmarc hoặc dịch vụ phân tích DMARC, Postmaster Tools, webhook bounce/complaint. Mọi bản ghi quản lý bằng
  IaC để có review.

## Greylisting là gì? Nó ảnh hưởng thế nào tới hệ thống gửi OTP?

Máy nhận gặp bộ ba (IP gửi, người gửi, người nhận) lần đầu thì trả `451 4.7.1` tạm thời; MTA thật thử lại sau vài phút và
được nhận, bot spam bắn-rồi-quên thì không. Rẻ và hiệu quả cho người nhận, nhưng thư đầu tiên trễ từ vài phút tới vài chục
phút, đúng loại thư không được trễ (OTP, đặt lại mật khẩu).

Bên gửi giảm ảnh hưởng bằng: gửi qua ESP có reputation tốt và dải IP ổn định (nhiều máy nhận whitelist sẵn), không xoay
IP liên tục (mỗi IP mới là một bộ ba mới), retry đúng lịch cho mã 4xx, và với đối tác B2B quan trọng thì đề nghị whitelist.
Bên vận hành phải đọc đúng log: `451` là chờ rồi thử lại, không phải bị chặn; `550` mới là bounce. Cung cấp kênh OTP thứ hai
(SMS, app) cho trường hợp email trễ.

## Vì sao dùng Mailpit trong dev và CI thay vì gửi thật tới một hộp Gmail test?

Mailpit là SMTP giả: mọi thư ứng dụng gửi đi đều vào một hộp của nó, không thư nào lọt ra Internet. Với CI: không cần
tài khoản, không có rate limit, không làm hỏng reputation của tên miền thật, chạy offline, và có API (`/api/v1/search`,
`/api/v1/message/{ID}`, headers, parts) nên test tự động kiểm được từng header, phần HTML, tệp đính kèm, `Return-Path`, Bcc
qua envelope. Gửi tới Gmail test thì chậm, không ổn định (bộ lọc spam thay đổi), và rủi ro gửi nhầm tới khách thật khi
cấu hình sai.

So với lựa chọn khác: MailHog cùng ý tưởng nhưng không còn được phát triển; smtp4dev mạnh trên .NET; GreenMail nhúng được
vào test JVM. Mailpit được chọn vì đang được bảo trì, một binary nhỏ, có giao diện, API, kiểm HTML và link. Giới hạn: không
nói gì về khả năng tới hộp thư thật (SPF, DKIM, reputation); phần đó cần kiểm trên staging với ESP thật và công cụ như
Postmaster Tools.

## Một service trên Kubernetes gọi API bên ngoài chậm bất thường, CoreDNS tốn CPU. Bạn nghi gì?

`ndots:5` trong `/etc/resolv.conf` của pod: tên có ít hơn 5 dấu chấm (`api.partner.com.br` có 3) bị thử lần lượt với từng
search domain (`<ns>.svc.cluster.local`, `svc.cluster.local`, `cluster.local`) trước khi thử tên tuyệt đối, mỗi lần cho
cả A và AAAA. Một lần gọi thành 8 truy vấn, 6 trong số đó NXDOMAIN; cộng với không có connection pool thì CoreDNS và
conntrack bị dồn. Có thể thêm race condition của conntrack với truy vấn A/AAAA song song qua UDP (timeout 5 giây ngẫu nhiên).

Sửa: viết FQDN có dấu chấm cuối trong cấu hình, hoặc `dnsConfig.options: ndots: 2` cho pod gọi ra ngoài nhiều; bật
NodeLocal DNSCache; dùng connection pool và keep-alive để không phải resolve và bắt tay mỗi request; xem metrics của
CoreDNS (`coredns_dns_requests_total` theo rcode) để thấy tỉ lệ NXDOMAIN bất thường.
