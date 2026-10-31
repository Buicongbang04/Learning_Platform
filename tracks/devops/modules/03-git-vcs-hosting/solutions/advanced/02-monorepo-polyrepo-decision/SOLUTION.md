# Lời giải: monorepo hay polyrepo cho Olist Shop

Bài Advanced không có một đáp án duy nhất. Dưới đây là hướng làm, rubric, và một ADR mẫu đã chạy qua test (đặt vào
`starter/DECISION.md` thì `test_decision_document` pass).

## Hướng làm

1. **Ràng buộc cứng loại phương án trước.** "Contractor không được đọc code thanh toán" loại monorepo toàn bộ trên
   GitHub, GitLab và Bitbucket: cả ba cấp quyền đọc theo repo. CODEOWNERS chỉ kiểm ai **duyệt**, không kiểm ai **đọc**.
   Muốn giữ monorepo toàn bộ thì phải tách code thanh toán ra, hoặc đổi nền tảng (Perforce, Gerrit với quyền theo
   đường dẫn), cả hai đều đắt.
2. **Gắn nỗi đau với nguyên nhân.** Thay đổi xuyên repo và lệch phiên bản thư viện là hai triệu chứng của việc đặt
   ranh giới repo không khớp ranh giới thay đổi. Những thứ hay đổi cùng nhau nên nằm cùng một repo. CI lệch nhau là vấn
   đề khác, giải được ở cả hai hướng bằng reusable workflow.
3. **Tính chi phí công cụ.** Monorepo lớn cần CI theo đường dẫn thay đổi, cache build, có khi cần build system hiểu đồ
   thị phụ thuộc (Bazel, Pants, Nx, Turborepo). Với 25 người và vài service, lọc `paths` trong GitHub Actions thường
   đủ; Bazel là quá tay khi không ai vận hành được.
4. **Chuyển đổi giữ lịch sử và không dừng team**: từng repo một, lịch sử được giữ bằng `git filter-repo`, repo cũ chỉ
   đọc. Lịch sử có tệp lớn: chuyển sang LFS (`git lfs migrate import`) hoặc bỏ khỏi lịch sử trước khi gộp.

## So sánh để tham khảo

| Khía cạnh | Monorepo | Polyrepo |
| --- | --- | --- |
| Thay đổi xuyên service | Một PR nguyên tử, refactor toàn cục dễ | Nhiều PR, phải phối hợp thứ tự, cần hợp đồng có phiên bản |
| Phụ thuộc nội bộ | Dùng mã nguồn trực tiếp, một phiên bản | Gói có phiên bản, lệch phiên bản là chuyện thường |
| Quyền truy cập | Một quyền đọc cho cả repo | Theo repo, chi tiết |
| CI | Cần chạy theo phần bị ảnh hưởng, cache; nếu không thì chậm dần | Đơn giản từng repo, nhưng cấu hình nhân bản |
| Công cụ Git | Clone lớn: partial clone, sparse checkout, `scalar` | Bình thường |
| Ai dùng | Google (Piper), Meta, Uber (Go), nhiều startup dùng Nx/Turborepo | Amazon, Netflix, phần lớn tổ chức microservice |

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Bối cảnh có số liệu và ràng buộc | 10 | Nỗi đau có số (3 ngày, 3 phiên bản, 9 bản CI), ràng buộc cứng tách khỏi mong muốn |
| Phương án thực tế | 15 | Ít nhất một phương án lai hoặc phương án "giữ polyrepo nhưng sửa triệu chứng"; ô bảng gắn với tình huống |
| Quyết định tôn trọng ràng buộc quyền | 20 | Nhận ra CODEOWNERS không giới hạn quyền đọc; không đặt code thanh toán chung repo với contractor |
| Tác động CI/CD và CODEOWNERS | 15 | CI theo đường dẫn hoặc build system, ảnh hưởng tới số phút Actions, cách tag và deploy từng service, CODEOWNERS theo thư mục |
| Kế hoạch chuyển đổi | 15 | Từng bước, giữ lịch sử, repo cũ chỉ đọc, xử lý 2 GB ảnh (LFS hoặc để lại), có đo lại sau chuyển |
| Rủi ro | 15 | Rủi ro cụ thể kèm cách giảm (CI bỏ sót test, clone nặng, thay đổi phá vỡ lan nhanh) |
| Tín hiệu xem lại | 10 | Tín hiệu đo được, có ngưỡng |

Trừ điểm: chọn monorepo toàn bộ mà không giải quyết ràng buộc contractor (−20); đề xuất Bazel mà không nói ai vận hành
(−5); kế hoạch "gộp tất cả trong một cuối tuần" (−10).

## ADR mẫu

`````markdown
# ADR: Monorepo hay polyrepo cho Olist Shop

## 1. Bối cảnh

Olist Shop có 9 repo cho 25 kỹ sư: `api`, `worker`, `web` (Next.js), `mobile-bff`, thư viện `olist-common` phát hành lên
PyPI nội bộ, `dbt`, `infra-tofu`, `helm-charts`, `ci-templates`. Nỗi đau đo được: thêm một trường vào đơn hàng cần 4 PR
ở 4 repo, merge theo thứ tự, trung bình 3 ngày; production đang chạy 3 phiên bản `olist-common` khác nhau; 9 bản sao
workflow CI lệch nhau, hai repo chưa có quét secret. Ràng buộc bắt buộc: contractor làm `web` không được đọc code thanh
toán trong `api`; team data muốn giữ quyền riêng cho `dbt`; ngân sách GitHub Actions không tăng quá 20%; không ai trong
team từng vận hành Bazel; lịch sử `web` có 2 GB ảnh thiết kế.

## 2. Phương án

| Phương án | Thay đổi xuyên service | Quyền truy cập | CI và build | Công cụ cần thêm | Điểm (1-5) |
| --- | --- | --- | --- | --- | --- |
| Monorepo toàn bộ | Một PR nguyên tử cho api, worker, olist-common | GitHub không giới hạn quyền đọc theo thư mục: contractor thấy code thanh toán | Cần CI theo đường dẫn thay đổi, nếu không mỗi PR chạy cả 9 bộ test | Lọc theo path, có thể cần Pants hoặc Nx; LFS cho ảnh của web | 2 |
| Polyrepo như hiện tại, chuẩn hoá bằng reusable workflow và Renovate | Vẫn 4 PR, nhưng Renovate tự mở PR nâng `olist-common` | Quyền theo repo, đã đáp ứng contractor | Reusable workflow trung tâm xoá chuyện lệch CI | Renovate, reusable workflow | 3 |
| Hybrid: monorepo backend (api, worker, mobile-bff, olist-common, helm-charts), giữ riêng web, dbt, infra-tofu | Thay đổi phổ biến nhất (api + worker + common) thành một PR | Contractor chỉ có quyền repo web; data giữ repo dbt | CI theo path trong monorepo backend, reusable workflow cho mọi repo | Lọc theo path trong Actions, CODEOWNERS theo thư mục | 4 |

## 3. Quyết định

Chọn: Hybrid: monorepo backend (api, worker, mobile-bff, olist-common, helm-charts), giữ riêng web, dbt, infra-tofu

Ba nỗi đau lớn nhất đều nằm trong nhóm backend: thay đổi xuyên service, lệch phiên bản `olist-common`, và chart Helm
phải đổi cùng code. Gộp nhóm đó vào một repo làm thay đổi xuyên service thành một PR, và `olist-common` thành mã nguồn
dùng trực tiếp thay vì gói phiên bản. Ràng buộc quyền truy cập loại monorepo toàn bộ: GitHub không giới hạn quyền đọc
theo thư mục, nên `web` phải ở repo riêng. `infra-tofu` có vòng đời khác (plan/apply, quyền cloud) và `dbt` thuộc team
khác, nên giữ riêng. Cái giá chấp nhận: thay đổi chạm cả web và api vẫn cần hai PR, phải giữ hợp đồng API có phiên
bản; CI backend phải học cách chỉ chạy phần bị ảnh hưởng.

## 4. Tác động lên CI/CD, quyền truy cập và CODEOWNERS

- CI: workflow dùng bộ lọc `paths` cho từng service, cộng một job "all" khi `olist-common` đổi; ước tính số phút Actions giảm vì bỏ được job build và publish gói.
- CD: mỗi service vẫn build image riêng, tag theo SHA của commit monorepo; deploy theo service đã đổi.
- Quyền: team backend và payments có write trên monorepo; contractor chỉ có quyền repo web; data giữ repo dbt.
- CODEOWNERS theo thư mục: `/services/api/app/payments/` cho payments và security, `/libs/olist-common/` cho backend và platform.

## 5. Kế hoạch chuyển đổi

1. Chuẩn hoá trước: reusable workflow trung tâm cho mọi repo, bật quét secret ở hai repo còn thiếu.
2. Tạo monorepo backend, đưa `olist-common` vào trước bằng `git filter-repo --to-subdirectory-filter` để giữ lịch sử.
3. Chuyển `worker` rồi `api`, mỗi repo một tuần, đóng băng repo cũ ở chế độ chỉ đọc kèm README trỏ sang repo mới.
4. Chuyển `helm-charts` và `mobile-bff`, bật CI theo path và CODEOWNERS.
5. Đo lại sau 6 tuần: thời gian thay đổi xuyên service, số phút CI, số phiên bản `olist-common` đang chạy.

## 6. Rủi ro và đánh đổi

- CI theo path cấu hình sai sẽ bỏ sót test của service bị ảnh hưởng; giảm bằng job chạy toàn bộ mỗi đêm.
- Clone monorepo nặng hơn; dùng partial clone và sparse checkout cho người chỉ làm một service.
- Mất ranh giới phiên bản của `olist-common` làm thay đổi phá vỡ lan ngay sang mọi service; bù bằng test hợp đồng.

## 7. Khi nào xem lại quyết định

- Thời gian CI trung bình của PR trong monorepo vượt 20 phút dù đã lọc theo path: cân nhắc Pants, Bazel hoặc tách lại.
- GitHub hoặc nền tảng khác cho phép giới hạn quyền đọc theo thư mục, hoặc hợp đồng với contractor kết thúc: xem lại việc gộp web.
`````
