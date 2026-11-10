---
title: Chính sách container image cho cả tổ chức Olist
level: advanced
services: []
files:
  - path: starter/POLICY.md
    note: Khung chính sách, điền mọi TODO
  - path: tests/test_policy.py
    note: Không sửa; kiểm khung và vài quyết định đo được, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/06-containers/exercises/advanced/01-org-image-policy -q
---

## Mục tiêu

Viết một chính sách image mà 12 team dùng được thật: đủ chặt để bảo mật ký duyệt, đủ thực tế để team không lách, có thời hạn
vá đo được, có đường ngoại lệ rõ ràng, và có kế hoạch triển khai không làm đứng mọi pipeline vào ngày đầu.

## Đề bài

Olist có 12 team sản phẩm, khoảng 60 service và 25 job định kỳ, viết bằng Python, Node.js và Go; chạy trên Kubernetes, build
trên GitHub Actions, image đẩy lên một registry chung. Kiểm toán vừa phát hiện:

- 23 image dùng tag `latest` hoặc không tag cho image nền; 9 image nền khác nhau cho cùng ngôn ngữ.
- 70% container chạy bằng root; 4 service mount `/var/run/docker.sock`.
- Trung bình 41 lỗ hổng HIGH có bản vá trên mỗi image production; lỗ hổng cũ nhất có bản vá từ 14 tháng trước.
- Một image production chứa tệp `.env` có khoá API của cổng thanh toán.
- Không ai biết image nào đang chạy được build từ commit nào.

CTO giao bạn (platform team, 3 người) viết chính sách image áp dụng trong 2 quý. Viết `starter/POLICY.md`, giữ các heading `## 1.`
tới `## 8.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Phạm vi và nguyên tắc | Ít nhất 300 ký tự (không tính bảng và khối code) |
| 2. Image nền được duyệt | Bảng ít nhất 3 dòng đủ 4 cột (`Image`, `Digest`, `Dùng cho`, `Lý do`); mỗi image ghim tag cụ thể (không `latest`), cột Digest có `sha256:` cộng 64 ký tự hex |
| 3. Quy tắc Dockerfile | Ít nhất 8 gạch đầu dòng; có nói tới USER/non-root, HEALTHCHECK, multi-stage, `latest` |
| 4. Quét lỗ hổng và thời hạn vá | Bảng ít nhất 4 dòng đủ 4 cột (`Mức độ`, `Có bản vá`, `Thời hạn`, `Gate`); dòng CRITICAL có bản vá (cột 2 bắt đầu bằng "Có") có thời hạn tối đa 7 ngày, dòng HIGH có bản vá tối đa 30 ngày, cả hai có chữ "chặn" ở cột Gate |
| 5. Ngoại lệ | Ít nhất 4 gạch đầu dòng; có nói tới hết hạn (`expired_at`), người duyệt, lý do (`statement`) |
| 6. Registry, tag và chuỗi cung ứng | Ít nhất 4 gạch đầu dòng; có nói tới digest, SBOM, ký image |
| 7. Runtime | Ít nhất 4 gạch đầu dòng; có nói tới read-only rootfs, `no-new-privileges`, capability |
| 8. Triển khai, đo lường và rủi ro | Ít nhất 4 gạch đầu dòng |

Số ngày trong phần 4 lấy từ cột Thời hạn (số lớn nhất trong ô). Test chỉ kiểm khung và các quyết định trên; hai test khác đưa
khung trống và một chính sách yếu (image `latest`, thiếu digest, CRITICAL vá trong 30 ngày, HIGH chỉ cảnh báo, runtime không có
`no-new-privileges`) vào cùng phép kiểm và đòi bị bắt. Nội dung chấm bằng rubric trong
`solutions/advanced/01-org-image-policy/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/06-containers/exercises/advanced/01-org-image-policy -q` pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi quy tắc có cách kiểm tự động (công cụ, bước CI, admission policy) hoặc ghi rõ vì sao chỉ kiểm bằng review.
- Kế hoạch triển khai trả lời được: tuần đầu tiên gate chặn gì, và 41 lỗ hổng HIGH tồn đọng mỗi image được xử lý thế nào.

## Gợi ý

### Gợi ý 1

Một chính sách chặn mọi thứ từ ngày đầu sẽ bị tắt vào ngày thứ hai. Tách "chặn image mới" khỏi "dọn image cũ", chạy chế độ chỉ
báo cáo trước, rồi siết dần theo mốc có ngày. Đo được thì quản được: số image vi phạm theo team, tuổi của lỗ hổng có bản vá.

### Gợi ý 2

Mỗi quy tắc nên có chỗ thực thi: hadolint hoặc conftest trên Dockerfile, trivy trong CI, Kyverno hoặc Gatekeeper ở admission
của Kubernetes (chặn image không theo digest, container root, `privileged`), cosign verify trước khi deploy. Quy tắc không có
chỗ thực thi là khuyến nghị.
