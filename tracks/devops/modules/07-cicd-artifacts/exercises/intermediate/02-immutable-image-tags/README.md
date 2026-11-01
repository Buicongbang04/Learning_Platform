---
title: Chính sách tag image bất biến và promotion bằng retag
level: intermediate
services: [registry]
files:
  - path: starter/ci/image-tags.sh
    note: Viết toàn bộ script
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

Mã hoá chính sách tag image của tổ chức thành một script chạy được ở mọi CI: mỗi tag trỏ đúng một commit và không bao giờ bị dời,
build từ working tree bẩn bị từ chối, và "phát hành" một bản là gắn thêm tag cho **cùng một digest** chứ không build lại.

## Đề bài

Viết `starter/ci/image-tags.sh` (bash). Script chạy ở gốc một repo git, đọc ref hiện tại từ biến `GITHUB_REF` (như GitHub Actions
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

**Cách test chấm.** Mỗi test dựng một repo git tạm (`GitRepo`, tác giả và ngày cố định 2026-05-01 10:00 UTC; test giờ UTC commit
lúc `2026-05-01T17:30:00+07:00`), rồi chạy `bash <đường dẫn script>` trong sandbox bwrap (`run_sandboxed`, `HOME` tạm, env dựng từ
đầu cộng `GITHUB_REF`) với thư mục làm việc là repo. Script không được tạo tệp trong repo (sẽ làm tree bẩn). Một test cuối build
`tests/fixtures/tiny/Dockerfile` bằng `DockerLab.build`, chạy script cho cùng một commit trên `main` rồi trên tag `v1.5.0`, đẩy
image lên registry local dưới **cả bốn** tag (`DockerLab.push`), hỏi digest của từng tag qua API của registry và đòi bốn digest
bằng nhau. Registry chưa bật thì test đó skip.

## Tiêu chí đạt

- 18 test pass: 6 trường hợp in tag, tag không trỏ HEAD, 4 dạng tag sai, tree bẩn (tệp đã track và tệp chưa track), 4 dạng ref
  không hỗ trợ, và promotion cùng digest.
- `shellcheck ci/image-tags.sh` sạch.
- Giải thích được vì sao tag `main-<thời điểm>-<sha>` sắp xếp được mà vẫn bất biến, và công cụ nào dựa vào điều đó.

## Gợi ý

### Gợi ý 1

`git status --porcelain --untracked-files=all` in rỗng khi tree sạch. `git rev-parse --verify "refs/tags/${tag}^{commit}"` trả
commit mà tag trỏ tới, kể cả tag có chú thích. `git show -s --format=%cd --date=format-local:%Y%m%d%H%M%S HEAD` với `TZ=UTC0` in
thời điểm commit theo UTC.

### Gợi ý 2

So khớp SemVer bằng `[[ "$tag" =~ $re ]]` với `re` đặt trong biến (viết regex thẳng sau `=~` trong `[[ ]]` dễ sai vì quote). Slug:
`tr '[:upper:]' '[:lower:]'` rồi `sed -E 's/[^a-z0-9]+/-/g'`. Cắt chuỗi trong bash: `${value:0:40}`.
