# Bàn giao: track DevOps (sau Phase 1)

Ngày: 2026-11-01. Dành cho phiên Claude Code làm Phase 2 (module 06–11, milestone m03–m06). Đọc hết trước khi làm.

## 1. Trạng thái

- Nhánh `devops-track`, worktree `Learning_Platform-devops`. Phase 1 xong: hạ tầng dùng chung, Olist Shop, module 00–05, capstone m01–m02.
- Mỗi task có implementer và reviewer độc lập; cuối phase có review toàn nhánh và một đợt sửa. Review cuối sạch.
- Track DA, DE, DS cho cùng kết quả trên `main` và trên nhánh (`SOLUTION=1`): DA 436 passed / 314 skipped, DE 638 / 218, DS 943 / 379. `tests/` từ 319 lên 436 passed (test DevOps mới).
- Chạy riêng từng track. Gộp DE + DS + DA vào một tiến trình pytest đã crash (faulthandler) dù từng track riêng đều xanh.

## 2. Tài liệu gốc

- Spec: `docs/superpowers/specs/2026-11-01-devops-track-design.md`
- Plan Phase 1: `docs/superpowers/plans/2026-11-01-devops-phase1.md` (mục Task 10/11 còn ghi `docker run --rm` trực tiếp, đã bị thay bằng `DockerLab`, xem mục 3)
- Checklist K8s/Terraform: `docs/superpowers/research/2026-11-01-k8s-terraform-topic-checklists.md`
- Quy ước nội dung DevOps (bắt buộc đọc): mục "Track DevOps" trong `CONTENT_SPEC.md`

## 3. Quyết định đã đưa ra khi làm Phase 1

Người học xem lại được; mỗi dòng ghi giá phải trả nếu sai.

1. Kiểm link `DEVOPS-TOOLS.md` lỏng tới Task 10 rồi mới chặt (vì module chưa có). Sai thì link hỏng lọt tới Task 10; đã chặt ở `b1962f5`.
2. Package ứng dụng mẫu là `olist_shop/`, log ở `log.py` (tránh trùng `app/` của repo và `logging` của Python). Sai thì đổi tên.
3. Capstone theo bố cục track DE (`project/`, `milestones/`, `solutions/`). Sai thì xếp lại thư mục.
4. Cổng mặc định Olist Shop: PG 25432, Redis 26379, API 28000 (stack DE trên máy đã dùng 15432/16379). Sai thì đổi cổng.
5. Sửa link module 04 và bỏ `12-35` cứng trong lệnh của người học, gộp vào Task 5. Chi phí nếu sai: diff thêm nhỏ.
6. Test graceful-stop không được gửi tín hiệu tới tiến trình lạ: nâng từ Minor lên sửa ngay.
7. Mọi test chạy script người học có thể ghi/xoá tệp phải qua `testkit.run_sandboxed` (bubblewrap); máy không có bwrap thì skip, không bao giờ chạy trần. Sai thì máy thiếu bwrap mất phần chấm, không mất dữ liệu.
8. Sandbox che thêm `/run` và `~/.docker`, lọc `LD_PRELOAD`/`SHELLOPTS`…, test chứng minh chỉ đọc trên đường thấy được.
9. Module 03: lệnh git chạy ngoài sandbox phải tắt `core.hooksPath`/`core.fsmonitor`; gate git ≥ 2.30.
10. Máy builder không có `dig` (cần `sudo apt`): bài chấm bắt buộc không dùng `dig`, DNS chấm offline.
11. Module 04: sửa quy tắc DMARC nhiều bản ghi theo RFC 7489, câu CN, khai báo `dnspython`.
12. Validator cấm gọi docker trực tiếp trong test module; `DockerLab` mặc định `--memory 256m --pids-limit 256`.
13. Capstone: test ở `capstone/project/tests`, `SOLUTION=1` chấm `capstone/solutions/project/`.
14. Capstone m02 dùng `DockerLab`, m01 dùng `run_sandboxed` (khác chữ trong plan).
15. Đợt sửa cuối: tài liệu capstone, compose chỉ publish trên 127.0.0.1, module 01 vào sandbox (graceful-stop là ngoại lệ có lý do, chạy session riêng), mục "Track DevOps" trong `CONTENT_SPEC.md`.
16. Hoãn sang Phase 2 các việc ở mục 4.

testkit vẫn nhận `DEVOPS_CPUSET=none` để tương thích; tài liệu không bao giờ khuyên dùng giá trị này.

## 4. Việc đầu tiên của Phase 2 (hạ tầng dùng chung)

Làm trước khi viết module 06. Đề xuất chi tiết nằm trong review toàn nhánh; tóm tắt:

- **Helper git dùng chung trong testkit** (`SAFE_GIT_CONFIG`, `git_env(home)`, `GitRepo` chuyển sang sandbox sau khi code người học chạy), thay 5 bản chép trong module 03. Module 07 và 12 cần dùng.
- **`require_cluster`** kiểm cluster chạy thật (`kubectl --context kind-devops-lab get --raw /readyz`), tách thông báo "docker tắt", "chưa có cluster", "cluster đang dừng".
- **Helper mới**, ghi vào bảng trong `CONTENT_SPEC.md` khi xong:
  - `KubeLab`: kubeconfig tạm từ `kind get kubeconfig`, namespace `devops-ex-<id>`, không bao giờ đụng `~/.kube/config` hay current-context của người học. Ưu tiên cao nhất.
  - `act_run`: env sạch, image `-P` ghim, giới hạn tài nguyên, không mount socket vào job container.
  - `DockerLab.build` và `DockerLab.compose` (override cpuset, giới hạn, cổng 127.0.0.1, `down -v` khi đóng).
  - `kind_node_exec` / `kind_node_cp` chỉ cho container `devops-lab-*`.
  - LocalStack riêng cho DevOps dưới profile `devops`, không đụng `localstack` của DE.
- **Validator**: thay regex `DIRECT_DOCKER` bằng danh sách cấm theo helper (docker, act, kind, kubectl/helm ngoài `KubeLab`); không bắt nhầm `require_tool("docker", "24")`.
- **`run_sandboxed`** che thêm `~/.kube`, `~/.aws`, `~/.ssh`, `~/.config/gcloud`, `~/.azure`; `import pwd` trong hàm và bắt `KeyError`; cache bước tự kiểm.
- **`DockerLab`**: `--security-opt no-new-privileges`, lưu `docker logs` khi lỗi, `run_once` nhận `memory`/`pids_limit`.
- **testkit**: so phiên bản đệm số 0 (`1.27` = `1.27.0`), câu báo không đọc được phiên bản.
- **Olist Shop** (trước module 10 và 13): response 500 có `X-Request-ID`, `/jobs/recompute` trả 503 khi Redis chết, Postgres có `connect_timeout`.
- **Kiểm trước module 06**: BuildKit có tôn trọng `--cpuset-cpus` không; nếu không, dùng builder `docker-container` với `--driver-opt cpuset-cpus=…`.

## 5. Chưa kiểm chứng trên máy

- Khối cài `gitleaks` (tuỳ chọn, module 03): tải binary bị chặn khi làm, chưa chạy thử.
- Cài `dig` (module 04): cần `sudo apt`, builder không chạy.
- Tương thích OpenSSL 1.1.1 và OpenSSH 8.x (module 04): suy từ code, chỉ chạy trên OpenSSL 3.0.13 và OpenSSH 9.6.
- Các khối lệnh "chạy thử" thủ công trong tài liệu m01/m02 (cần stack compose đã seed).

## 6. Công cụ đã cài trên máy người học

- `~/.local/bin/shellcheck` 0.11.0 (theo hướng dẫn module 01).
- Image: `axllent/mailpit:v1.21.8`, `nginx:1.30.6-alpine`, `python:3.12.16-alpine3.24`.
- Không chạy container nào lâu dài. Container của người học (`de-learning-*`, `portainer`) không bị đụng.
