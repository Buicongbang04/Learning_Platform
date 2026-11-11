# Câu hỏi phỏng vấn: tích hợp hệ thống và dữ liệu của khách

## Khách nói "đăng nhập SSO được nhưng không thấy gì". Bạn làm gì trong 30 phút đầu?

Tách làm hai nửa và kiểm bằng dữ liệu thật. Nửa một: sản phẩm nhận ra người gọi là ai, thuộc nhóm/vai trò nào (endpoint
kiểu `/api/me`, log đăng nhập). Lấy một token thật của đúng người dùng đó, giải mã payload và so với claim sản phẩm đang
chờ (tên claim, dạng giá trị, có trong access token hay chỉ ID token). Nửa hai: quyền được ánh xạ thế nào: so quy tắc
phân quyền với dữ liệu **sản phẩm đã lưu** (đường dẫn, mã phòng ban) bằng tài khoản quản trị. Có thể có lỗi ở cả hai
nửa; sửa một, kiểm lại bằng token mới của từng người, rồi mới sang nửa kia. Phần thuộc IdP thì viết yêu cầu cho IT kèm lý
do và cách kiểm, không xin quyền admin.

## Resource server kiểm những gì trên một access token JWT, theo thứ tự nào?

Tách header lấy `alg` và `kid` (chỉ để chọn khoá); `alg` phải nằm trong danh sách bạn chấp nhận (RS/PS/ES), không lấy từ
token; chọn khoá theo `kid` trong JWKS (lạ thì tải lại một lần, có giới hạn tần suất); kiểm chữ ký; rồi `iss` khớp
nguyên chuỗi, `aud` chứa định danh của bạn, `exp`/`nbf`/`iat` với độ lệch nhỏ. Chỉ sau đó mới đọc claim nghiệp vụ. Lý do
thứ tự: mọi thứ trước chữ ký là dữ liệu kẻ tấn công kiểm soát. Hai lỗi kinh điển: `alg: none` và ký HMAC bằng khoá công
khai (RFC 8725).

## Vì sao phải kiểm `aud` khi chữ ký và issuer đều đúng?

Vì cùng một IdP cấp token cho mọi ứng dụng trong realm/tenant, ký bằng cùng khoá. Không kiểm `aud` thì token người dùng
lấy cho một ứng dụng khác (portal nội bộ, công cụ có thể bị lộ token) cũng mở được API của bạn: một ứng dụng yếu nhất
trong realm thành cửa vào ứng dụng của bạn. Muốn `aud` có client id của bạn, IdP phải được cấu hình (audience mapper,
resource/scope tương ứng).

## IT khách xoay khoá ký của IdP lúc 2 giờ sáng. Điều gì xảy ra với sản phẩm của bạn?

Token mới mang `kid` mới. Resource server cache JWKS mãi thì từ chối mọi token mới tới khi restart ("sự cố lúc 8 giờ
sáng"); tải JWKS mỗi request thì sống sót nhưng dồn tải lên IdP. Cách đúng: cache theo `kid`, gặp `kid` lạ thì tải lại
(có giới hạn tần suất), có TTL để khoá đã gỡ không sống mãi. Token cũ còn hạn vẫn hợp lệ nếu IdP giữ khoá cũ trong JWKS
một thời gian, điều nên hỏi IT khi lập kế hoạch xoay khoá.

## Khách chỉ có Active Directory, hỏi sao sản phẩm không "nối LDAP" cho nhanh. Bạn trả lời thế nào?

Nối LDAP trực tiếp nghĩa là sản phẩm nhận và chuyển mật khẩu người dùng, không có MFA, không SSO, mỗi ứng dụng một bản
sao logic tìm nhóm lồng nhau. Hỏi trước: họ có AD FS hay Entra ID (đồng bộ từ AD) không: có thì nối OIDC/SAML qua đó.
Không có thì đề xuất một broker do IT quản (vd. Keycloak với LDAP user federation, LDAPS với CA nội bộ), sản phẩm vẫn chỉ
nói OIDC. Ghi rõ ai vận hành broker.

## Khác biệt thực tế khi khách dùng SAML thay vì OIDC?

SAML là XML assertion ký, đi qua trình duyệt bằng POST, không có back-channel lấy token, không có access token cho API
hay CLI; nhóm là attribute trong assertion. Lỗi hiện trường hay gặp: xoay chứng chỉ ký của IdP (metadata cũ), lệch đồng
hồ, `NameID` sai định dạng, attribute nhóm không được release cho SP. Nếu sản phẩm cần API cho script, vẫn cần một cơ chế
token riêng (OIDC song song, hoặc token dịch vụ), nói rõ từ đầu.

## Khách muốn quillo phân quyền "giống quyền trên file share". Bạn thiết kế thế nào và nói trước điều gì?

Giữ đường dẫn từ nguồn tới sản phẩm (connector không làm phẳng thư mục), ánh xạ thư mục cấp trên sang nhóm IdP (đúng
nhóm khách đã dùng cho ACL của share), viết quy tắc theo chuỗi sản phẩm đã lưu. Nói trước: đây là **mô phỏng** quyền ở
mức thư mục, không phải đồng bộ ACL từng tệp của NTFS (quyền riêng từng tệp, deny, kế thừa bị ngắt không được mô phỏng);
đổi quyền ở share không tự đổi ở sản phẩm; nhóm của phiên UI được giữ tới khi đăng nhập lại. Khách cần chính xác từng tệp
thì đó là yêu cầu cho product, kèm chi phí.

## Connector của bạn chạy mỗi đêm. Nêu những thuộc tính nó phải có, và cách bạn kiểm từng thuộc tính.

Incremental (chỉ đọc nội dung khi metadata đổi; kiểm bằng cách tước quyền đọc một tệp không đổi rồi chạy lại), không giao
trùng (state riêng của connector, không suy từ đích; kiểm bằng cách giả lập đích bị dọn), idempotent (chạy lại không làm
gì: so cây đích trước/sau gồm mtime và inode), xoá đúng (chỉ gỡ cái mình giao), chịu lỗi từng mục (một tệp hỏng không
dừng cả lượt, mã thoát báo động), ghi nguyên tử (tệp tạm + rename; state ghi sau mỗi mục), không cần root hay công cụ hệ
thống của khách.

## Khách gửi tệp CSV, mở ra thấy "lỗi font". Bạn tiếp cận thế nào?

Coi bảng mã là giả thuyết cần bằng chứng: hỏi hệ thống nguồn chạy nền tảng gì, ngôn ngữ gì, năm nào; xem các byte ≥ 0x80
và giải mã thử theo các ứng viên với `errors="strict"`; đối chiếu với một bản ghi người dùng chụp từ màn hình hệ thống
gốc. Sau khi giải mã, chuẩn hoá Unicode trước khi so sánh hay lưu. Rồi mới tới dấu phân cách, ô nhiều dòng, định dạng
ngày/số. Không dùng bảng mã "đọc được mọi byte" để cho hết lỗi: hết lỗi không có nghĩa là đúng.

## Vì sao chính sách bảo mật hay cấm secret trong biến môi trường, và bạn chứng minh tuân thủ thế nào?

Env kế thừa sang mọi tiến trình con, nằm trong `/proc/<pid>/environ`, `docker inspect`, `systemctl show`, crash report
và support bundle có `env`; tham số dòng lệnh còn tệ hơn vì mọi user thấy qua `ps`. Tệp có quyền và chủ riêng, audit được,
xoay được (quy ước `*_FILE`, Docker/K8s secrets, Vault Agent). Chứng minh bằng secret gieo ngẫu nhiên mỗi lần chạy: chạy
đường thành công và mọi đường lỗi, tìm giá trị đó trong stdout/stderr, log, tệp, `/proc/*/cmdline`, `/proc/*/environ`.

## Phòng bảo mật hỏi "dữ liệu có được mã hoá at rest không". Sản phẩm không tự mã hoá. Bạn trả lời gì?

"Một phần", kèm sự thật: dữ liệu nằm ở đâu (database, bản gốc tệp, backup), sản phẩm không mã hoá ở tầng ứng dụng, mã
hoá at rest dựa vào mã hoá đĩa/volume do khách quản khoá, lệnh để họ tự kiểm (`lsblk -f`, vị trí volume). Thêm biện pháp
bù và kế hoạch nếu có (yêu cầu gửi product). Trả lời "Có, AES-256" cho đẹp là tạo một cam kết sai trong hợp đồng và mất
uy tín ở buổi kiểm tra kỹ thuật.

## Khách lo dữ liệu cá nhân trong hợp đồng bị "đưa vào AI". Bạn đề xuất gì?

Đi theo dữ liệu: bản gốc, chunk, embedding, prompt, log, backup. Xử lý **trước khi index** vì embedding không che được sau
khi tính: phát hiện theo loại (mẫu có cấu trúc + kiểm tra hợp lệ; NER chạy local cho tên, địa chỉ), hai góc nhìn (đầy đủ
cho người phụ trách, đã che hoặc bí danh nhất quán có khoá do khách giữ cho người còn lại) gắn với phân quyền hiện có, đo
recall/precision trên bộ có nhãn và ảnh hưởng tới chất lượng trả lời, đường xoá theo yêu cầu. Không dùng dịch vụ phát hiện
PII trên cloud; nói rõ rủi ro còn lại (che sót, nhận diện gián tiếp).

## Khách hỏi "dữ liệu có ở lại Việt Nam không" với một sản phẩm on-prem. Câu trả lời đầy đủ gồm gì?

Máy đặt ở đâu chỉ là một phần. Đủ là: model và mọi thành phần chạy local, không telemetry, không kiểm bản quyền hay cập
nhật tự động qua internet (kiểm bằng chạy được air-gapped, bảng kết nối ra), và quy trình hỗ trợ của chính vendor không
mang dữ liệu ra (support bundle không có tài liệu, che secret; không chép dữ liệu về máy kỹ sư). Kèm trách nhiệm của khách
(backup ngoài site đặt ở đâu).
