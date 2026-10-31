# Lời giải: cứu commit sau reset --hard nhầm và nhánh đã xoá

Script đầy đủ ở `rescue.sh` cạnh tệp này.

## Cách làm

1. **Một hàm cho cả hai việc.** `value_before <ref> <tiền tố subject>` đọc reflog của ref, mới nhất trước, gặp mục
   khớp tiền tố thì trả SHA của mục liền sau (cũ hơn), tức giá trị của ref **trước** thao tác đó.
2. **Tip đã mất của `main`**: `value_before refs/heads/main "reset: "`. Mục reset gần nhất là `HEAD~3`; giá trị trước
   nó là commit "refund endpoint". Lần reset cũ hơn (bỏ tệp debug) bị bỏ qua vì hàm dừng ở mục khớp đầu tiên.
3. **Tip của nhánh đã xoá**: reflog của chính nhánh bị xoá cùng nhánh, nhưng reflog của `HEAD` vẫn còn. Mỗi lần
   `switch` ghi `checkout: moving from A to B`, và `HEAD` ngay trước mục đó là tip của `A` lúc rời đi.
4. **Kiểm hết rồi mới ghi.** Cả hai SHA và cả hai nhánh đích được kiểm trước; nhánh đã tồn tại ở đúng commit thì coi
   như xong (idempotent), ở commit khác thì dừng. Không bao giờ ghi đè một ref mà người dùng có thể đang cần.
5. **`git update-ref` thay vì checkout.** Tạo ref không động vào index hay working tree, nên phần sửa dở của Lan vẫn
   nguyên. `-m` ghi lý do vào reflog của nhánh mới.

## Vì sao `main@{1}` sai

`main@{1}` là giá trị của `main` trước **thao tác cuối cùng** trên `main`. Ngay sau `reset --hard` thì đúng, nhưng Lan
đã commit hotfix: thao tác cuối là commit đó, và `main@{1}` là kết quả của reset. Tương tự, `@{-1}` là nhánh checkout
trước đó (`docs/runbook` hay `main` tuỳ thứ tự), không phải `feature/pix-payment`. Cứu dữ liệu bằng reflog cần
**đọc** reflog (`git reflog show main`), không đoán số.

## Các công cụ khác

| Cách | Khi nào dùng |
| --- | --- |
| `git reflog` / `git log -g` | Mọi thao tác trên máy này trong 90 ngày (mục unreachable: 30 ngày, `gc.reflogExpireUnreachable`) |
| `ORIG_HEAD` | Ngay sau `reset`, `merge`, `rebase`: `git reset --hard ORIG_HEAD` hoàn tác thao tác vừa làm |
| `git fsck --lost-found` / `git fsck --unreachable` | Reflog đã mất (clone khác, reflog bị xoá) nhưng object chưa bị `gc` |
| Remote, CI, PR | Commit đã push: lấy lại từ server, PR đã đóng vẫn giữ ref `refs/pull/<n>/head` trên GitHub |
| Clone của đồng nghiệp | Không ai push và reflog mất: hỏi ai đã fetch nhánh đó |

Phòng hơn chữa: push nhánh feature sớm (kể cả draft PR), bật branch protection để `main` trên server không bị
force-push, và đặt alias `git config --global alias.undo 'reset --soft HEAD~1'` thay cho thói quen `reset --hard`.
Thao tác nguy hiểm đầu tiên khi đi cứu dữ liệu là `git gc --prune=now`: đừng chạy nó cho tới khi đã cứu xong.
