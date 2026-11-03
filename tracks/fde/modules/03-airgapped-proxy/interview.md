# Câu hỏi phỏng vấn: air-gapped, proxy và chứng chỉ công ty

## 1. "Air-gapped" nghĩa là gì với bạn khi lên kế hoạch triển khai? Các kiểu bạn từng gặp khác nhau thế nào?

Có ít nhất ba kiểu, và mỗi kiểu một chiến lược. Air-gapped hoàn toàn: chỉ tệp đi vào qua kênh duyệt (USB, MFT, data
diode), bundle phải tự chứa mọi thứ kể cả công cụ. Air-gapped có hạ tầng nội bộ: vẫn chỉ tệp đi vào, nhưng trong vùng có
registry, mirror, DNS, nên đưa vào một lần rồi phân phối nội bộ. Ra ngoài qua proxy công ty: có HTTP(S) tới tên miền được
phép, thường bị soi TLS, nên phải cấu hình proxy và CA ở mọi tầng. Tôi hỏi rõ kiểu nào ngay buổi khảo sát, vì nó quyết định
cả định dạng bundle lẫn lịch (thời gian quét virus của MFT có thể tới 24 giờ).

## 2. Khách nói "máy đã cấu hình proxy rồi" nhưng `docker pull` vẫn timeout. Bạn làm gì?

Hỏi "cấu hình ở đâu". Thường là `/etc/environment` hoặc `~/.bashrc`, tức là chỉ shell đăng nhập thấy. `docker pull` do
daemon kéo, và daemon là service systemd: không đọc `/etc/environment`, chỉ đọc `Environment=` của unit. Tôi kiểm
`systemctl show docker -p Environment`, thêm drop-in `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` (hoặc khoá `proxies` trong
`daemon.json` từ Docker 23), `daemon-reload`, restart (xin cửa sổ nếu không có `live-restore`). Nếu sau đó đổi sang lỗi chứng
chỉ thì proxy soi TLS và daemon chưa tin CA của khách: thêm CA vào trust store hệ thống rồi restart lần nữa, vì Go nạp trust
store lúc khởi động.

## 3. Vì sao `sudo apt-get update` không đi qua proxy dù `echo $https_proxy` trong shell có giá trị?

`sudo` mặc định `env_reset`, bỏ gần hết biến môi trường của người gọi. Cách đúng là cấu hình riêng của apt
(`Acquire::http::Proxy`, `Acquire::https::Proxy` trong `/etc/apt/apt.conf.d/`), không phải `sudo -E` (mang theo mọi biến khác,
kể cả thứ không nên) hay sửa `sudoers` cho cả hệ thống. Kho Ubuntu là HTTP nên vẫn phải qua proxy; nhiều người tưởng chỉ
HTTPS mới cần.

## 4. `no_proxy` có những bẫy gì?

Không có chuẩn chung. curl chỉ đọc `http_proxy` chữ thường, không hiểu CIDR trước bản 7.86; Python `urllib` so hậu tố tên,
không hiểu CIDR; `requests` và Go hiểu CIDR; Java bỏ qua biến môi trường, dùng `http.nonProxyHosts` với cú pháp khác. Tôi
đặt cả hai dạng chữ cùng giá trị, liệt kê `localhost`, `127.0.0.1`, `::1`, IP cụ thể của dịch vụ nội bộ, tên miền nội bộ có
dấu chấm đầu; thêm CIDR bên cạnh IP chứ không thay. Rồi kiểm bằng đúng công cụ, đúng phiên bản có trên máy khách. Triệu
chứng sai `no_proxy` hay gặp nhất: gọi dịch vụ nội bộ bị treo tới timeout, vì request đi vòng ra proxy.

## 5. Proxy soi TLS hoạt động thế nào, và vì sao nó làm hỏng các chương trình?

Proxy kết thúc TLS từ máy khách bằng một chứng chỉ do CA của công ty ký cho đúng tên máy chủ đích, mở gói ra quét, rồi mở
TLS mới tới máy chủ thật. Chương trình nào không tin CA của công ty sẽ thấy chứng chỉ "do một CA lạ ký" và từ chối:
`CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`. Nó không hỏng ngẫu nhiên: nó hỏng ở đúng những chương
trình đọc một trust store chưa có CA đó. Chẩn đoán bằng `openssl s_client -connect pypi.org:443 -proxy host:port -showcerts`
để xem issuer thật, rồi hỏi "chương trình đang lỗi đọc trust store nào".

## 6. Kể các trust store khác nhau trên một máy Ubuntu chạy Docker và Python.

Trust store hệ thống `/etc/ssl/certs/ca-certificates.crt` (curl, `ssl` của Python, apt, Go như dockerd). `certifi` của
`requests`/`httpx` cài bằng pip: bundle riêng, không đọc hệ thống. pip từ 24.2 trên Python 3.10+ dùng hệ thống qua
`truststore`. Docker kéo registry: hệ thống cộng `/etc/docker/certs.d/<host:port>/`. Mỗi image container có trust store riêng,
không liên quan gì tới máy chủ. Node có bundle riêng (`NODE_EXTRA_CA_CERTS`), Java có keystore `cacerts`. "Đã trust CA trên
máy" chỉ giải quyết dòng đầu tiên.

## 7. Một đồng nghiệp đề nghị thêm `verify=False` để demo kịp chiều nay. Bạn trả lời sao?

Không. `verify=False` (hay `curl -k`, `pip --trusted-host`, `insecure-registries` cho registry công cộng) tắt chính thứ phân
biệt proxy của khách với một kẻ đứng giữa bất kỳ, và dòng đó sẽ sống lâu hơn buổi demo: nó đi vào repo, vào image, sang
khách sau. Thay vào đó: lấy CA của khách (đọc fingerprint với An ninh), trỏ đúng biến (`REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`)
vào bundle hệ thống đã có CA, mất mười phút. Nếu công cụ thật sự không cấu hình được CA (ghim chứng chỉ) thì xin An ninh
bypass đúng tên miền đó bằng văn bản; quyết định đó là của họ.

## 8. Khách nói: "Máy đã tin chứng chỉ của chúng tôi rồi, sao app của các anh vẫn lỗi chứng chỉ?" Bạn làm gì?

Tin lời họ về máy, và đi tìm **tiến trình đang lỗi chạy ở đâu, khởi động khi nào, đọc trust store nào**: "máy" chỉ là một
trong nhiều nơi một chương trình lấy danh sách CA. Tôi tái hiện trên chính máy đó, chạy cùng một yêu cầu HTTPS bằng công cụ
của máy và bằng đúng tiến trình đang lỗi, so kết quả, rồi lần theo khác biệt. Sửa ở đúng tầng đó, không thay cả bundle bằng một tệp
chỉ có CA của khách (sẽ hỏng ở khách khác), và để lại một kiểm tra tự động (chạy tới một endpoint chứng chỉ tự ký phải bị
từ chối) để chắc chắn không ai "sửa" bằng cách tắt kiểm.

## 9. Registry nội bộ của khách chạy HTTP. Bạn chọn `insecure-registries` hay đề nghị TLS?

Tuỳ môi trường và ai chịu rủi ro. `insecure-registries` không cần khách làm gì nhưng image đi không mã hoá, không xác thực
máy chủ, mỗi máy phải sửa `daemon.json` và restart Docker. TLS với CA nội bộ cần IT cấp chứng chỉ, nhưng mỗi máy chỉ cần
chép `ca.crt` vào `/etc/docker/certs.d/<host:port>/`, không restart. Staging cô lập: tôi chấp nhận `insecure-registries` cho
đúng một địa chỉ, ghi rủi ro vào biên bản. Production: đề nghị TLS trước go-live. Không bao giờ khai cả dải địa chỉ.

## 10. Bạn chuyển bundle 1 GB qua USB/MFT vào vùng air-gapped. Kiểm toàn vẹn thế nào, ở đâu?

Hai lớp. Lớp một: `SHA256SUMS` cho mọi tệp trên USB, kiểm bằng `sha256sum -c` **trước** khi giải nén hay nạp gì, bắt chép
hỏng, máy quét cắt tệp. Lớp hai: manifest bên trong bundle, kiểm sau khi giải nén, bắt bundle khác bản phát hành; công cụ
kiểm phải chạy được với Python/công cụ của máy khách. Neo tin cậy: sha256 của chính `SHA256SUMS` gửi qua kênh khác (đọc
qua điện thoại) hoặc chữ ký cosign. Bí mật không đi trên USB, sinh tại chỗ. Và lịch: gửi trước ngày cài đủ thời gian quét,
có một khe gửi lại.

## 11. Khách air-gapped có nhiều team Python cần gói. Bạn đề xuất gì?

Một mirror trong vùng trong. Nhỏ và ít đổi: simple index tĩnh (PEP 503) từ danh sách gói đã duyệt, phục vụ bằng web server
có sẵn, quét virus được. Có máy cầu nối ra được PyPI: devpi làm mirror có cache. Doanh nghiệp đã có Nexus/Artifactory thì
dùng kho đó. Dù chọn gì, tính toàn vẹn nằm ở lockfile có hash của từng dự án (`uv export`, `--require-hashes`): không phải
công cụ nào cũng kiểm hash mà mirror đưa ra.

## 12. Khách nói: "Cài xong rồi, nhưng từ máy người dùng không vào được, trên server `curl localhost` thì được." Bạn hỏi gì?

Hỏi dịch vụ đang nghe địa chỉ nào (`ss -tlnp`): mặc định an toàn của nhiều sản phẩm là `127.0.0.1`, cần đặt địa chỉ nghe
rõ ràng (và đặt reverse proxy TLS phía trước). Rồi tường lửa máy chủ và mạng, DNS nội bộ của tên người dùng gõ. Và một bẫy
proxy: trình duyệt của người dùng có thể bị ép đi qua proxy công ty cho cả tên nội bộ, nếu PAC/`no_proxy` của họ không có
tên đó, request đi ra proxy rồi chết ở đó.

## 13. Bạn cần hỗ trợ từ xa một khách air-gapped khi có sự cố. Bạn đề xuất kênh nào?

Không tự dựng kênh (reverse SSH, ngrok, công cụ điều khiển từ xa cài thêm): đó là lỗ hổng mà An ninh sẽ tìm ra và mất lòng
tin. Dùng kênh khách đã có: chia sẻ màn hình trên công cụ họp của họ, admin của khách gõ lệnh theo hướng dẫn, phiên có ghi lại
và kết thúc là đóng. Thu thập chẩn đoán bằng support bundle đã loại bí mật, gửi qua MFT. Chuẩn bị trước runbook chẩn đoán để
người không phải bạn làm theo được.

## 14. Bạn viết đề nghị mở mạng gửi An ninh của khách. Một đề nghị tốt có gì?

Tên miền cụ thể (đo bằng log proxy, kể cả CDN mà công cụ bị chuyển hướng tới), cổng, máy nguồn, mục đích, tần suất, dung
lượng, thời hạn; đề nghị soi + tin CA làm mặc định, bypass chỉ khi có lý do kỹ thuật cụ thể; những gì **không** xin (máy chủ
ứng dụng, tên miền upload); chỗ nào sẽ cấu hình CA và cách An ninh tự kiểm rằng không ai tắt kiểm chứng chỉ; ngày đóng lại
và ai chấp nhận rủi ro. Đề nghị càng hẹp càng nhanh được duyệt.
