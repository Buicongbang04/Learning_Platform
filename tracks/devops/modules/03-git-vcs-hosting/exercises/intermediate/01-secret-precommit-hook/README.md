---
title: Pre-commit hook chặn secret, có allowlist và không chặn nhầm
level: intermediate
services: []
files:
  - path: starter/pre-commit
    note: 5 TODO, script Bash không có đuôi .sh
  - path: tests/test_hook.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/intermediate/01-secret-precommit-hook -q
---

## Mục tiêu

Viết lớp chặn secret đầu tiên, ngay trên máy lập trình viên: hook đọc đúng thứ sắp được commit (bản staged), nhận ra
các dạng secret hay bị lộ nhất, có cách bỏ qua dữ liệu giả có kiểm soát, và đủ ít chặn nhầm để team không tắt nó đi.

## Đề bài

Olist Shop vừa có một sự cố: mật khẩu Postgres production nằm trong `settings.py` và bị push lên GitHub. Team muốn một
hook `pre-commit` chạy trên máy mọi người. Viết `starter/pre-commit` (Bash).

**Tệp được xét**: tệp được thêm, sửa, copy hoặc đổi tên trong index (`--diff-filter=ACMR`). Tệp bị xoá không xét. Tên
tệp có thể có dấu cách. Commit đầu tiên của repo (chưa có `HEAD`) cũng phải được kiểm.

**Nội dung được xét**: **bản staged** của tệp (thứ sẽ vào commit), không phải working tree. Secret đã stage rồi xoá
khỏi working tree vẫn bị chặn; secret chỉ có trong working tree, chưa stage, thì không chặn. Bạn chọn quét toàn bộ nội
dung staged hay chỉ dòng được thêm; test không phân biệt hai cách. Tệp nhị phân bỏ qua.

**Quy tắc**:

| Rule | Bắt | Không bắt |
| --- | --- | --- |
| `aws-access-key-id` | Chuỗi `AKIA` hoặc `ASIA` + đúng 16 ký tự `[A-Z0-9]`, hai đầu không dính ký tự `[A-Z0-9]` | Chuỗi kết thúc bằng `EXAMPLE` (key mẫu của tài liệu AWS, `AKIAIOSFODNN7EXAMPLE`); chuỗi ngắn hơn như `AKIA1234` |
| `private-key` | Dòng có `-----BEGIN PRIVATE KEY-----`, hoặc có `RSA `, `DSA `, `EC `, `OPENSSH `, `ENCRYPTED `, `PGP ` trước `PRIVATE KEY`, có thể kèm ` BLOCK` sau; dòng có thể thụt lề (key trong YAML) | `BEGIN PUBLIC KEY`, `BEGIN CERTIFICATE`, chữ `BEGIN RSA PRIVATE KEY` không có năm dấu `-` hai bên |
| `postgres-password-url` | `postgres://` hoặc `postgresql://`, rồi `user:password@`; user không chứa `:`, `/`, `@`, khoảng trắng; password không rỗng, không chứa `@`, `/`, khoảng trắng | Không có password (`postgresql://olist@db/olist`); password bắt đầu bằng `$` (`${PGPASSWORD}`, `$DB_PASS`) hoặc `<` (`<password>`) |
| `dotenv-file` | Tên tệp (phần sau `/` cuối) là `.env` hoặc bắt đầu bằng `.env.`, ở bất kỳ thư mục nào, bất kể nội dung | `.env.example`, `.env.sample`, `.env.template`; tên chỉ chứa chữ env như `docs/env.md`, `environment.py` |

**Allowlist** (chỉ áp dụng cho ba rule nội dung, không cho `dotenv-file`):

- Dòng chứa chuỗi `pragma: allowlist secret` (cùng quy ước với detect-secrets) không bị bắt.
- Tệp `.secrets-allowlist` ở gốc repo: mỗi dòng không rỗng và không bắt đầu bằng `#` là một chuỗi cố định; dòng nội
  dung nào chứa nguyên văn một chuỗi trong đó thì không bị bắt. Nên đọc bản staged của tệp này; test luôn stage nó với
  nội dung trùng working tree, nên đọc bản nào cũng qua. Dòng trống không được biến thành "cho qua mọi thứ".

**Output và exit code**:

- Mỗi phát hiện in **một dòng** ra stderr đúng dạng `secret: <rule>: <đường dẫn từ gốc repo>`, ví dụ
  `secret: postgres-password-url: services/api/settings.py`. Một tệp vi phạm nhiều rule thì in mỗi rule một dòng; in
  trùng không sao. Sau đó in thêm hướng dẫn tuỳ ý.
- Có ít nhất một phát hiện: exit khác `0` (commit bị huỷ). Không có: exit `0`.
- Không được đổi index (không unstage tệp của người dùng) hay working tree.

Test tạo repo trong thư mục tạm, chép hook của bạn vào `.git/hooks/pre-commit`, stage tệp rồi chạy cả `git commit`
trong sandbox bubblewrap của [module 02](../../../../02-scripting/README.md#0-cài-đặt) (hook chạy bên trong git, nên
cả lệnh git nằm trong sandbox). Môi trường dựng lại từ đầu: `HOME` tạm, `GIT_CONFIG_GLOBAL=/dev/null`,
`GIT_CONFIG_SYSTEM=/dev/null`, nên `core.hooksPath` hay signing trong `~/.gitconfig` của bạn không ảnh hưởng, và
hook của bạn không chạy trên repo thật nào. Thiếu `bwrap` thì test skip. Có 11 ca phải chặn, 12 ca không được chặn
(xem `BLOCK` và `ALLOW` trong test), cộng các ca staged/working tree, xoá `.env`, commit đầu tiên, nhiều phát hiện,
và hai ca lạm dụng allowlist phải vẫn bị chặn: `.secrets-allowlist` có dòng trống hoặc chỉ có khoảng trắng cùng một
AWS key thật ở tệp khác, và `.env` có dòng chứa `pragma: allowlist secret`. Git cũ hơn 2.30 thì test skip.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/intermediate/01-secret-precommit-hook -q` pass
  toàn bộ, gồm `shellcheck -S style` sạch.
- Giải thích được vì sao hook phía client chỉ là lớp đầu: `git commit --no-verify` bỏ qua nó, máy mới clone chưa có
  hook. Kể được lớp phía server (push protection, quét trong CI) cần có thêm.
- Nói được bạn làm gì, theo thứ tự, khi hook bị bỏ qua và key đã lên remote.

## Gợi ý

### Gợi ý 1

Danh sách tệp: `git diff --cached --name-only -z --diff-filter=ACMR "$against" --`, với `against` là `HEAD`, hoặc
empty tree `$(git hash-object -t tree /dev/null)` khi chưa có commit nào (cách của tệp `pre-commit.sample` trong mọi
repo). Đọc bằng `while IFS= read -r -d '' path`. Nội dung staged của một tệp: `git show ":$path"`.

### Gợi ý 2

`git grep --cached -I -z -F -e AKIA -e ASIA -e 'PRIVATE KEY' -e postgres -- <pathspec...>` tìm thẳng trong index, bỏ
tệp nhị phân, in `đường dẫn\0dòng`. Dùng pathspec `":(literal)$path"` để tên tệp có `*` hay `?` không bị hiểu là glob.
Rồi xét từng dòng bằng `[[ $line =~ $re ]]` trong Bash: kiểm AWS key theo từng token
(`${line//[^A-Z0-9]/ }` với `set -f`), kiểm URL Postgres theo `BASH_REMATCH`.
