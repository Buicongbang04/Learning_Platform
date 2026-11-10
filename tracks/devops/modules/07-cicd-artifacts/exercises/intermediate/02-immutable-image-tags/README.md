---
title: Chính sách tag image bất biến và promotion bằng retag
level: intermediate
services: [registry]
files:
  - path: starter/ci/image-tags.sh
    note: Viết toàn bộ script tính tag
  - path: starter/ci/promote.sh
    note: Viết toàn bộ script promote bằng retag trên registry
  - path: tests/test_image_tags.py
    note: Không sửa
  - path: tests/fixtures/tiny/Dockerfile
    note: Image nhỏ dùng để thử push nhiều tag
run:
  - docker pull python:3.12.16-alpine3.24
  - docker compose -f setup/docker-compose.yml --profile devops up -d registry
  - uv run pytest tracks/devops/modules/07-cicd-artifacts/exercises/intermediate/02-immutable-image-tags -q
---

## Mục tiêu

Mã hoá chính sách tag image của tổ chức thành script chạy được ở mọi CI: mỗi tag trỏ đúng một commit và không bao giờ bị dời,
build từ working tree bẩn bị từ chối, và "phát hành" một bản là gắn thêm tag cho **cùng một digest** chứ không build lại.

## Đề bài

**Phần 1: tính tag.** Viết `starter/ci/image-tags.sh` (bash). Script chạy ở gốc một repo git, đọc ref hiện tại từ biến `GITHUB_REF` (như GitHub Actions
đặt), và in các tag image ra stdout, mỗi dòng một tag, đúng thứ tự:

1. Dòng đầu luôn là `sha-<12 ký tự đầu của commit HEAD>`.
2. Dòng thứ hai theo ref:

| `GITHUB_REF` | Dòng thứ hai | Ví dụ |
| --- | --- | --- |
| `refs/heads/main` | `main-<thời điểm commit theo UTC, YYYYmmddHHMMSS>-<12 ký tự>` | `main-20260501103000-3f9c2a1b7d10` |
| `refs/heads/<nhánh khác>` | `br-<slug>-<12 ký tự>` | `refs/heads/Feature/Pix_Payments` thành `br-feature-pix-payments-3f9c2a1b7d10` |
| `refs/tags/v<MAJOR>.<MINOR>.<PATCH>[-<pre>]` | Phiên bản bỏ chữ `v` | `v1.4.2` thành `1.4.2`, `v2.0.0-rc.1` thành `2.0.0-rc.1` |
| `refs/pull/<số>/merge` | `pr-<số>-<12 ký tự>` | `pr-42-3f9c2a1b7d10` |

Quy tắc chi tiết:

- Thời điểm commit là **committer date** của HEAD đổi sang UTC, không phải giờ chạy script: build lại cùng commit phải ra cùng tag.
- Slug của nhánh: chữ thường; mọi chuỗi ký tự không phải `a-z0-9` thành một dấu `-`; bỏ `-` ở hai đầu; cắt còn tối đa 40 ký tự rồi
  bỏ `-` ở cuối nếu có.
- Tag git phải là `v` cộng SemVer: ba số không có số 0 thừa ở đầu (`v01.4.2` sai), phần pre-release tuỳ chọn. Tag phải trỏ đúng
  HEAD (tag có chú thích cũng vậy).
- Không bao giờ in `latest` hay tag nào dời được (`main`, `stable`, `1.4`).

Từ chối (không in gì ra stdout, in lý do ra stderr):

| Tình huống | Mã thoát |
| --- | --- |
| `GITHUB_REF` không có hay rỗng, hoặc ref không thuộc bốn dạng trên (`refs/remotes/...`, `main`) | 2 |
| Working tree có thay đổi chưa commit, kể cả tệp chưa track | 3 |
| Tag sai dạng, không tồn tại, hoặc không trỏ HEAD | 4 |

**Phần 2: promote bằng retag trên registry.** Viết `starter/ci/promote.sh <registry> <repository> <tag-nguồn> <tag-đích>`
(bash, dùng `curl`). Script gắn tag đích cho **đúng manifest** của tag nguồn ngay trên registry, không pull, không build lại, theo
API của OCI distribution spec: `GET /v2/<repository>/manifests/<tag-nguồn>` với header `Accept` gồm bốn media type (OCI index, OCI
manifest, Docker manifest list, Docker manifest v2), giữ nguyên thân và `Content-Type` của response, rồi
`PUT /v2/<repository>/manifests/<tag-đích>` với thân và `Content-Type` đó. Thành công thì in digest (`sha256:...`, lấy từ header
`Docker-Content-Digest`) ở dòng cuối stdout, thoát 0.

| Tình huống | Kết quả |
| --- | --- |
| Tag đích chưa có | PUT, kiểm lại tag đích trỏ đúng digest nguồn, in digest, thoát 0 |
| Tag đích đã trỏ **cùng** digest | Không làm gì, in digest, thoát 0 (chạy lại pipeline không lỗi) |
| Tag đích đã trỏ digest **khác** | Từ chối, thoát 5, stdout rỗng: tag phát hành không bao giờ bị dời |
| Tag nguồn không có trên registry | Thoát 4, stdout rỗng |
| Sai số tham số | Thoát 2 |

Registry local chạy HTTP không xác thực ở `127.0.0.1`; thêm `--noproxy '*'` cho `curl` để proxy của máy không chen vào.

**Cách test chấm.** Phần 1: mỗi test dựng một repo git tạm (`GitRepo`, tác giả và ngày cố định 2026-05-01 10:00 UTC; test giờ UTC
commit lúc `2026-05-01T17:30:00+07:00`), rồi chạy `bash <đường dẫn script>` trong sandbox bwrap (`run_sandboxed`, `HOME` tạm, env
dựng từ đầu cộng `GITHUB_REF`) với thư mục làm việc là repo. Script không được tạo tệp trong repo (sẽ làm tree bẩn). Phần 2:
`DockerLab.build` build `tests/fixtures/tiny/Dockerfile`, `DockerLab.push` đẩy **chỉ** tag `sha-...` lên registry local (dưới tên
riêng `devops-ex-<id>/olist-api`), rồi test chạy `promote.sh` của bạn trong sandbox (mạng không bị tách) và hỏi API của registry:

1. Commit có tag `v1.5.0`: tag `sha-...` từ `image-tags.sh` cho `main` và cho `refs/tags/v1.5.0` phải trùng; `promote.sh` gắn
   `1.5.0` cho tag `sha-...`; digest của `1.5.0` phải đúng digest đã build và đúng dòng cuối script in ra; chạy lại lần hai vẫn
   thoát 0 với cùng digest.
2. Hai image khác nhau (build arg `VARIANT=a` và `b`) đã nằm ở `sha-0123456789ab` và `1.5.0`: promote phải thoát 5 và `1.5.0` vẫn
   trỏ digest cũ.
3. Tag nguồn không tồn tại: thoát 4.

Registry chưa bật thì ba test đó skip; thiếu `curl` cũng skip. Mọi manifest bị xoá khi test xong. Test cuối chạy `shellcheck` trên
cả hai script (skip khi chưa cài shellcheck, module 01).

## Tiêu chí đạt

- 21 test pass: 6 trường hợp in tag, tag không trỏ HEAD, 4 dạng tag sai, tree bẩn (tệp đã track và tệp chưa track), 4 dạng ref
  không hỗ trợ, 3 trường hợp promote trên registry, và shellcheck.
- `shellcheck ci/image-tags.sh ci/promote.sh` sạch (có test).
- Giải thích được vì sao tag `main-<thời điểm>-<sha>` sắp xếp được mà vẫn bất biến, và công cụ nào dựa vào điều đó.

## Gợi ý

### Gợi ý 1

`git status --porcelain --untracked-files=all` in rỗng khi tree sạch. `git rev-parse --verify "refs/tags/${tag}^{commit}"` trả
commit mà tag trỏ tới, kể cả tag có chú thích. `git show -s --format=%cd --date=format-local:%Y%m%d%H%M%S HEAD` với `TZ=UTC0` in
thời điểm commit theo UTC.

### Gợi ý 2

`curl -sS -o body -D headers -w '%{http_code}' -H "Accept: ..." <url>` ghi thân, header và in mã HTTP; đọc `Content-Type` và
`Docker-Content-Digest` từ tệp header (bỏ `\r` bằng `tr -d '\r'`). PUT: `curl -fsS -X PUT -H "Content-Type: <kiểu>"
--data-binary @body <url>`. Tệp tạm đặt trong `mktemp -d` và xoá bằng `trap ... EXIT`.

So khớp SemVer bằng `[[ "$tag" =~ $re ]]` với `re` đặt trong biến (viết regex thẳng sau `=~` trong `[[ ]]` dễ sai vì quote). Slug:
`tr '[:upper:]' '[:lower:]'` rồi `sed -E 's/[^a-z0-9]+/-/g'`. Cắt chuỗi trong bash: `${value:0:40}`.
