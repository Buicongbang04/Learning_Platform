---
title: ADR chọn nền tảng CI/CD và artifact repository sau sáp nhập
level: advanced
services: []
files:
  - path: starter/ADR.md
    note: Khung ADR, điền mọi TODO
  - path: tests/test_adr.py
    note: Không sửa; kiểm khung và tính nhất quán của quyết định, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/07-cicd-artifacts/exercises/advanced/02-ci-platform-adr -q
---

## Mục tiêu

Ra một quyết định công cụ mà người khác kiểm lại được: tiêu chí và trọng số viết ra trước, phương án so trên cùng thước đo, quyết
định khớp với điểm, cái giá được nói thẳng, kế hoạch chuyển đổi chạy song song và quay lại được, và điều kiện nào thì xem lại.

## Đề bài

Olist vừa mua Lojas Rápidas, một chuỗi bán lẻ có đội kỹ thuật 25 người. Ban lãnh đạo muốn một nền tảng CI/CD và một artifact
repository chung trước cuối năm sau. Hiện trạng:

| | Olist | Lojas Rápidas |
| --- | --- | --- |
| CI/CD | GitHub Actions (runner của GitHub), khoảng 60 repo | Jenkins 2.4xx tự host trên 3 VM, 40 pipeline Groovy, shared library tự viết, 70 plugin (12 plugin đã ngừng bảo trì) |
| Artifact | GHCR cho image; gói Python và npm nội bộ chưa có chỗ, đang build từ git | Nexus Repository OSS: proxy Maven Central, npm, PyPI; hosted Maven và Docker |
| Ngôn ngữ | Python, Node.js, Go | Java (Maven), Node.js, một ít .NET |
| Ràng buộc | | Hợp đồng với một ngân hàng yêu cầu artifact của module thanh toán lưu ở Brazil và có log truy cập 1 năm |

Platform team chung có 4 người. Ngân sách công cụ tối đa 120.000 USD mỗi năm. Hai sự cố gần đây của Lojas: Jenkins controller hết
đĩa làm dừng mọi pipeline 6 giờ; một plugin Jenkins có lỗ hổng bị khai thác để đọc credential.

Viết `starter/ADR.md` theo khung có sẵn, giữ các heading `## 1.` tới `## 8.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh | Ít nhất 300 ký tự (không tính bảng và khối code) |
| 2. Tiêu chí và trọng số | Bảng ít nhất 5 dòng đủ 3 cột (`Tiêu chí`, `Trọng số`, `Cách đo`); trọng số là số, tổng đúng 100 |
| 3. Phương án CI/CD | Bảng đủ 5 cột (`Phương án`, `Điểm mạnh`, `Điểm yếu`, `Chi phí ước tính`, `Điểm`); ít nhất 4 phương án có tên chứa một trong: GitHub Actions, GitLab CI, Jenkins, CircleCI, TeamCity, Buildkite, Azure Pipelines, Tekton; cột Điểm là số; không hai phương án cùng điểm cao nhất |
| 4. Phương án artifact repository | Như phần 3 với ít nhất 3 phương án trong: Artifactory, Nexus, Cloudsmith, GHCR, GitHub Packages, Harbor, ECR, Artifact Registry |
| 5. Quyết định | Văn bản phải nhắc đúng tên phương án điểm cao nhất của phần 3 và của phần 4 (đúng như ô `Phương án`) |
| 6. Hệ quả | Ít nhất 4 gạch đầu dòng; có nói tới lock-in (hay "phụ thuộc nhà cung cấp") và chi phí |
| 7. Kế hoạch chuyển đổi | Ít nhất 4 gạch đầu dòng; có mốc thời gian dạng `<số> tuần` hay `<số> tháng`; có chạy song song và cách quay lại (rollback) |
| 8. Điều kiện xem lại quyết định | Ít nhất 2 gạch đầu dòng |

Điểm ở phần 3 và 4 tên theo ý bạn (thang 10, 100, tổng có trọng số), miễn là số và quyết định khớp điểm. Hai test khác đưa khung
trống và một ADR yếu (trọng số cộng ra 120, chỉ 2 phương án CI, quyết định chọn phương án điểm thấp hơn, kế hoạch không mốc thời
gian và không chạy song song, không nhắc lock-in) vào cùng phép kiểm và đòi bị bắt. Nội dung chấm bằng rubric trong
`solutions/advanced/02-ci-platform-adr/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/07-cicd-artifacts/exercises/advanced/02-ci-platform-adr -q` pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Ràng buộc artifact thanh toán ở Brazil có lời giải cụ thể (vùng lưu trữ, log truy cập), không bị bỏ qua vì phương án thắng
  không đáp ứng.
- Một kỹ sư Lojas đọc ADR hiểu được pipeline Groovy của họ sẽ đi đâu, khi nào, và ai giúp.

## Gợi ý

### Gợi ý 1

Chọn trọng số **trước** khi chấm phương án, và nói vì sao (ví dụ "vận hành ít" nặng vì platform team chỉ 4 người, sự cố đĩa của
Jenkins là chứng cứ). Một tiêu chí không đo được thì viết cách sẽ đo: số giờ vận hành mỗi tháng, số plugin cần thay, chi phí phút
runner theo số build thật của hai bên.

### Gợi ý 2

CI/CD và artifact repository không buộc phải cùng nhà cung cấp. Một kế hoạch chuyển đổi tốt chạy hai hệ thống song song cho một
nhóm pipeline thử, có tiêu chí "xong" cho từng nhóm, giữ hệ thống cũ chỉ đọc một thời gian để quay lại, và có ngày tắt hẳn.
