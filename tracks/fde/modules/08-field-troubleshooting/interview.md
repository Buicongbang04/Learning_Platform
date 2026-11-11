# Câu hỏi phỏng vấn: xử lý sự cố tại hiện trường

## Khách gọi lúc 8 giờ sáng: "hệ thống của các anh chết rồi". Bạn làm gì trong 15 phút đầu?

Chưa gõ lệnh nào. Biến câu đó thành thứ kiểm được: cái gì không chạy (đăng nhập, hỏi đáp, nạp dữ liệu), với ai (một
người, một phòng, tất cả), từ khi nào, gần đây đổi gì (bảo trì, vá OS, chuyển máy, đổi mạng), cái gì **vẫn** chạy. Xác
nhận mức độ và hẹn giờ cập nhật kế tiếp. Xin support bundle nếu khách chưa gửi. Liệt kê 2-4 giả thuyết từ những câu trả
lời đó, rồi chọn lệnh chỉ đọc rẻ nhất phân biệt được chúng. Phần "cái gì vẫn chạy" thường loại được nửa số giả thuyết
trước khi ai phải đăng nhập vào đâu.

## Bạn không có quyền vào máy, IT của khách gõ lệnh hộ qua screen-share. Làm sao để buổi đó hiệu quả?

Mỗi lệnh có lý do nói trước được ("nếu ra X thì loại A"); một lệnh mỗi lần, đọc to và giải thích lệnh làm gì, không đổi
gì; chỉ lệnh chỉ đọc trong giai đoạn chẩn đoán; dặn che secret trước khi dán (và chọn lệnh ít in secret: `docker inspect
--format` một trường thay vì cả object, không `env`, không `cat` tệp cấu hình nguyên văn). Ghi nhật ký lệnh, giờ, kết
luận. Thực tế có khoảng 3-5 lệnh trước khi khách mất kiên nhẫn, nên những lệnh đó phải là lệnh phân biệt được nhiều giả
thuyết nhất, không phải lệnh "xem cho biết".

## Khách đề nghị "restart thử xem". Bạn trả lời thế nào?

Restart là một thay đổi trên production và xoá bằng chứng: log của container cũ (nếu bị tạo lại), trạng thái tiến trình
treo, bộ nhớ, kết nối đang mở. Nếu sự cố đang gây ảnh hưởng nặng và restart là workaround đã biết, thu bằng chứng trước
(bundle, vài lệnh chỉ đọc, `docker inspect`, `ps`), rồi restart có chủ đích, ghi lại giờ. Nếu không, chẩn đoán trước. Sự
cố tự hết sau restart mà không biết vì sao thường quay lại vào lúc tệ hơn, và lúc đó không còn bằng chứng của lần trước.

## Support bundle của sản phẩm nên thu gì và tuyệt đối không thu gì?

Thu: phiên bản OS/kernel/sản phẩm, tài nguyên (`df -h`, `df -i`, `free`, `uptime`), mạng (địa chỉ, route, socket đang
nghe, resolver, biến proxy hệ thống đã che), trạng thái dịch vụ và restart count, cấu hình **của sản phẩm** đã che, phần
cuối của log có giới hạn, health endpoint, danh sách lệnh đã lỗi. Không thu: biến môi trường của tiến trình, shell
history, private key, dữ liệu nghiệp vụ, dump database, log không giới hạn. Chạy không cần root, dọn sạch tệp tạm, lệnh
lỗi không làm hỏng cả bundle. Thước đo: bundle chỉ chứa thứ bạn chấp nhận thấy trong một ticket mà nhiều người đọc.

## Làm sao chắc support bundle không lộ secret?

Che theo dạng (userinfo trong URL, cặp khoá-giá trị có tên nhạy cảm, header `Authorization`) trên **mọi** tệp, kể cả
output lệnh (status của systemd in log, `docker inspect` có `Env`), giữ dòng và tên khoá. Không thu các nguồn rủi ro cao
thay vì cố che chúng. Rồi **kiểm bằng thử nghiệm**: gieo secret ngẫu nhiên vào mọi chỗ có thể (cấu hình, env của
service và container, log, tệp khoá) trên máy thử, chạy bundle, grep cả secret lẫn từng đoạn của nó trong bundle đã giải
nén. Regex không bao giờ hoàn hảo; test có secret gieo ngẫu nhiên là thứ biến "chắc là không lộ" thành bằng chứng.

## `curl` báo "SSL certificate problem: unable to get local issuer certificate" ở máy khách. Bạn nghĩ gì và hỏi gì?

Kết nối TLS đã lên, server đưa chuỗi chứng chỉ mà trust store **của curl trên máy đó** không dẫn được về CA nào nó tin.
Ở doanh nghiệp, hai khả năng hàng đầu: proxy có TLS inspection (chứng chỉ do CA của proxy ký) hoặc dịch vụ nội bộ dùng CA
nội bộ. Hỏi: có proxy không (`env | grep -i proxy` của chính tiến trình đó, dòng `Uses proxy env variable` trong `curl
-v`), `openssl s_client -connect host:443 -servername host` cho thấy issuer là ai. Sửa bằng cách lấy CA của khách qua kênh
tin cậy và đưa vào **đúng** trust store của ứng dụng (OS, certifi của Python, cacerts của Java, image container), không
bao giờ bằng `-k`/`verify=False` trên production.

## Phân biệt "Connection refused", "Connection timed out" và "No route to host".

Refused: máy đích sống và trả RST, không ai nghe cổng đó (dịch vụ chưa lên, nghe sai địa chỉ như chỉ `127.0.0.1`, sai
cổng). Timeout: không ai trả lời trong thời gian chờ: firewall bỏ gói, đích tắt, hoặc qua proxy thì proxy đang chờ đích
hộ bạn. No route / network unreachable: chính kernel của máy gửi không biết đường (không route, không gateway) hoặc máy
cùng subnet không trả lời ARP. Mỗi loại một người sửa: chủ dịch vụ, đội firewall, đội mạng. Qua proxy thì nhớ địa chỉ
trong `Trying …` là của proxy, và mã HTTP ở bước CONNECT là của proxy.

## Một dịch vụ trả "502 Bad Gateway" mà dịch vụ đó không bao giờ trả 502. Bạn suy ra gì?

Có thứ gì đó đứng giữa client và dịch vụ trả lời thay: reverse proxy, load balancer, sidecar, hay một forward proxy mà
client không định đi qua. Tìm xem client thực sự gửi request tới đâu (biến proxy của **tiến trình** client, cấu hình
service mesh, DNS trỏ đi đâu) và log của thứ đứng giữa. Song song, kiểm dịch vụ đích trực tiếp từ cùng mạng với client;
nếu nó trả lời bình thường thì vấn đề nằm trên đường đi, không phải ở dịch vụ.

## Khi nào bạn dùng `strace` hay `tcpdump` ở máy khách, và cần lưu ý gì?

Khi log và các lệnh thông thường đã thu hẹp về một tiến trình hay một kết nối cụ thể mà vẫn không biết nó đang chờ gì.
`strace -f -tt -e trace=network,file -p <pid>` cho thấy syscall treo hay errno (`EACCES` khi mở tệp, `connect()` tới đâu);
`tcpdump -ni <if> host X and port Y -c 50` cho thấy SYN có đi ra, có SYN-ACK hay RST quay về. Cả hai thường cần quyền
khách phải duyệt (`ptrace` với tiến trình user khác, `CAP_NET_RAW`), có thể chạm tới dữ liệu nhạy cảm trong payload, và
có chi phí hiệu năng. Xin phép rõ ràng, giới hạn bộ lọc và số gói/thời gian, không mang pcap có payload ra khỏi mạng khách.

## Log khách gửi có 5 dịch vụ, 5000 dòng, không theo thứ tự. Bạn đọc thế nào?

Không đọc từng dòng. Tách theo dịch vụ, phân tích các dòng có cấu trúc, xếp theo thời gian thật. Gom cảnh báo/lỗi theo
(dịch vụ, thông điệp cố định) với số lần, lần đầu, lần cuối; đếm request 5xx theo endpoint; xếp các sự kiện xấu thành
từng đợt tách bởi khoảng lặng. Dòng lỗi đầu tiên của một đợt thường gần nguyên nhân hơn dòng nhiều nhất. Kiểm đồng hồ
các máy trước khi so log giữa máy. Nhớ log có thể thiếu (log driver không ghi được, container cũ đã bị xoá), và khoảng
trống là một câu hỏi phải hỏi.

## Lỗi chỉ xảy ra ở khách, bạn không được thử trên máy họ. Bạn tái hiện thế nào?

Lấy từ bundle mọi thứ cố định: phiên bản, cấu hình đã che, thứ tự sự kiện, và chữ ký lỗi đầy đủ (dịch vụ, thông điệp,
kiểu exception, phần lý do sau khi bỏ host/cổng/thời gian). Liệt kê điều kiện môi trường khác máy lab (proxy, CA nội bộ,
không root, đĩa nhỏ, SELinux, OS cũ) và dựng điều kiện tối thiểu gây ra **đúng** chữ ký đó, không phải "một lỗi giống".
Script hoá (`repro.sh`) để chạy lại được và để đội sản phẩm chạy trên máy họ, không dùng dữ liệu hay secret của khách. Thử
cách sửa ở lab trước khi đề xuất cho khách, kèm cách kiểm sau khi sửa.

## Bạn escalate một lỗi cho đội sản phẩm. Ticket của bạn có gì?

Tiêu đề nêu chữ ký lỗi và hành vi sai, không phải tên khách. Phiên bản chính xác và môi trường khác mặc định ở đâu. Cách
tái hiện chạy được trên máy sạch (lý tưởng là script), kết quả mong đợi và thực tế, hoặc lý do chưa tái hiện được. Bằng
chứng đã che secret, có nguồn. Sự thật đã kiểm, giả thuyết, những gì đã loại trừ, tách bạch. Ảnh hưởng, mức độ có lý do,
workaround đang dùng và giới hạn. Câu hỏi hay quyết định cụ thể bạn cần đội trả lời. Kỹ sư on-call đọc 30 giây phải biết
lỗi gì, tái hiện thế nào.

## Nguyên nhân sự cố nằm ở phía khách (IT của họ đổi cấu hình). Bạn viết báo cáo sự cố thế nào?

Nói thẳng nguyên nhân theo bằng chứng, nhưng mô tả **điều kiện và quy trình**, không gọi tên người ("nguồn giờ cũ đã tắt
mà cấu hình máy không đổi theo", không phải "anh X quên đổi"). Có tóm tắt cho người không kỹ thuật, ảnh hưởng định lượng,
timeline theo giờ của khách, cách đã khắc phục, việc phòng ngừa có bên chịu trách nhiệm và hạn: phần của khách, và phần
của bạn (bạn gần như luôn có phần: preflight, checklist, giám sát, tài liệu). Không hứa tính năng thay đội sản phẩm. Điều
chưa chứng minh thì để ở mục "chưa biết". Không tên, email nhân viên, không mảnh secret nào.

## Khách hỏi: "tại sao support bundle của các anh cần nhóm docker? Thế có khác gì root?"

Họ đúng: thuộc nhóm `docker` gần như tương đương root trên máy đó (mount `/` vào một container là xong). Trả lời trung thực
và đưa lựa chọn: chạy bundle bằng user vận hành vốn đã trong nhóm docker (không cấp thêm quyền mới), hoặc chạy phần
Docker riêng bởi người có quyền đó còn phần còn lại bằng user thường, hoặc dùng một cách đọc chỉ-đọc mà nền tảng hỗ trợ
(Docker socket proxy chỉ cho `GET`, Podman rootless của chính user). Bundle phải chạy được khi thiếu quyền đó (ghi lỗi,
thu phần còn lại), để quyết định cấp quyền là của khách.
