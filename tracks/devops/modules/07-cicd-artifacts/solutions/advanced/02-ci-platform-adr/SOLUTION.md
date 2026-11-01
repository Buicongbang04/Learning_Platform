# Lời giải: ADR chọn nền tảng CI/CD và artifact repository

Không có phương án "đúng" duy nhất: GitHub Actions cộng Nexus Pro, GitHub Actions cộng Artifactory, hay GitLab cho cả hai đều có
thể đạt điểm cao nếu lập luận khớp ràng buộc. Reviewer chấm việc ADR có **kiểm lại được** không: trọng số có lý do, điểm có căn
cứ, quyết định khớp điểm, cái giá được nói thẳng, kế hoạch quay lại được.

## Các quyết định cốt lõi

- **Tách hai câu hỏi.** CI/CD và artifact repository có ràng buộc khác nhau: CI cần hệ sinh thái, ít vận hành; artifact cần đa
  định dạng (Maven, npm, PyPI, Docker, NuGet), proxy cache, vị trí lưu trữ và log truy cập theo hợp đồng.
- **Trọng số đến từ sự cố và con người.** Platform 4 người và sự cố Jenkins hết đĩa làm "công sức vận hành" nặng nhất; lỗ hổng
  plugin làm "bảo mật chuỗi cung ứng" nặng; Olist đã có 60 repo trên GitHub nên chi phí chuyển đổi của bên đó gần 0.
- **CI: GitHub Actions** cho cả hai bên. Bỏ Jenkins tự host (controller là điểm chết, 12 plugin ngừng bảo trì). Job cần chạy gần
  dữ liệu hay cần mạng nội bộ dùng runner tự host tạm thời (Actions Runner Controller trên Kubernetes, runner chỉ sống một job).
- **Artifact: Nexus Repository Pro** tự host ở vùng Brazil (São Paulo) cho mọi định dạng gói và proxy; image vẫn ở GHCR cho
  service thường, image của module thanh toán ở Nexus Docker hosted cùng vùng. Lojas đã quen Nexus, OSS sang Pro là nâng cấp tại
  chỗ, có log truy cập và quản lý vòng đời. Artifactory mạnh hơn nhưng đắt gấp ba ở quy mô này.
- **Chuyển đổi theo sóng, chạy song song.** Pipeline nhỏ trước, pipeline thanh toán sau cùng; mỗi sóng có tiêu chí xong; Jenkins
  chỉ đọc 2 tháng rồi tắt.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Bối cảnh và ràng buộc | 10 | Nêu đủ ràng buộc cứng (Brazil, log 1 năm, ngân sách, 4 người) và sự cố làm căn cứ |
| Tiêu chí và trọng số | 15 | Tiêu chí đo được, trọng số có lý do, viết trước khi chấm |
| So sánh phương án | 20 | Ít nhất 4 CI và 3 artifact, điểm mạnh/yếu cụ thể (không chung chung), chi phí ước tính có cách tính |
| Quyết định | 15 | Khớp điểm, đáp ứng ràng buộc cứng (nếu phương án thắng không đáp ứng, có cách bù cụ thể) |
| Hệ quả | 15 | Nói thẳng cái giá: lock-in, chi phí theo phút runner, đào tạo, thứ mất đi (plugin, shared library), việc vận hành mới |
| Kế hoạch chuyển đổi | 20 | Sóng có mốc, chạy song song, tiêu chí xong, cách quay lại, ngày tắt hệ thống cũ, ai giúp đội Lojas |
| Điều kiện xem lại | 5 | Ngưỡng cụ thể (chi phí, sự cố, thay đổi hợp đồng) khiến quyết định phải mở lại |

Trừ điểm: chọn phương án không đáp ứng ràng buộc Brazil mà không có cách bù (−15); không có kế hoạch quay lại (−10); "big bang"
chuyển mọi pipeline trong một lần (−10).

## ADR mẫu

`````markdown
# ADR-012: Nền tảng CI/CD và artifact repository sau khi sáp nhập Lojas Rápidas

Trạng thái: đề xuất. Người viết: platform team. Ngày: 2026-11-01.

## 1. Bối cảnh

Olist chạy khoảng 60 repo trên GitHub Actions với runner của GitHub và đẩy image lên GHCR; gói Python và npm nội bộ chưa có
registry nên đang cài thẳng từ git. Lojas Rápidas chạy 40 pipeline Groovy trên Jenkins tự host (3 VM, 70 plugin, 12 plugin đã ngừng
bảo trì) và Nexus OSS làm proxy Maven, npm, PyPI cộng hosted Maven và Docker. Hai sự cố trong 6 tháng: controller Jenkins hết đĩa
làm dừng mọi pipeline 6 giờ; một plugin có lỗ hổng bị khai thác để đọc credential. Hợp đồng với ngân hàng đối tác yêu cầu artifact
của module thanh toán lưu ở Brazil và có log truy cập 1 năm. Platform team chung có 4 người, ngân sách công cụ tối đa 120.000 USD
mỗi năm, hạn hợp nhất là cuối năm sau.

## 2. Tiêu chí và trọng số

| Tiêu chí | Trọng số | Cách đo |
| --- | --- | --- |
| Công sức vận hành | 25 | Giờ platform team mỗi tháng để giữ hệ thống chạy, ước từ sự cố và việc nâng cấp 6 tháng qua |
| Bảo mật chuỗi cung ứng | 20 | OIDC, token ngắn hạn, cô lập job, ghim action hoặc plugin, log kiểm toán |
| Đáp ứng ràng buộc dữ liệu | 20 | Lưu artifact thanh toán ở Brazil, log truy cập 1 năm |
| Chi phí năm | 15 | USD mỗi năm theo số build và dung lượng thực tế của hai bên |
| Công sức chuyển đổi | 20 | Tuần kỹ sư để chuyển 40 pipeline Jenkins và đưa gói nội bộ của Olist vào registry |

## 3. Phương án CI/CD

| Phương án | Điểm mạnh | Điểm yếu | Chi phí ước tính | Điểm |
| --- | --- | --- | --- | --- |
| GitHub Actions | Olist đã dùng; OIDC tới cloud; runner sống một job; hệ sinh thái action lớn | Lojas phải viết lại 40 pipeline; action bên thứ ba cần ghim SHA | 45.000 USD/năm (phút runner và gói Enterprise) | 82 |
| GitLab CI | CI và registry trong một sản phẩm; pipeline YAML mạnh | Phải chuyển cả 60 repo của Olist sang GitLab | 70.000 USD/năm (Premium, 120 người) | 61 |
| Jenkins | Lojas đã quen; linh hoạt vô hạn | Controller là điểm chết; plugin là bề mặt tấn công; tốn người vận hành nhất | 30.000 USD/năm hạ tầng cộng 0,5 người vận hành | 44 |
| CircleCI | Nhanh, cache tốt, orb | Thêm một nhà cung cấp; Olist vẫn phải chuyển khỏi Actions | 55.000 USD/năm | 55 |
| TeamCity | Mạnh với Java và .NET, Kotlin DSL | Ít người biết ở Olist; tự host hoặc Cloud trả theo agent | 40.000 USD/năm | 52 |

## 4. Phương án artifact repository

| Phương án | Điểm mạnh | Điểm yếu | Chi phí ước tính | Điểm |
| --- | --- | --- | --- | --- |
| Nexus Repository Pro | Lojas đã dùng bản OSS; đa định dạng; tự host ở São Paulo; log truy cập | Phải vận hành (backup, nâng cấp) | 28.000 USD/năm cộng hạ tầng 6.000 USD | 80 |
| Artifactory | Đa định dạng tốt nhất; replication; Xray quét | Đắt; vận hành phức tạp nếu tự host | 90.000 USD/năm | 68 |
| Cloudsmith | SaaS, không vận hành; đa định dạng | Vùng lưu trữ ở Brazil cần gói Enterprise, chưa xác nhận | 50.000 USD/năm | 62 |
| GHCR | Gắn với GitHub, token ngắn hạn | Không có Maven proxy, PyPI; không chọn được vùng | Trong gói GitHub | 50 |

## 5. Quyết định

Chọn GitHub Actions làm nền tảng CI/CD chung và Nexus Repository Pro tự host ở vùng São Paulo làm artifact repository cho mọi
định dạng gói và proxy. Image của service thường tiếp tục ở GHCR; image và gói của module thanh toán chỉ ở Nexus Repository Pro để
đáp ứng yêu cầu lưu trữ ở Brazil và log truy cập 1 năm.

## 6. Hệ quả

- Tăng lock-in vào GitHub: workflow, OIDC, environment đều là khái niệm của GitHub; giảm bằng cách giữ logic build trong script
  và Makefile chạy được ở mọi CI.
- Chi phí phút runner tăng khi 40 pipeline của Lojas chuyển sang; theo dõi hằng tháng, dùng runner tự host trên Kubernetes cho job
  nặng nếu vượt 60.000 USD/năm.
- Đội Lojas mất shared library Groovy và một số plugin; platform team viết reusable workflow tương đương.
- Platform team nhận thêm việc vận hành Nexus Pro (backup, nâng cấp, dung lượng), bù lại bỏ 3 VM Jenkins.
- Gói Python và npm nội bộ của Olist có chỗ phát hành đúng nghĩa, có phiên bản và proxy cache.

## 7. Kế hoạch chuyển đổi

- Tháng 1: dựng Nexus Pro ở São Paulo, nâng cấp dữ liệu từ Nexus OSS, chạy song song với bản OSS ở chế độ chỉ đọc.
- Tháng 2-3: sóng 1, 10 pipeline nhỏ nhất của Lojas sang GitHub Actions, chạy song song với Jenkins 2 tuần, so kết quả build.
- Tháng 4-6: sóng 2 và 3, 25 pipeline còn lại trừ thanh toán; mỗi sóng xong khi 2 tuần không có build nào phải quay lại Jenkins.
- Tháng 7: sóng cuối, 5 pipeline thanh toán, có người của đội thanh toán và security duyệt.
- Cách quay lại: Jenkins giữ chỉ đọc và vẫn chạy được 2 tháng sau sóng cuối; pipeline lỗi có thể chạy lại trên Jenkins trong ngày.
- Tháng 9: tắt Jenkins và Nexus OSS, lưu cấu hình và log 1 năm.

## 8. Điều kiện xem lại quyết định

- Chi phí GitHub Actions vượt 60.000 USD/năm trong hai quý liên tiếp.
- Ngân hàng đối tác đổi yêu cầu lưu trữ, hoặc GitHub có vùng lưu trữ ở Brazil cho artifact.
- Nexus Pro gây hơn 2 sự cố dừng build mỗi quý.
`````
