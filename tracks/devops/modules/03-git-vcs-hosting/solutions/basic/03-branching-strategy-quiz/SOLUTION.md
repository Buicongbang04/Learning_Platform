# Lời giải: chọn branching strategy và cách merge theo tình huống

| Câu | Đáp án | Ràng buộc quyết định |
| --- | --- | --- |
| `saas-daily-deploy` | b. Trunk-based | Một bản production, CI nhanh, đã có feature flag |
| `mobile-store-release` | c. Cắt `release/x.y`, sửa trên main rồi cherry-pick | Bên ngoài (store) quyết định thời điểm, main không được dừng |
| `on-prem-versions` | a. Nhánh bảo trì cho từng dòng phiên bản, backport | Hai phiên bản đang chạy ở khách cùng lúc |
| `dora-lead-time` | d. PR nhỏ vào main hằng ngày, deploy từ main | Thời gian chờ nằm ở nhánh, không ở code |
| `hotfix-continuous-deploy` | b. Rollback rồi sửa qua PR bình thường | Khôi phục dịch vụ trước, pipeline vẫn là đường duy nhất lên prod |
| `merge-method` | c. Squash merge | Changelog theo tiêu đề PR, bisect cần mỗi commit trên main đều chạy được |
| `long-migration` | c. Branch by abstraction sau feature flag | Việc dài nhưng không được tạo nhánh dài |
| `env-branches` | b. Image prod khác image đã test, nhánh lệch nhau | Build once, promote the same artifact |
| `gitflow-fit` | a. Firmware phát hành theo quý, QA dài | Phát hành theo phiên bản, có giai đoạn ổn định hoá |
| `trunk-prerequisites` | a, b, d | CI, flag, PR nhỏ là điều kiện; freeze và develop là thứ trunk-based bỏ đi |

## Giải thích từng câu

### `saas-daily-deploy`: trunk-based

Một bản production nghĩa là không có phiên bản cũ nào phải sửa, nên nhánh release không có việc gì làm. CI 8 phút và
feature flag là hai điều kiện để merge vào `main` nhiều lần mỗi ngày mà vẫn an toàn. GitFlow (a) và release branch mỗi
tuần (c) thêm một hàng chờ giữa merge và production: đúng khi phát hành theo lịch, sai khi muốn deploy liên tục. Nhánh
feature dài (d) là cách tệ nhất cho DORA: lead time tính bằng sprint, và merge cuối sprint là lúc xung đột dồn lại.

### `mobile-store-release`: release branch cắt từ main

Bản đang chờ duyệt cần đứng yên, `main` thì không. Cắt `release/x.y` lúc gửi duyệt, sửa lỗi **trên main trước** rồi
cherry-pick sang nhánh release, để bản sau không mất bản sửa. Code freeze (a) chặn cả team 1–3 ngày mỗi lần phát hành.
GitFlow đầy đủ (b) giải quyết được, nhưng thêm nhánh `develop` không cần thiết cho team đã trunk-based: chỉ cần nhánh
release, không cần đổi cả mô hình. Commit lên tag (d) không làm được: tag không phải nhánh, "commit lên tag" là commit
ở trạng thái detached rồi đặt lại tag, tức viết lại một tag đã công bố.

### `on-prem-versions`: nhánh bảo trì và backport

Hai dòng phiên bản cùng sống thì cần hai nhánh sống lâu, mỗi nhánh có pipeline phát hành bản vá. Sửa trên `main` trước
rồi backport (cherry-pick `-x` để ghi lại nguồn) đảm bảo bản sửa không bị mất ở phiên bản sau. Fork thành hai repo (b)
làm mỗi bản vá thành hai lần sửa tay, sớm muộn sẽ lệch. Ép khách nâng cấp (c) không phải lựa chọn với bản vá bảo mật có
hạn 48 giờ. GitFlow chuẩn (d) giả định chỉ một dòng phiên bản trên `master`, không có chỗ cho 3.x.

### `dora-lead-time`: PR nhỏ vào main hằng ngày

Lead time for changes đo từ commit tới production. Nếu code nằm chờ trên `develop` và `release/*`, chỉ rút ngắn chỗ chờ
đó mới cải thiện được nhiều. Thêm QA thủ công (a) hay thêm người review (b) làm lead time dài thêm; nghiên cứu DORA cho
thấy duyệt nặng ở bên ngoài team không làm giảm change failure rate. Squash merge (c) chỉ đổi hình dạng lịch sử.

### `hotfix-continuous-deploy`: rollback rồi sửa qua main

30% request lỗi thì khôi phục dịch vụ trước: deploy lại artifact trước đó (hoặc tắt flag nếu thay đổi nằm sau flag).
Sau đó sửa qua PR bình thường, vì pipeline 15 phút đủ nhanh và là đường lên production đã được kiểm. Hotfix branch từ
tag cũ (a) tạo một bản production chưa từng đi qua `main`, dễ quên merge lại; đó là cách của GitFlow, hợp khi `main` có
code chưa sẵn sàng phát hành. Tắt required checks (c) đổi một sự cố thành hai. Giữ nguyên trong lúc viết bản sửa đầy
đủ (d) kéo dài thời gian khôi phục (MTTR / failed deployment recovery time).

### `merge-method`: squash merge

Squash biến mỗi PR thành một commit trên `main`, message là tiêu đề PR (dùng được cho changelog), và mỗi commit trên
`main` đều đã qua CI, nên bisect không vấp phải commit `wip` không build được. Merge commit (a) đưa mọi commit `wip` vào lịch sử
qua parent thứ hai của merge commit; `git bisect --first-parent` giảm được vấn đề, nhưng changelog vẫn phải đọc merge
commit. Rebase and merge (b) đưa từng commit `wip` lên `main`. Push thẳng `main` (d) bỏ qua review và CI. Squash có
giá: mất lịch sử chi tiết của nhánh, nên PR cần nhỏ và mô tả rõ.

### `long-migration`: branch by abstraction

Đặt một lớp trừu tượng (interface `PaymentGateway`) trước code cũ, viết bản mới phía sau nó từng phần, merge vào
`main` hằng ngày với flag tắt, bật dần theo phần trăm traffic, cuối cùng xoá bản cũ và flag. Nhánh 6 tuần rebase hằng
tuần (a) vẫn là một nhánh dài: xung đột tăng dần và lần merge cuối là một lần deploy lớn rủi ro. Nhánh `develop` tạm (b)
và fork (d) cùng vấn đề, thêm việc PR lớn không ai review kỹ được.

### `env-branches`: artifact khác nhau, nhánh lệch nhau

Mỗi nhánh tự build nghĩa là image chạy ở prod chưa bao giờ được test. Merge qua lại giữa nhánh sống lâu cũng tạo khác
biệt (một hotfix vào thẳng `prod`, quên đưa về `dev`). Cách đúng: build một lần từ một commit trên `main`, promote cùng
artifact (cùng digest image) qua các môi trường, khác biệt giữa môi trường nằm ở cấu hình. Module 07 và 12 làm điều này.
Git không cấm merge qua lại (a), GitHub không tính phí theo số nhánh (c), còn lịch sử khó đọc (d) là vấn đề nhỏ.

### `gitflow-fit`: firmware phát hành theo quý

GitFlow được thiết kế (2010) cho phần mềm phát hành theo phiên bản, có giai đoạn ổn định hoá trên `release/*` trong
khi `develop` nhận việc mới. Firmware, phần mềm desktop đóng gói, thiết bị y tế cần chứng nhận là các ví dụ còn hợp.
Chính tác giả GitFlow đã thêm ghi chú năm 2020 khuyên web app deploy liên tục nên dùng mô hình đơn giản hơn: đó là b và
d. Startup làm prototype (c) chỉ cần `main` và PR.

### `trunk-prerequisites`: a, b, d

Trunk-based an toàn khi mỗi thay đổi nhỏ được kiểm tự động trước khi vào `main` (a), việc dở dang không lộ ra người dùng
(b), và PR không nằm chờ (d). Code freeze (c) và nhánh `develop` (e) là các cơ chế của mô hình phát hành theo lịch, thứ
trunk-based thay bằng CI và flag.
