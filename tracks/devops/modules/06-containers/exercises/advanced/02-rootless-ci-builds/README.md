---
title: Bỏ docker.sock khỏi runner CI - thiết kế build image rootless
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung tài liệu thiết kế, điền mọi TODO
  - path: tests/test_design.py
    note: Không sửa; kiểm khung và lựa chọn không privileged, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/06-containers/exercises/advanced/02-rootless-ci-builds -q
---

## Mục tiêu

Ra một quyết định kiến trúc về builder như một senior trình bày trong buổi review: hiểu chính xác vì sao mount `docker.sock` là
trao quyền root, so sánh các builder không cần daemon root bằng tiêu chí cụ thể, chọn một, và có kế hoạch chuyển đổi đo được.

## Đề bài

Runner CI tự host của Olist là pod trên một cluster Kubernetes dùng chung (cùng node với vài service nội bộ). Mỗi ngày khoảng
300 lần build image cho 25 repository, Dockerfile đa số multi-stage, build trung bình 4 phút nhờ cache trên node. Hiện mỗi job
build mount `/var/run/docker.sock` của node vào pod rồi gọi `docker build` và `docker push`.

Sau một đợt pentest, bảo mật yêu cầu trong một quý:

- Không pod CI nào mount `docker.sock`, không pod CI nào `privileged`.
- Job build không đọc được container, image hay bí mật của job khác.
- Image đẩy lên registry chung kèm SBOM.

Team platform 3 người muốn giữ nguyên Dockerfile của các team, không để thời gian build tăng quá 30%, và không phải tự bảo trì
một fork của công cụ nào.

Viết `starter/DESIGN.md`, giữ các heading `## 1.` tới `## 7.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. Bối cảnh | Ít nhất 300 ký tự (không tính bảng và khối code) |
| 2. Hiện trạng và rủi ro | Ít nhất 3 gạch đầu dòng, có nhắc `docker.sock` |
| 3. So sánh phương án | Bảng đúng các cột `Phương án`, `Cần daemon`, `Cần privileged`, `Cache`, `Đánh đổi`; ít nhất 4 dòng đủ cột; tên phương án phủ ít nhất 3 trong BuildKit, Buildah, Kaniko, Podman, DinD |
| 4. Quyết định | Một dòng `Lựa chọn: <tên>` trùng (không phân biệt hoa thường) tên một phương án ở phần 3, và ô `Cần privileged` của phương án đó bắt đầu bằng "Không"; phần này ít nhất 250 ký tự |
| 5. Kiến trúc | Một khối ` ```mermaid ` có ít nhất 5 cạnh (`-->`, `->>` hoặc `---`), không có chữ `docker.sock` hay `privileged` |
| 6. Kế hoạch chuyển đổi | Ít nhất 5 bước đánh số |
| 7. Kiểm chứng và rủi ro còn lại | Ít nhất 4 gạch đầu dòng |

Test chỉ kiểm khung và các điều kiện trên; một test khác đưa một thiết kế chọn Docker-in-Docker privileged vào cùng phép kiểm
và đòi nó bị bắt. Nội dung chấm bằng rubric trong `solutions/advanced/02-rootless-ci-builds/SOLUTION.md`; đọc rubric **sau**
khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/06-containers/exercises/advanced/02-rootless-ci-builds -q` pass.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Giải thích được bằng một ví dụ lệnh cụ thể vì sao quyền vào `docker.sock` tương đương root trên node.
- Kế hoạch có cách đo "build không chậm hơn 30%" trước và sau khi chuyển.

## Gợi ý

### Gợi ý 1

Phân biệt ba câu hỏi: builder có cần **daemon** không (BuildKit cần `buildkitd`, Buildah và Kaniko thì không), daemon hay tiến
trình đó chạy **root** không (rootless dùng user namespace), và pod có cần **privileged** không (rootless BuildKit cần tắt
seccomp/AppArmor của pod hoặc chạy không có process sandbox, nhưng không cần privileged). Tra trạng thái bảo trì của từng dự án
trước khi chọn.

### Gợi ý 2

Mất cache trên node là cái giá lớn nhất khi bỏ socket. Cache build đặt ở registry (`--cache-to type=registry,mode=max`) dùng được
cho mọi pod ở mọi node. buildkitd chạy thành service dùng chung (một Deployment rootless) giữ cache nóng hơn buildkitd chạy theo
từng job, đổi lại các job dùng chung một daemon.
