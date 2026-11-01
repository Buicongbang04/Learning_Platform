# Lời giải: sự cố TLS chỉ một số client lỗi

Bài Advanced không có một đáp án duy nhất. Dưới đây là chẩn đoán, các quyết định khi viết, rubric, và một postmortem mẫu
đã chạy qua test (đặt vào `starter/POSTMORTEM.md` thì `test_postmortem_document` pass).

## Chẩn đoán

**Nguyên nhân kỹ thuật**: change CHG-2291 trỏ `ssl_certificate` vào `cert.pem` (chỉ cert lá) thay vì `fullchain.pem`
(cert lá + intermediate `R11`). Bằng chứng: `s_client-before-fix.txt` có đúng một mục `0 s:CN = api...` trong
`Certificate chain`, lỗi `num=20 unable to get local issuer certificate` rồi `num=21 unable to verify the first
certificate`; `s_client-after-fix.txt` có hai mục; `nginx-api-diff.txt` cho thấy đúng dòng đó đổi.

**Vì sao chỉ một số client lỗi**: server TLS có trách nhiệm gửi đủ chuỗi tới (không cần gửi) root. Client chỉ có kho root.

| Client | Có tự hoàn thiện chuỗi thiếu intermediate không | Kết quả |
| --- | --- | --- |
| Chrome, Edge, Safari desktop | Có: đọc URL **AIA** (`CA Issuers`) trong cert lá để tải intermediate, và cache intermediate đã gặp ở site khác (Firefox dùng danh sách intermediate preload) | Không lỗi |
| iOS (URLSession) | Có: hệ thống tự tải theo AIA và có cache intermediate | Không lỗi |
| Android (OkHttp / Conscrypt) | Không tải AIA (một số bản có cache intermediate nhưng không đảm bảo) | Lỗi |
| Java (JSSE) | Không, trừ khi bật `com.sun.security.enableAIAcaIssuers=true` | Lỗi |
| OpenSSL: Python, curl, phần lớn công cụ Linux | Không bao giờ tải AIA | Lỗi |

Vì vậy "tôi mở Chrome thấy xanh" là phép thử tệ nhất cho chuỗi cert: nó là client khoan dung nhất.

**POS**: `s_client-no-sni.txt` cho thấy client không gửi SNI nhận cert `shop.olist-shop.com.br` của khối
`default_server`, nên báo `hostname mismatch`. Đây là vấn đề **khác**, có từ trước (ticket POS-77), không do CHG-2291.
Postmortem tốt nhắc nó trong phần tác động như "không thuộc sự cố này" và tạo việc riêng (ví dụ: khối `default_server`
dùng cert có SAN `api...` cho cổng mà POS gọi, hoặc tách IP/cổng riêng cho POS, hoặc nâng firmware), không trộn vào
nguyên nhân gốc.

**Yếu tố góp phần** (đây là chỗ ăn điểm nhất):

- Thay cert là thao tác tay, tải "Certificate (PEM)" từ portal; không có ACME client tự gia hạn (certbot, lego, cert-manager)
  vốn luôn xuất `fullchain.pem`.
- Kiểm sau change bằng trình duyệt, không bằng một client nghiêm ngặt (`openssl s_client -verify_return_error`, `curl`).
- Synthetic chỉ kiểm hạn cert, không xác minh chuỗi với một kho root chuẩn.
- Thời gian tới khi phát hiện dài: cảnh báo lỗi `payment-sync` lúc 18:58 không được nối với change 18:41; dấu hiệu "Chrome
  được, curl không" bị hiểu thành DNS/CDN cache, tốn 18 phút purge CDN.
- Change đóng ngay sau khi reload, không có cửa sổ quan sát; không có bước rollback ghi sẵn.

## Việc cần làm nên có

| Việc | Loại |
| --- | --- |
| Gia hạn bằng ACME client tự động, Nginx trỏ vào `fullchain.pem` do client sinh; không sửa tay | phòng ngừa |
| CI/pre-deploy: `openssl verify -untrusted` hoặc khởi động Nginx trong container và gọi bằng `curl` với kho root chuẩn; chặn deploy khi chuỗi thiếu | phòng ngừa |
| Synthetic check bằng client nghiêm ngặt (curl/OpenSSL, Java) từ nhiều nơi, cảnh báo khi verify lỗi, không chỉ khi sắp hết hạn | phát hiện |
| Dashboard lỗi TLS theo loại client / user agent; cảnh báo khi tỉ lệ handshake lỗi tăng | phát hiện |
| Runbook "sau khi đổi cert": lệnh `s_client` đếm số cert trong chuỗi, `-servername` và không SNI | giảm thiểu |
| Xử lý POS-77 (không SNI) như việc riêng có người phụ trách | phòng ngừa |

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Nguyên nhân kỹ thuật đúng, có bằng chứng | 20 | Nêu `cert.pem` thay cho `fullchain.pem`, trích số cert trong chuỗi trước và sau |
| Giải thích vì sao chỉ một số client lỗi | 15 | Nói AIA fetching / cache intermediate ở trình duyệt và iOS, OpenSSL/Java/Android không làm |
| Tách bạch vấn đề POS | 10 | Nhận ra SNI/`default_server`, có từ trước, không gộp vào nguyên nhân gốc, có việc riêng |
| Tác động định lượng | 10 | Số request lỗi theo loại client, thời gian 18:41–20:06 (85 phút), 1.840 đơn đối tác, ước tính doanh thu |
| Dòng thời gian | 10 | Có mốc change, mốc lỗi đầu tiên, mốc phát hiện, chẩn đoán sai (purge CDN), sửa, xác nhận; tính được time to detect và time to resolve |
| Yếu tố góp phần và phát hiện | 15 | Quy trình tay, kiểm bằng trình duyệt, synthetic chỉ xem hạn, cảnh báo không nối với change |
| Việc cần làm | 15 | Cụ thể, kiểm được, có người và hạn; có ít nhất một việc biến lỗi thành thứ máy chặn trước production |
| Blameless và rõ ràng | 5 | Không đổ lỗi cá nhân; người ngoài team đọc hiểu |

Trừ điểm: kết luận "do CDN" hoặc "do DNS" (−15); việc cần làm kiểu "cẩn thận hơn khi đổi cert" (−10); gộp POS vào nguyên
nhân gốc (−5).

## Postmortem mẫu

`````markdown
# Postmortem: lỗi TLS trên api.olist-shop.com.br ngày 2026-10-30

## 1. Tóm tắt

Tối thứ Sáu 30/10, từ 18:41 tới 20:06 (giờ São Paulo, 85 phút), API của Olist Shop gửi chuỗi chứng chỉ thiếu
chứng chỉ trung gian sau một lần thay cert thủ công. Trình duyệt và iPhone tự bù phần thiếu nên vẫn chạy, còn app
Android, tích hợp của đối tác logistics và worker đồng bộ thanh toán không kết nối được. Đã sửa bằng cách trỏ Nginx
về tệp fullchain; mọi hệ thống đã chạy lại và đối tác đã đồng bộ xong.

## 2. Tác động

- 95.200 trên 412.300 request tới API lỗi bắt tay TLS (23%) trong 85 phút.
- App Android: 52.300 request lỗi, giỏ hàng không tải được; ước tính mất khoảng 6% đơn của khung giờ.
- Đối tác logistics: 100% request lỗi, 1.840 đơn phải đồng bộ lại.
- Worker `payment-sync`: 31.200 request lỗi, trạng thái thanh toán trễ tới 85 phút.
- Không bị ảnh hưởng: trình duyệt desktop, app iOS.
- Không thuộc sự cố này: 2.000 request lỗi `hostname mismatch` từ POS firmware 2019 ở 14 cửa hàng, có từ trước (POS-77).

## 3. Dòng thời gian

| Thời điểm | Sự kiện | Nguồn |
| --- | --- | --- |
| 18:32 | Bắt đầu CHG-2291 thay cert, tải "Certificate (PEM)" từ portal | Chat |
| 18:41 | Reload Nginx trên lb-1, lb-2 với `cert.pem`; kiểm bằng Chrome thấy xanh, đóng change | Chat, diff Nginx |
| 18:44 | Synthetic kiểm hạn cert báo OK | Monitor |
| 18:58 | `payment-sync` báo 312 lỗi trong 10 phút, chưa ai nối với change | Log worker |
| 19:07 | CSKH báo app Android lỗi giỏ hàng | Chat |
| 19:15 | Đối tác logistics báo `PKIX path building failed` | Email |
| 19:22 | curl lỗi 60, Chrome vẫn được; nghi DNS/CDN, purge CDN | Chat |
| 19:40 | Purge không giúp; mở SEV-2 | Chat |
| 19:52 | `openssl s_client` cho thấy server chỉ gửi 1 cert | s_client trước khi sửa |
| 20:03 | Trỏ `ssl_certificate` về `fullchain.pem`, reload | Chat |
| 20:06 | curl, Java, `payment-sync` hết lỗi | s_client sau khi sửa |
| 20:15 | Đối tác xác nhận chạy lại | Email |

Time to detect (từ lỗi đầu tiên tới SEV-2): 59 phút. Time to resolve: 85 phút.

## 4. Nguyên nhân gốc và yếu tố góp phần

Nginx được cấu hình `ssl_certificate /etc/nginx/tls/api/cert.pem`, tệp chỉ chứa cert lá của `api.olist-shop.com.br`.
Trước change, cấu hình trỏ vào `fullchain.pem` gồm cert lá và intermediate `R11` của Let's Encrypt. Client chỉ có root
`ISRG Root X1` trong kho tin cậy, nên cần server gửi intermediate để dựng chuỗi. `s_client` trước khi sửa thấy một cert và
lỗi `unable to get local issuer certificate`; sau khi sửa thấy hai cert và `Verify return code: 0`.

Chỉ một số client lỗi vì trình duyệt desktop và iOS tự tải intermediate theo URL AIA trong cert lá hoặc dùng intermediate
đã cache, còn OpenSSL (Python, curl), Java và Android không làm vậy. Vì thế kiểm bằng trình duyệt không phát hiện được.

Yếu tố góp phần:

- Thay cert là việc tay qua portal; bản tải mặc định là cert lá, không phải fullchain. Không có ACME client tự động.
- Bước kiểm sau change dùng trình duyệt, client khoan dung nhất, thay vì một client nghiêm ngặt.
- Synthetic chỉ kiểm hạn cert, không xác minh chuỗi.
- Cảnh báo lỗi của `payment-sync` lúc 18:58 không hiện cạnh change vừa đóng, nên không ai nối hai việc.
- Change đóng ngay sau reload, không có cửa sổ quan sát và lệnh rollback ghi sẵn.

## 5. Phát hiện và xử lý

Giám sát không bắt được vì synthetic chỉ đọc ngày hết hạn của cert, mà cert mới hoàn toàn hợp lệ về ngày. Tín hiệu đầu
tiên là lỗi của worker 17 phút sau change, rồi tới phản ánh của CSKH và đối tác. Chẩn đoán mất thêm 30 phút vì triệu chứng
"Chrome được, curl không" được hiểu thành cache DNS hoặc CDN, dẫn tới purge CDN không cần thiết. Thứ giúp tìm ra là
`openssl s_client -showcerts`, đếm số cert trong mục Certificate chain. Sửa bằng một dòng cấu hình và reload, không cần
cấp lại cert.

## 6. Việc cần làm

| Việc | Loại | Người phụ trách | Hạn |
| --- | --- | --- | --- |
| Chuyển gia hạn cert sang ACME client tự động, Nginx chỉ trỏ vào fullchain do client sinh | phòng ngừa | Team platform | 2026-11-20 |
| Pipeline deploy Nginx chạy `openssl verify -untrusted` và `curl` với kho root chuẩn, chặn khi chuỗi thiếu | phòng ngừa | Team platform | 2026-11-13 |
| Synthetic check TLS bằng curl và Java từ 3 vùng, cảnh báo khi verify lỗi | phát hiện | SRE | 2026-11-10 |
| Dashboard tỉ lệ handshake lỗi theo user agent, cảnh báo khi vượt 1% | phát hiện | SRE | 2026-11-17 |
| Runbook đổi cert: lệnh s_client có và không SNI, đếm cert, cửa sổ quan sát 30 phút, lệnh rollback | giảm thiểu | On-call lead | 2026-11-06 |
| Xử lý POS-77: cert cho khối default_server hoặc cổng riêng cho POS không SNI | phòng ngừa | Team cửa hàng | 2026-11-30 |

## 7. Bài học

- Trình duyệt là client khoan dung nhất; kiểm TLS phải dùng client nghiêm ngặt như các hệ thống gọi API.
- Giám sát cert phải trả lời "client có tin cert này không", không chỉ "cert còn hạn không".
- Việc định kỳ làm tay là việc sẽ có ngày làm sai; gia hạn cert phải tự động từ đầu tới cuối.
`````
