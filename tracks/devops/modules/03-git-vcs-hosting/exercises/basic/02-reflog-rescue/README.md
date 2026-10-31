---
title: Cứu commit sau reset --hard nhầm và nhánh đã xoá bằng reflog
level: basic
services: []
files:
  - path: starter/rescue.sh
    note: 4 TODO
  - path: tests/test_rescue.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/basic/02-reflog-rescue -q
---

## Mục tiêu

Hiểu reflog đủ để cứu dữ liệu khi đồng nghiệp hoảng loạn nhắn "mất hết code rồi": tìm lại commit sau `reset --hard`
và nhánh đã `branch -D`, đúng commit cần tìm chứ không phải commit gần đó, mà không đụng vào thứ đang dở dang trong
working tree của họ.

## Đề bài

Lan làm trên repo Olist Shop (chưa push). Theo thứ tự:

1. Commit vài thay đổi trên `main`, tạo nhánh `feature/pix-payment` và commit trên đó, qua lại giữa hai nhánh vài lần.
2. Trên `main`: commit một tệp debug rồi `git reset --hard HEAD~1` để bỏ nó (lần reset này đúng ý).
3. Commit thêm "refund endpoint", ghé nhánh `docs/runbook` rồi quay lại `main`.
4. Gõ nhầm `git reset --hard HEAD~3`: ba commit trên `main` biến mất.
5. Không để ý, commit thêm một hotfix lên `main`, rồi `git branch -D feature/pix-payment` vì tưởng đã merge.
6. Đang sửa dở `api/orders.py` và có một tệp chưa track.

Viết `starter/rescue.sh <nhánh-đã-xoá>`, chạy trong gốc repo:

- Tạo nhánh `rescue/main` trỏ vào **giá trị của `main` ngay trước lần `reset` gần nhất** trong reflog của `main` (mục
  reflog có subject bắt đầu bằng `reset: `). Với tình huống trên, đó là commit "refund endpoint", không phải tệp debug
  của lần reset trước.
- Tạo lại nhánh `<nhánh-đã-xoá>` trỏ vào **giá trị của `HEAD` ngay trước lần gần nhất rời nhánh đó** trong reflog của
  `HEAD` (mục có subject `checkout: moving from <nhánh-đã-xoá> to ...`; `git switch` cũng ghi đúng dạng này).
- stdout đúng hai dòng: `rescue/main <sha 40 ký tự>` rồi `<nhánh-đã-xoá> <sha 40 ký tự>`. Exit `0`.
- **Không đổi** `main`, `HEAD` (vẫn ở `main`), index, working tree, tệp chưa track. Không `checkout`, `switch`,
  `reset`, `stash`. Tạo nhánh bằng `git branch <tên> <sha>` hoặc `git update-ref`.
- Chạy lần hai: nhánh đã tồn tại và trỏ **đúng** commit cần khôi phục thì giữ nguyên, exit `0`, output như lần một.

| Tình huống | Exit | Kết quả |
| --- | --- | --- |
| Thiếu tham số hoặc thừa | `2` | stderr bắt đầu bằng `Usage:` |
| Reflog của `main` không có mục `reset: ` nào, hoặc reflog của `HEAD` không có lần rời nhánh đó | `1` | Lỗi ra stderr, **không tạo nhánh nào** |
| `rescue/main` hoặc nhánh cần khôi phục đã tồn tại ở commit khác | `1` | Lỗi ra stderr, không ghi đè, **không tạo nhánh nào** |

Nội dung commit trong test sinh ngẫu nhiên mỗi lần chạy, nên SHA không đoán trước được. Mọi lần chạy script của bạn đi
qua sandbox bubblewrap của [module 02](../../../../02-scripting/README.md#0-cài-đặt) với `HOME` tạm,
`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`: cấu hình Git của bạn không ảnh hưởng và repo thật không
bị đụng tới. Thiếu `bwrap` thì test skip.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/03-git-vcs-hosting/exercises/basic/02-reflog-rescue -q` pass toàn bộ, gồm
  `shellcheck -S style` sạch.
- Giải thích được vì sao `main@{1}` và `@{-1}` (cách hay được chỉ trên mạng) cho kết quả sai trong tình huống này
  (test `test_naive_rescue_is_caught` chạy đúng cách đó).
- Nói được giới hạn của reflog: chỉ có trên máy đã làm thao tác, hết hạn sau 90 ngày (30 ngày với commit không còn
  reachable), không có trong clone mới hay trên server.

## Gợi ý

### Gợi ý 1

`git reflog show --format='%H%x09%gs' main` in mỗi mục một dòng, mới nhất trước: SHA mà ref trỏ tới **sau** thao tác,
tab, rồi subject của mục. Giá trị **trước** thao tác ở dòng `i` chính là SHA của dòng `i+1` (mục cũ hơn liền kề), tức
`main@{i+1}`.

### Gợi ý 2

Đọc từng dòng bằng `while IFS=$'\t' read -r sha subject; do ... done < <(git reflog show ...)`, đánh dấu khi gặp dòng
khớp và in SHA của dòng ngay sau. Kiểm cả hai kết quả và cả hai nhánh đích **trước** khi tạo nhánh nào, để lỗi không
để lại trạng thái nửa vời.
