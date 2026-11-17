# Bộ câu hỏi đánh giá bảo mật nhà cung cấp: Quillo 1.0.0

Phòng An toàn thông tin, Công ty Luật (bản rút gọn, 12 câu). Trả lời ngay dưới mỗi câu. Với mỗi câu, ghi rõ:
**Trả lời** (Có / Không / Một phần / Không áp dụng), **Chi tiết**, **Bằng chứng** (tệp, cấu hình, lệnh kiểm chứng mà
chúng tôi tự chạy được), **Trách nhiệm** (nhà cung cấp / khách hàng / chung).

## Q1. Dữ liệu và luồng mạng

Hệ thống có gửi bất kỳ dữ liệu nào ra ngoài mạng nội bộ của chúng tôi không (telemetry, gọi API AI bên ngoài, kiểm tra
bản quyền, cập nhật tự động)? Liệt kê mọi kết nối ra ngoài và mọi kết nối vào.

## Q2. Lưu trữ và mã hoá khi lưu (at rest)

Tài liệu, đoạn trích, vector embedding và bản gốc tệp được lưu ở đâu? Có mã hoá at rest không, do ai quản lý khoá?

## Q3. Mã hoá khi truyền (in transit)

Kết nối từ người dùng tới hệ thống và giữa các thành phần có mã hoá TLS không? Hỗ trợ CA nội bộ của chúng tôi không?

## Q4. Xác thực

Hỗ trợ SSO với IdP của chúng tôi (giao thức nào)? MFA thực thi ở đâu? Có tài khoản cục bộ, tài khoản dùng chung hay
token tĩnh nào không, và kiểm soát chúng thế nào?

## Q5. Phân quyền

Làm sao đảm bảo nhân viên phòng này không đọc được tài liệu của phòng khác, kể cả qua câu trả lời của AI?

## Q6. Nhật ký

Hệ thống ghi log những gì? Log có chứa dữ liệu cá nhân hoặc nội dung tài liệu không? Định dạng, nơi lưu, thời gian
lưu?

## Q7. Quản lý bí mật (secret)

Mật khẩu database, token quản trị, client secret OIDC được lưu và cung cấp cho ứng dụng thế nào? Có tích hợp Vault
không? Xoay (rotate) secret thế nào?

## Q8. Chuỗi cung ứng phần mềm và lỗ hổng

Làm sao chúng tôi xác minh gói cài đặt không bị sửa? Có SBOM không? Quy trình vá lỗ hổng và thời gian phản hồi?

## Q9. Mô hình AI

Mô hình nào được dùng, chạy ở đâu? Dữ liệu và câu hỏi của chúng tôi có được dùng để huấn luyện hay cải thiện mô hình
không? Câu hỏi của người dùng có được lưu không?

## Q10. Xoá dữ liệu

Khi một tài liệu bị gỡ khỏi nguồn, hoặc khi chấm dứt hợp đồng, dữ liệu được xoá thế nào và chứng minh ra sao?

## Q11. Truy cập của nhà cung cấp

Nhân sự của nhà cung cấp có truy cập hệ thống hoặc dữ liệu không, khi nào, bằng cách nào? Dữ liệu chẩn đoán gửi về nhà
cung cấp gồm những gì?

## Q12. Rủi ro riêng của AI

Nhà cung cấp đánh giá và giảm thiểu rủi ro prompt injection qua nội dung tài liệu, và câu trả lời sai (hallucination)
thế nào?
