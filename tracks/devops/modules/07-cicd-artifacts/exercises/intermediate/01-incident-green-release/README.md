---
title: Sự cố - bản lỗi lên staging dù pipeline release xanh
level: intermediate
services: []
files:
  - path: starter/.github/workflows/release.yml
    note: Workflow release đang chạy lúc sự cố
  - path: tests/test_release.py
    note: Không sửa
  - path: tests/fixtures/incident/release.yml
    note: Bản lúc sự cố, test dùng để tái hiện triệu chứng
  - path: tests/fixtures/repo/requirements-dev.txt
    note: Dependency cho test, ghim phiên bản
run:
  - 'ACT_RUNNER="devops-track/act-runner:1.0-$(cat setup/act-runner/Dockerfile setup/act-runner/requirements-ci.txt | sha256sum | cut -c1-8)" && docker pull node:24.22.2-trixie-slim && docker build --pull=false -t "$ACT_RUNNER" setup/act-runner'
  - uv run pytest tracks/devops/modules/07-cicd-artifacts/exercises/intermediate/01-incident-green-release -q
---

## Mục tiêu

Điều tra một sự cố pipeline từ bằng chứng (trạng thái job, log, summary) thay vì đoán, sửa tối thiểu ở đúng chỗ, và chứng minh
bằng hành vi rằng pipeline đã chặn được đúng loại lỗi đã lọt.

## Đề bài

Workflow `release.yml` của Olist Shop chạy test rồi build và đẩy image khi có commit lên `main`; hệ thống deploy tự kéo image mới
nhất có tag `sha-...` lên staging. Ngày 2026-10-28, staging trả `500` cho `GET /orders/{order_id}` suốt 40 phút. Bằng chứng nhóm
on-call thu được:

- Trang run của commit gây lỗi: cả hai job `test` và `publish` đều ✅. Job `publish` đã đẩy image `sha-3f9c2a1b7d10`.
- Job summary của job `test`: `### Kết quả test: 1 failed, 34 passed, 1 warning in 1.16s`.
- Log bước **Test** có đầy đủ traceback của `test_order_total` (`AssertionError`), rồi bước chuyển sang ✅.
- `publish` có `needs: test`. Bước **Test** có `continue-on-error: false`. Không ai sửa trạng thái run bằng tay.
- Dev chạy `uv run pytest -q tests` trên máy với cùng commit: thấy `1 failed`, `echo $?` in `1`.
- Các commit trước có test đỏ thì job `test` đỏ và `publish` không chạy. Workflow vừa được chỉnh sửa tuần trước để thêm job summary.

Tìm nguyên nhân và sửa `starter/.github/workflows/release.yml`. Giữ nguyên hành vi đang có: job `publish` chạy sau `test`, tag
`sha-<12 ký tự>`, bước tóm tắt vẫn ghi kết quả pytest vào summary **kể cả khi test đỏ** và in `devops-ex-output summary=<dòng cuối
của pytest>`.

**Cách test chấm.** Repo là Olist Shop (`tracks/devops/sample-app`) cộng `requirements-dev.txt` và workflow của bạn. Test chạy
workflow bằng `testkit.act_run` (sự kiện `push` trên `main`, image runner `devops-track/act-runner:1.0-<hash8>`, không socket Docker; hai bước
`docker/*` có `if: ${{ !env.ACT }}` bị bỏ qua và chỉ được kiểm tĩnh). Kết quả từng job đọc bằng `act_job_results`, các dòng
`devops-ex-output` đọc bằng `act_outputs`. Có ba lần chạy act, mỗi lần khoảng 15 giây, không cần mạng: uv, Python và wheel
có sẵn trong image runner.

## Tiêu chí đạt

- Có một test đỏ do harness thêm (`tests/test_devops_ex_canary.py`): job `test` fail, job `publish` không chạy và không in tag,
  summary vẫn có `1 failed`.
- Không có test đỏ: hai job xanh, `publish` in tag `sha-<12 hex>`, summary có `passed` và không có `failed`.
- Cấu trúc giữ nguyên: `publish` vẫn `needs: test` và giữ `permissions` `contents: read`, `packages: write`; không job hay bước
  nào `continue-on-error`; bước tóm tắt có `if: always()` và in `devops-ex-output summary=`. Một test đưa vào bản cố ý bỏ `needs`,
  thêm `continue-on-error`, xoá bước tóm tắt và đòi phép kiểm bắt đủ.
- Một test chạy bản lúc sự cố (`tests/fixtures/incident/release.yml`) với test đỏ và đòi nó tái hiện đúng triệu chứng: summary có
  `1 failed` mà hai job xanh và tag vẫn được in.
- `actionlint` (nếu đã cài) không báo lỗi.
- Viết được postmortem ngắn: vì sao lỗi không lộ ra ở lần chỉnh sửa tuần trước, và một biện pháp để cả tổ chức không lặp lại.

## Gợi ý

### Gợi ý 1

Runner quyết định một bước `run:` xanh hay đỏ chỉ bằng **một con số**: mã thoát của tiến trình shell chạy script của bước.
Đọc script của bước **Test** trong `starter/`: với dòng lệnh đó, mã thoát của cả dòng đến từ lệnh nào? Chạy đúng dòng đó trên máy
với một test đỏ rồi `echo $?` để kiểm.

### Gợi ý 2

Log của act in đúng lệnh mà runner dùng để chạy mỗi bước (`docker exec cmd=[...]`). Chạy thử workflow lúc sự cố bằng
`act push -j test -P ubuntu-latest="$ACT_RUNNER" --pull=false --container-daemon-socket -` trong một bản sao repo
(`ACT_RUNNER` đặt như lệnh build ở mục 0 của module),
xem dòng đó, rồi tra tài liệu GitHub về `jobs.<job_id>.steps[*].shell` để biết runner gọi shell với cờ gì khi bạn không khai báo.
