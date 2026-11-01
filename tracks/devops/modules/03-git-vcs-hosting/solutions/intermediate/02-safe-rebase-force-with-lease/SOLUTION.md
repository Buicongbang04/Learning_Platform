# Lời giải: dọn nhánh bằng rebase --autosquash và --force-with-lease

Script đầy đủ ở `tidy_branch.sh` cạnh tệp này.

## Cách làm

1. **Chặn sớm, exit `2`.** Tên nhánh lấy bằng `git symbolic-ref`, nên detached HEAD lỗi ngay. Nhánh dùng chung bị từ
   chối bằng `case`. `git update-index --refresh` trước `git diff --quiet` để tệp chỉ đổi mtime không bị coi là sửa.
2. **Lease đọc trước fetch.** `refs/remotes/origin/<nhánh>` lúc này là thứ bạn đã thấy và đã dựa vào để làm việc. Đây
   chính là giá trị cần so trên server.
3. **Fetch đúng `main`**, bằng refspec tường minh `+refs/heads/main:refs/remotes/origin/main`, nên ref theo dõi nhánh
   của mình không bị cập nhật ngầm.
4. **`GIT_SEQUENCE_EDITOR=true`** chấp nhận danh sách todo mà `--autosquash` đã sắp: mỗi `fixup!` đứng ngay sau commit
   gốc với lệnh `fixup`. Xung đột thì `rebase --abort` trả nhánh về nguyên trạng.
5. **`--force-with-lease=refs/heads/<nhánh>:<lease>`**: server chỉ cập nhật khi nhánh trên server vẫn bằng `lease`
   (rỗng: chưa tồn tại). Bị từ chối thì dừng và chỉ cách xem commit lạ. Nhánh local lúc đó đã được rebase; bản cũ vẫn
   còn ở `ORIG_HEAD` và reflog.

## Vì sao lease ngầm định không đủ

`git push --force-with-lease` không kèm giá trị so remote với **ref theo dõi của bạn**, `origin/<nhánh>`. Lệnh
`git fetch origin` (hay IDE tự fetch nền) cập nhật ref đó thành commit của Hoa. Lease khi đó "khớp" và push ghi đè
commit của Hoa, đúng như `--force`. Hai cách sửa:

| Cách | Ý nghĩa | Ghi chú |
| --- | --- | --- |
| `--force-with-lease=<ref>:<sha>` với `sha` ghi lại trước fetch | So với đúng thứ bạn đã thấy | Không phụ thuộc fetch nền; dùng được trong script |
| `--force-with-lease --force-if-includes` (Git 2.30+) | Từ chối nếu tip trên remote chưa từng nằm trong reflog nhánh local của bạn, tức bạn chưa từng tích hợp nó | Nên đặt `push.useForceIfIncludes=true` cho người dùng tương tác |
| `--force` | Ghi đè vô điều kiện | Không dùng trên nhánh có người khác; branch protection nên chặn force-push trên `main` |

## Khi nào không rebase

- **Nhánh dùng chung** (`main`, `release/*`, nhánh nhiều người cùng làm): rebase đổi SHA, mọi người phải reset theo, và
  commit của họ dễ mất. Dùng merge, hoặc `git revert` để đảo thay đổi đã push.
- **Khi PR sẽ được squash-merge**: dọn `fixup!` không còn cần, vì mọi commit gộp thành một khi merge. Rebase chỉ để có
  CI chạy trên `main` mới nhất; GitHub có nút "Update branch", và merge queue làm việc đó tự động.
- **Commit đã ký**: rebase tạo commit mới, chữ ký cũ mất; người rebase phải ký lại bằng khoá của mình.

Quy tắc ngắn cho team: rebase thoải mái nhánh **của riêng bạn** trước khi người khác dựa vào nó; khi đã có người khác
push lên, chỉ dùng lease tường minh, hoặc chuyển sang merge.
