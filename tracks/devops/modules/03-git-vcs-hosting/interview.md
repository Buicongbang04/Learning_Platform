# Câu hỏi phỏng vấn: Git & VCS hosting

## Git lưu dữ liệu thế nào? Vì sao rebase làm đổi SHA của mọi commit phía sau?

Git là kho content-addressed với bốn loại object: blob (nội dung tệp), tree (thư mục: tên, mode, sha của blob và tree
con), commit (sha của tree gốc, sha của parent, author, committer, message) và annotated tag. Tên mỗi object là hash
của nội dung. Nhánh và tag chỉ là ref, một con trỏ tới sha.

Commit chứa sha của parent, nên đổi bất cứ thứ gì ở một commit (nội dung, message, parent, ngày) cho ra sha mới, và
mọi commit sau nó phải tạo lại vì parent của chúng đã đổi. Rebase áp lại các thay đổi lên một parent mới, nên mọi
commit được rebase là commit mới. Hệ quả vận hành: người khác đang dựa vào commit cũ phải điều chỉnh, chữ ký trên
commit cũ không còn, và CI đã chạy trên sha cũ không áp dụng cho sha mới.

## Merge commit, squash hay rebase khi merge PR: team bạn chọn gì?

Phụ thuộc vào thứ team cần từ lịch sử `main`:

- **Squash** khi PR nhỏ và team muốn mỗi commit trên `main` là một thay đổi đã qua CI, message là tiêu đề PR (dùng cho
  changelog, Conventional Commits), bisect không vấp commit `wip`. Cái giá: mất lịch sử chi tiết của nhánh, và nhánh
  chồng lên nhánh khác phải rebase sau khi nhánh dưới được squash.
- **Merge commit** khi commit của nhánh có ý nghĩa riêng và cần truy vết PR nào mang commit nào; bisect dùng
  `--first-parent`. Cũng là cách đúng để đưa nhánh release về `main`.
- **Rebase and merge** khi team có kỷ luật commit nguyên tử, mỗi commit tự build được.

Mặc định của tôi cho team sản phẩm là squash cộng ruleset "linear history", tiêu đề PR kiểm theo Conventional Commits
trong CI, và merge queue khi repo bận.

## Trunk-based hay GitFlow? Liên hệ với DORA metrics thế nào?

Câu hỏi quyết định là có bao nhiêu phiên bản đang chạy và ai quyết định lúc phát hành. Dịch vụ web một bản production,
deploy liên tục: trunk-based, nhánh sống dưới một ngày, việc dở dang giấu sau feature flag. Phần mềm nhiều phiên bản
cùng sống (app qua store, bản on-prem, SDK): trunk-based cộng nhánh release, sửa trên `main` rồi cherry-pick. GitFlow
chỉ còn hợp với phát hành theo lịch có giai đoạn ổn định hoá dài, như firmware.

Với DORA: lead time for changes gồm cả thời gian code nằm chờ trên nhánh, nên nhánh dài là lead time dài; deployment
frequency bị chặn bởi tần suất có `main` phát hành được; merge lớn hiếm hoi làm tăng change failure rate; và hotfix đi
đường riêng làm khôi phục chậm và rủi ro. Nghiên cứu DORA liệt kê trunk-based development (ít hơn ba nhánh hoạt động,
merge ít nhất mỗi ngày, không code freeze) là một capability dự báo hiệu suất cao. Điều kiện đi kèm: CI nhanh, test tin
được, review trong ngày.

## Đồng nghiệp chạy `git reset --hard` nhầm rồi commit thêm, và xoá luôn một nhánh chưa push. Bạn cứu thế nào?

Đầu tiên là không làm gì phá thêm: không `gc`, không clone lại. Rồi đọc reflog trên **chính máy đó**:

- `git reflog show main`: tìm mục `reset: moving to ...`, giá trị trước mục đó (mục liền sau trong danh sách) là tip
  đã mất. Không dùng `main@{1}` một cách máy móc: đã có commit mới thì `main@{1}` là kết quả của reset.
- Nhánh đã xoá: reflog của nhánh mất theo nhánh, nhưng reflog của `HEAD` có `checkout: moving from <nhánh> to ...`;
  `HEAD` ngay trước mục đó là tip của nhánh.
- Tạo nhánh cứu hộ bằng `git branch rescue/main <sha>`, không checkout hay reset, để không đụng tới việc đang dở.

Giới hạn: reflog chỉ có trên máy đã làm thao tác, mục cho commit không reachable hết hạn sau 30 ngày, object không
reachable bị `gc` xoá sau 2 tuần kể từ khi hết được reflog giữ. Mất reflog thì còn `git fsck --lost-found`, remote,
`refs/pull/*`, CI cache, máy đồng nghiệp. Phòng ngừa: push nhánh sớm, ruleset chặn force-push trên `main`.

## `--force`, `--force-with-lease` và `--force-if-includes` khác nhau thế nào?

`--force` ghi đè nhánh trên server vô điều kiện. `--force-with-lease` chỉ ghi đè khi nhánh trên server còn bằng giá trị
bạn kỳ vọng; không kèm giá trị thì kỳ vọng là `origin/<nhánh>` **hiện tại** của bạn. Bẫy: `git fetch` (hay IDE tự fetch
nền) đã cập nhật `origin/<nhánh>` thành commit của đồng nghiệp, lease khớp, và push vẫn ghi đè họ.

Cách an toàn: `--force-with-lease=<nhánh>:<sha>` với sha ghi lại trước khi fetch (dùng trong script), hoặc thêm
`--force-if-includes` (Git 2.30+): server tip phải từng nằm trong reflog nhánh local của bạn, tức bạn đã thật sự tích
hợp nó. Cho người dùng tương tác, đặt `push.useForceIfIncludes=true`. Trên nhánh dùng chung thì không force gì cả:
ruleset chặn, và đảo thay đổi bằng `git revert`.

## Sự cố: một AWS access key vừa bị push lên repo public. Bạn làm gì, theo thứ tự?

Coi key là đã lộ ngay lập tức: bot quét GitHub công khai trong vài phút, và xoá commit không xoá được bản đã bị fork,
clone hay cache.

1. **Thu hồi**: deactivate rồi xoá access key trong IAM (hoặc xoay ngay nếu đang dùng ở production, theo thứ tự tạo key
   mới, cập nhật nơi dùng, rồi xoá key cũ). Nếu GitHub đã gửi cảnh báo qua secret scanning partner, AWS có thể đã gắn
   policy cách ly cho user đó.
2. **Đánh giá thiệt hại**: CloudTrail theo access key id từ lúc push tới lúc thu hồi; tìm tài nguyên lạ (EC2 đào coin ở
   region ít dùng, IAM user mới, thay đổi S3 policy), kiểm hoá đơn và Cost Anomaly Detection.
3. **Dọn hậu quả**: xoá tài nguyên kẻ tấn công tạo, xoay các credential khác mà key đó đọc được (secret trong SSM,
   Secrets Manager).
4. **Cập nhật nơi dùng** bằng credential ngắn hạn thay vì access key dài hạn (OIDC từ CI, IAM role, SSO).
5. **Lịch sử Git**: chỉ sau khi đã thu hồi. `git filter-repo --replace-text`, thông báo mọi người clone lại, liên hệ
   GitHub support để xoá cached view và PR ref. Với repo public, bước này giảm lộ thêm chứ không làm key "an toàn lại".
6. **Postmortem không đổ lỗi**: vì sao key dài hạn tồn tại, vì sao nó ở trong code, vì sao hook, push protection và quét
   trong CI không chặn được. Thêm lớp còn thiếu.

Sai lầm hay gặp là làm bước 5 trước bước 1: mất 30 phút viết lại lịch sử trong khi key vẫn còn sống.

## Bạn dùng `git bisect` thế nào? Khi nào bisect khó?

`git bisect start <bad> <good>`, rồi `git bisect run <script>` để chạy tự động. Script trả `0` là good, `1`–`127` (trừ
`125`) là bad, `125` là không kiểm được (build hỏng, thiếu phụ thuộc), `128` trở lên làm bisect dừng. Đọc kết quả từ
`refs/bisect/bad`, luôn `git bisect reset` khi xong, kể cả khi lỗi.

Bisect khó khi: nhiều commit không build được (phải skip nhiều, có khi chỉ ra một khoảng nghi phạm thay vì một commit);
lỗi không tất định (chạy test vài lần, chỉ trả bad khi lặp lại); lịch sử nhiều merge (dùng `--first-parent` để tìm PR
gây lỗi); lỗi phụ thuộc dữ liệu hay môi trường chứ không phụ thuộc code. Script kiểm phải phân loại đúng: trả `1` cho
cả lỗi build lẫn lỗi thật sẽ chỉ sai thủ phạm, và team sẽ revert nhầm commit.

## Hook phía client và phía server khác nhau thế nào? Có nên dựa vào pre-commit hook để chặn secret không?

Hook client (`pre-commit`, `commit-msg`, `pre-push`) chạy trên máy dev, không được clone theo repo, và bỏ qua được bằng
`--no-verify`. Hook server (`pre-receive`, `update`) chạy trên server trước khi nhận ref, người dùng không bỏ qua được,
nhưng chỉ có trên server tự host (GitLab self-managed, GitHub Enterprise Server, Gitea). Trên GitHub.com, phần tương
đương là ruleset, push protection và required checks.

Không dựa vào hook client như một kiểm soát. Hook là tiện ích để người dùng biết sớm; kiểm soát thật là cùng các kiểm
tra đó chạy ở chỗ không bypass được: push protection, job quét secret là required check của PR, quét toàn bộ lịch sử
định kỳ. Dùng framework pre-commit để một tệp cấu hình chạy được cả trên máy lẫn trong CI (`pre-commit run --all-files`),
và ghim phiên bản hook vì đó là code bên thứ ba chạy trên máy mọi người.

## Conventional Commits và semver giúp gì cho release? Có bẫy nào khi tự động hoá?

Message theo `<type>(<scope>)!: <description>` thành dữ liệu máy đọc được: `fix` bump patch, `feat` bump minor, `!`
hoặc footer `BREAKING CHANGE:` bump major. Công cụ như release-please hay semantic-release đọc commit từ tag cuối, quyết
định phiên bản và sinh changelog.

Bẫy: chọn sai tag gốc (`git describe` lấy cả tag pre-release, `git tag | sort` lấy tag chưa merge và sắp xếp chữ đặt
`v1.9.0` sau `v1.10.0`); shallow clone trong CI không có tag; merge commit có message vô nghĩa; giai đoạn `0.x` mà
breaking làm nhảy lên `1.0.0` ngoài ý muốn; message không chuẩn bị bỏ qua lặng lẽ nên bản sửa không vào changelog. Với
squash merge, kiểm tiêu đề PR trong CI là cách ép chuẩn hiệu quả nhất. Cũng hỏi lại: dịch vụ web nội bộ có cần semver
không, hay sha của image là đủ, còn semver dành cho API contract và thư viện?

## Vì sao chọn GitHub (hay GitLab) cho công ty? Bạn so sánh thế nào?

Tôi không chọn theo Git, vì Git như nhau ở mọi nơi. Tôi chọn theo bốn thứ:

- **Tự host hay SaaS**: yêu cầu dữ liệu ở on-prem hoặc mạng kín (ngân hàng, chính phủ) nghiêng về GitLab self-managed
  hoặc GitHub Enterprise Server; còn lại SaaS rẻ hơn về vận hành.
- **CI/CD và hệ sinh thái**: GitHub Actions có marketplace lớn nhất và cộng đồng mã nguồn mở; GitLab gom CI, registry,
  issue, security scanning vào một nền tảng với merge train, environments, runner tự host rất thuận; Bitbucket hợp khi
  công ty sống trong Jira và Confluence.
- **Bảo mật và tuân thủ**: secret scanning, push protection, ruleset ở tầng organization, audit log, SSO/SCIM, và tính
  năng nào nằm ở gói nào.
- **Chi phí và kỹ năng**: giá theo user, phút CI, team đã quen gì.

Ví dụ cho Olist Shop (team nhỏ, SaaS, mã nguồn ở cloud): GitHub với Actions, rulesets, Dependabot và push protection.
Một tổ chức tài chính bắt buộc tự host và muốn một nền tảng duy nhất có security scanning: GitLab self-managed.

## Thiết kế bảo vệ `main` cho một repo có code thanh toán (PCI DSS). Bạn cấu hình gì?

- Ruleset trên `main`: bắt buộc PR, review của code owner, bỏ duyệt cũ khi có commit mới, không ai bypass kể cả admin
  (ngoại lệ qua danh sách bypass có audit).
- CODEOWNERS: dòng `*` mặc định ở đầu; `/services/api/app/payments/` cần payments **và** security; `.github/` và chính
  CODEOWNERS thuộc platform và security, vì ai sửa được workflow là sửa được luật.
- Required checks theo tên job: test, lint, quét secret, quét phụ thuộc, quét image; merge queue để giữ `main` xanh.
- Chặn force-push, chặn xoá nhánh, lịch sử thẳng; bảo vệ tag `v*`; bắt buộc ký commit nếu auditor yêu cầu.
- Deploy production qua environment có required reviewers khác người viết thay đổi, chỉ từ `main`: đây là tách quyền,
  không cần nhánh riêng.
- Bẫy cần tránh: check bắt buộc gắn với workflow có bộ lọc `paths` sẽ chờ mãi với PR không đụng đường dẫn đó.

## Monorepo hay polyrepo? Bạn quyết định dựa trên gì?

Ranh giới repo nên khớp ranh giới thay đổi và ranh giới quyền. Thứ hay đổi cùng nhau, cùng nhóm sở hữu (API, worker,
thư viện dùng chung của chúng) có lợi lớn khi nằm cùng repo: một PR nguyên tử, không lệch phiên bản thư viện. Thứ cần
quyền khác (contractor không được đọc code thanh toán; GitHub, GitLab, Bitbucket không giới hạn quyền đọc theo thư mục)
hoặc vòng đời khác (hạ tầng với plan/apply) nên tách.

Monorepo có giá: CI phải chạy theo phần bị ảnh hưởng (lọc `paths`, rồi Bazel, Pants, Nx khi lớn), clone nặng (partial
clone, sparse checkout), thay đổi phá vỡ lan ngay. Polyrepo có giá: thay đổi xuyên repo nhiều PR, hợp đồng có phiên bản,
cấu hình CI nhân bản (giảm bằng reusable workflow, Renovate). Mô hình lai thường là câu trả lời thực tế. Chuyển đổi đi
từng repo, giữ lịch sử bằng `git filter-repo --to-subdirectory-filter`, repo cũ để chỉ đọc.

## Repo của team clone mất 20 phút, `.git` 8 GB, CI chậm. Bạn xử lý thế nào?

Đo trước: `git count-objects -vH`, `git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sort -k3 -n | tail`
để tìm blob lớn nhất và đường dẫn của chúng. Thường là binary đã commit (dump, ảnh, model, artifact build).

- Ngắn hạn, không viết lại lịch sử: CI dùng shallow clone (`fetch-depth: 1`) cho job không cần lịch sử, partial clone
  (`--filter=blob:none`) cho dev, sparse checkout cho người chỉ làm một phần, cache repo trên runner.
- Ngăn phát sinh thêm: hook và required check chặn tệp lớn, `.gitattributes` đưa loại tệp nhị phân vào Git LFS, artifact
  đi vào registry.
- Dài hạn, có kế hoạch: `git lfs migrate import` hoặc `git filter-repo --strip-blobs-bigger-than` để gỡ khỏi lịch sử,
  thông báo trước, đóng băng repo, mọi người clone lại. Nhớ shallow clone có bẫy: thiếu tag thì `git describe` và công
  cụ release sai.

## Thiết kế: quy trình từ commit tới production cho 5 team, 3 môi trường, có yêu cầu audit

- **Nhánh**: trunk-based, PR sống dưới hai ngày, squash merge, feature flag cho việc dài; nhánh release chỉ khi có thứ
  phát hành theo phiên bản.
- **Kiểm soát trước merge**: ruleset ở tầng organization áp cho mọi repo dịch vụ (không bypass), CODEOWNERS theo thư mục,
  required checks gồm test, lint, quét secret, quét phụ thuộc; merge queue cho repo bận; hook pre-commit dùng chung cấu
  hình với CI.
- **Artifact**: build một lần mỗi commit trên `main`, image gắn sha, ký và có provenance; promote cùng digest qua dev,
  staging, prod, khác biệt nằm ở cấu hình (GitOps, module 12).
- **Deploy**: dev tự động cho mỗi PR (preview), staging tự động khi merge, prod qua environment có người duyệt khác
  người viết; rollback bằng digest trước đó hoặc tắt flag.
- **Audit**: audit log của nền tảng, lịch sử deployment theo environment, commit và tag có chữ ký cho repo hạ tầng,
  changelog sinh từ tiêu đề PR.
- **Đo**: bốn chỉ số DORA lấy từ dữ liệu có sẵn (thời điểm commit, merge, deploy, rollback), xem theo tháng; đổi quy
  trình khi số liệu nói vậy, không theo cảm giác.

## Có nên bắt buộc ký commit không? GPG, SSH hay gitsign?

Author của commit là chữ tự khai, ai cũng giả được. Ký commit chứng minh người giữ khoá tạo commit, và vì commit trỏ tới
tree và parent, chữ ký phủ cả nội dung lẫn lịch sử. Tôi bắt buộc ở repo hạ tầng, repo phát hành và repo chứa chính sách
bảo mật; với repo sản phẩm thông thường, ruleset + review + audit log thường đủ, và bắt buộc ký làm khó bot, rebase,
squash.

Chọn cách ký: SSH (Git 2.34+) dễ nhất vì dùng lại khoá SSH có sẵn, GitHub và GitLab hiển thị "Verified"; GPG lâu đời
nhưng quản lý khoá phiền; gitsign (Sigstore) ký keyless bằng danh tính OIDC và ghi transparency log, hợp cho CI nhưng
nền tảng chưa hiển thị như chữ ký thường. Nhớ rằng ký commit không chứng minh gì về binary build ra: artifact cần chữ
ký và provenance riêng.

## Feature flag giúp trunk-based thế nào, và cái giá của nó là gì?

Flag tách deploy khỏi release: code chưa xong vẫn merge vào `main` và lên production ở trạng thái tắt, nên không cần
nhánh dài. Bật dần theo phần trăm người dùng hay theo nhóm, tắt ngay khi lỗi mà không cần deploy lại. Kết hợp branch by
abstraction cho thay đổi lớn: interface trước code cũ, bản mới phía sau, chuyển dần.

Cái giá: mỗi flag nhân đôi số đường code cần test; flag cũ không ai xoá thành nợ kỹ thuật và rủi ro (Knight Capital mất
440 triệu USD năm 2012 một phần vì tái sử dụng một flag cũ kích hoạt code chết). Quản lý: mỗi flag có chủ sở hữu, hạn
xoá, loại (release, ops, experiment, permission), và một công cụ quản lý (Unleash, LaunchDarkly, OpenFeature làm chuẩn
chung) thay vì `if` rải rác.
