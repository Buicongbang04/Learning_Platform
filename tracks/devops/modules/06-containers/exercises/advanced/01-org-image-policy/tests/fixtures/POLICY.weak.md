# Chính sách container image của Olist

## 1. Phạm vi và nguyên tắc

Chính sách áp dụng cho mọi image do các team của Olist build và chạy, gồm service, job định kỳ và image dùng trong CI.
Team platform sở hữu chính sách và danh sách image nền; team sản phẩm sở hữu Dockerfile của service mình. Nguyên tắc: dùng
image mới nhất để luôn có bản vá, để mỗi team tự chọn image nền cho nhanh, và chỉ chặn khi có lỗ hổng nghiêm trọng thật sự
đã bị khai thác ngoài thực tế. Mọi ngoại lệ trao đổi qua Slack của team bảo mật.

## 2. Image nền được duyệt

| Image | Digest | Dùng cho | Lý do |
| --- | --- | --- | --- |
| python:latest | luôn lấy bản mới | Service Python | Luôn có bản vá mới nhất |
| node:22-alpine | không cần | Frontend build | Nhỏ |
| gcr.io/distroless/python3-debian13:nonroot | sha256:1c32c3720dc4c7f0c7dbe998737f32c200add6511eca7cec705008be488b87d6 | Job Python | Không shell |

## 3. Quy tắc Dockerfile

- Nên dùng USER không phải root khi tiện.
- HEALTHCHECK tuỳ team.
- Có thể dùng multi-stage nếu image quá lớn.
- Được dùng tag latest cho image nền.
- Cài gói bằng apt-get khi cần.
- Không ghi mật khẩu vào Dockerfile.
- Dùng .dockerignore.
- Exec form cho CMD.

## 4. Quét lỗ hổng và thời hạn vá

| Mức độ | Có bản vá | Thời hạn | Gate |
| --- | --- | --- | --- |
| CRITICAL | Có | 30 ngày | Chặn |
| HIGH | Có | 90 ngày | Cảnh báo |
| MEDIUM | Có | 180 ngày | Báo cáo |
| LOW | Không | Không đặt | Báo cáo |

## 5. Ngoại lệ

- Ngoại lệ xin qua Slack, team bảo mật duyệt.
- Ghi lý do ngắn gọn.
- Ngoại lệ có thể không hết hạn nếu lỗ hổng khó vá.
- Danh sách ngoại lệ lưu trong wiki.

## 6. Registry, tag và chuỗi cung ứng

- Đẩy image lên registry chung với tag latest và tag commit.
- Deploy theo digest khi có thể.
- SBOM tạo khi được yêu cầu.
- Ký image bằng cosign là tuỳ chọn.

## 7. Runtime

- Chạy với read_only khi app cho phép.
- cap_drop ALL cho service mới.
- Giới hạn RAM theo kinh nghiệm.
- Không mount docker.sock trừ khi cần.

## 8. Triển khai, đo lường và rủi ro

- Thông báo chính sách qua email.
- Đo số image vi phạm mỗi quý.
- Rủi ro: team phản đối.
- Rủi ro: chậm release.
