---
title: Tính phiên bản semver và changelog từ Conventional Commits
level: intermediate
services: []
files:
  - path: starter/release.py
    note: 6 TODO
  - path: tests/test_release.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/intermediate/03-conventional-release -q
---

## Mục tiêu

Hiểu cơ chế mà release-please, semantic-release hay commitizen dùng để tự đánh số phiên bản: đọc commit từ tag gần
nhất, phân loại theo Conventional Commits, quyết định bump theo semver, sinh changelog. Viết một bản nhỏ để biết nó
sai ở đâu khi tag hay message không chuẩn.

## Đề bài

Olist Shop phát hành API theo semver, tag dạng `vX.Y.Z`. Viết `starter/release.py`, chạy bằng `python release.py` trong
gốc repo, không tham số.

**1. Tag gốc**: trong các tag **reachable từ `HEAD`** (`git tag --merged HEAD`), chỉ xét tag khớp đúng
`^v<số>.<số>.<số>$` (không hậu tố: `v2.0.0-rc.1`, `release-2026-07` bị bỏ), lấy bản **cao nhất theo semver** (so số,
không so chữ: `v1.10.0 > v1.9.0`). Tag trên nhánh chưa merge vào `HEAD` không tính. Không có tag nào thì phiên bản hiện
tại là `v0.0.0` và xét mọi commit.

**2. Commit được xét**: `<tag>..HEAD` (hoặc mọi commit), **bỏ merge commit**, theo thứ tự `git log` (mới nhất trước).

**3. Phân tích message** theo [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

- Header (dòng đầu): `<type>[(<scope>)][!]: <description>`. `type` gồm chữ cái, **không phân biệt hoa thường**
  (`Feat`, `FIX` hợp lệ). `scope` không chứa ngoặc. Sau `:` đúng một dấu cách rồi tới description không rỗng. Header
  sai dạng (`feat : x`, `fixup! feat: x`, `WIP`) thì bỏ qua commit đó: không bump, không vào changelog. Có thể in lý do
  ra stderr, test không kiểm stderr.
- Breaking khi header có `!` trước `:`, **hoặc** một dòng sau header **bắt đầu bằng** `BREAKING CHANGE: ` hay
  `BREAKING-CHANGE: ` (chữ hoa, đúng như spec). Chữ đó nằm giữa dòng hay viết thường thì không tính.

**4. Bump**:

| Trong các commit được xét có | Phiên bản mới |
| --- | --- |
| Ít nhất một breaking | Major + 1, minor = patch = 0. **Nếu major đang là `0`**: minor + 1, patch = 0 (`v0.9.1` thành `v0.10.0`) |
| Không breaking, có `feat` | Minor + 1, patch = 0 |
| Chỉ có `fix` hoặc `perf` (cộng loại khác) | Patch + 1 |
| Không có gì ở trên (chỉ `docs`, `chore`, `ci`...) | Không release: stdout đúng một dòng `no release`, exit `0` |

**5. Changelog** ra stdout, exit `0`, đúng định dạng:

```text
## v1.5.0

### Features
- payments: add Pix (3f2a9c1)

### Bug Fixes
- shipping: round fee to 2 decimals (8b0d4e7)
```

- Dòng đầu `## v<phiên bản mới>`, rồi các mục theo thứ tự `BREAKING CHANGES`, `Features` (`feat`), `Bug Fixes`
  (`fix`), `Performance` (`perf`). Mục rỗng không in. Giữa các khối đúng một dòng trống.
- Mỗi commit một dòng `- <scope>: <description> (<7 ký tự đầu của SHA>)`, không có scope thì `- <description> (<sha7>)`.
  Thứ tự trong mục theo thứ tự `git log`.
- Commit breaking **chỉ** nằm ở `BREAKING CHANGES` (không lặp ở mục theo type), và description lấy từ dòng
  `BREAKING CHANGE:` nếu có, không thì từ header. Commit loại khác (`docs`, `chore`...) chỉ xuất hiện khi breaking.

**6. Lỗi**: chạy ngoài repo git thì thông báo ra stderr, exit `1`, stdout rỗng, không traceback.

Test dựng repo bằng `git` trong thư mục tạm, rồi chạy `python release.py` của bạn trong sandbox bubblewrap của
[module 02](../../../../02-scripting/README.md#0-cài-đặt) với `HOME` tạm, `GIT_CONFIG_GLOBAL=/dev/null`,
`GIT_CONFIG_SYSTEM=/dev/null`: cấu hình Git của bạn (alias, `tag.sort`, `log.showSignature`) không ảnh hưởng tới
output. So sánh stdout nguyên văn (bỏ khoảng trắng cuối). Thiếu `bwrap` thì test skip.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/intermediate/03-conventional-release -q` pass
  toàn bộ.
- Giải thích được vì sao `git describe --tags --abbrev=0` và `git tag | sort | tail -1` đều cho tag gốc sai trong
  `test_picks_highest_plain_semver_tag_reachable_from_head`.
- Nói được team sẽ ép chuẩn message ở đâu (hook `commit-msg`, kiểm tiêu đề PR khi squash-merge, CI) và vì sao squash
  merge làm việc này dễ hơn.

## Gợi ý

### Gợi ý 1

Đọc message đầy đủ an toàn bằng NUL: `git log --no-merges --format=%H%x00%B%x00 <range>`, rồi `split("\x00")` và ghép
từng cặp SHA, message. Message có thể nhiều dòng, nên không tách theo `\n`. Header:
`^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^()\r\n]+)\))?(?P<bang>!)?: (?P<description>\S.*)$`.

### Gợi ý 2

So phiên bản bằng tuple số nguyên: `max((tuple(map(int, m.groups())), tag) for ...)`. Bọc mọi lệnh `git` trong một hàm
ném exception riêng khi exit khác `0`, bắt nó trong `main()` để in lỗi gọn và trả `1`.
