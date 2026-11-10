# ADR-012: Nền tảng CI/CD và artifact repository sau khi sáp nhập Lojas Rápidas

Trạng thái: đề xuất. Người viết: platform team. Ngày: 2026-11-01.

## 1. Bối cảnh

Olist dùng GitHub Actions và GHCR cho khoảng 60 service. Lojas Rápidas dùng Jenkins tự host với 40 pipeline viết bằng Groovy và
Nexus OSS làm proxy cho Maven, npm, PyPI và Docker. Ban lãnh đạo muốn một nền tảng chung trong năm nay để giảm chi phí vận hành
và để kỹ sư hai bên chuyển team dễ dàng. Platform team có ba người. Một phần artifact của Lojas phải lưu ở Brazil theo hợp đồng.

## 2. Tiêu chí và trọng số

| Tiêu chí | Trọng số | Cách đo |
| --- | --- | --- |
| Chi phí | 30 | USD mỗi năm |
| Bảo mật | 30 | Đánh giá của security |
| Trải nghiệm dev | 30 | Khảo sát |
| Công sức chuyển đổi | 20 | Số tuần kỹ sư |
| Hỗ trợ đa định dạng | 10 | Số định dạng gói |

## 3. Phương án CI/CD

| Phương án | Điểm mạnh | Điểm yếu | Chi phí ước tính | Điểm |
| --- | --- | --- | --- | --- |
| GitHub Actions | Đã dùng ở Olist | Runner tính phút | 40.000 USD/năm | 8 |
| Jenkins | Đã dùng ở Lojas | Tự vận hành | 60.000 USD/năm | 6 |

## 4. Phương án artifact repository

| Phương án | Điểm mạnh | Điểm yếu | Chi phí ước tính | Điểm |
| --- | --- | --- | --- | --- |
| GHCR | Gắn với GitHub | Chỉ container và vài định dạng | Trong gói GitHub | 7 |
| Nexus Repository Pro | Đa định dạng, tự host ở Brazil | Phải vận hành | 25.000 USD/năm | 8 |
| Artifactory | Mạnh nhất | Đắt | 70.000 USD/năm | 6 |

## 5. Quyết định

Chọn GitHub Actions cho CI/CD và GHCR cho mọi artifact vì đơn giản nhất.

## 6. Hệ quả

- Lojas phải viết lại pipeline.
- Chi phí runner tăng.
- Đơn giản hoá vận hành.
- Kỹ sư Lojas cần đào tạo.

## 7. Kế hoạch chuyển đổi

- Viết lại pipeline Jenkins.
- Chuyển artifact sang GHCR.
- Tắt Jenkins.
- Tắt Nexus.

## 8. Điều kiện xem lại quyết định

- Chi phí vượt dự kiến.
- Security phản đối.
