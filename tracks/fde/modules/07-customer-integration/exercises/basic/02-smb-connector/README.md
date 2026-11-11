---
title: "Connector file share → inbox: chỉ giao cái đã đổi"
level: basic
services: []
files:
  - path: starter/sync_share.py
    note: Bản đầu chép hết share mỗi lần chạy; bạn viết lại
  - path: tests/test_smb_connector.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - uv run pytest tracks/fde/modules/07-customer-integration/exercises/basic/02-smb-connector -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Công ty luật để hợp đồng trên một share Windows (SMB) theo cây thư mục của từng phòng. Quillo nạp tài liệu từ thư mục
`inbox`; worker nạp xong thì **chuyển tệp đi** (`inbox/done/…`). Bạn viết connector chạy định kỳ (cron, systemd timer)
đưa tài liệu từ share sang inbox: tệp mới và tệp đổi nội dung được giao đúng một lần, giữ nguyên đường dẫn (ACL theo
thư mục của quillo cần nó), tệp bị xoá ở nguồn được xử lý đúng, và chạy lại khi không có gì đổi thì không làm gì. Máy
chạy quillo không có `smbclient`, `cifs-utils` hay quyền mount: connector dùng client SMB thuần Python
([`smbprotocol`](https://github.com/jborean93/smbprotocol), đã ghim trong môi trường của repo).

## Đề bài

Viết lại `starter/sync_share.py`. Cách chạy:

```sh
python sync_share.py --server HOST --port PORT --share contracts --user svc-quillo --password-file PATH \
    --inbox DIR --state FILE
```

- `--password-file`: tệp chứa mật khẩu của `svc-quillo` (bỏ ký tự xuống dòng cuối).
- `--state`: tệp trạng thái của connector (bạn tự chọn định dạng); chưa có thì coi như lần chạy đầu. Thư mục chứa nó
  đã tồn tại.
- Dòng **cuối** của stdout là một object JSON `{"added": [...], "updated": [...], "deleted": [...], "errors": [...]}`;
  mỗi phần tử là đường dẫn tương đối trong share, phân tách bằng `/`, giữ nguyên tên tiếng Việt.

Quy tắc:

1. Tệp có trong share mà connector chưa từng giao ⇒ chép vào `inbox/<đường dẫn>` (tạo thư mục con), báo `added`.
2. Bỏ qua tệp rác của Windows/macOS: tên bắt đầu bằng `~$`, `Thumbs.db`, `desktop.ini`, `.DS_Store` (không phân biệt
   hoa thường). Chúng không được giao và không xuất hiện trong báo cáo.
3. Tệp có **mtime và kích thước** trùng lần chạy trước ⇒ coi là không đổi và **không được mở để đọc**.
4. mtime hoặc kích thước đổi ⇒ đọc lại: nội dung khác bản đã giao ⇒ giao lại (ghi đè nếu bản cũ còn chờ trong inbox),
   báo `updated`; nội dung y hệt ⇒ không giao, không báo.
5. Tệp đã giao mà không còn trong share ⇒ báo `deleted`; nếu bản connector đã giao **vẫn còn chờ** ở đúng đường dẫn đó
   trong inbox thì gỡ nó khỏi inbox.
6. Connector chỉ đụng tệp nó giao: không bao giờ sửa/xoá `inbox/done/`, `inbox/failed/` hay tệp người khác thả vào
   inbox.
7. Một tệp không đọc được ⇒ ghi vào `errors`, các tệp khác vẫn xử lý; lần chạy sau thử lại tệp đó. Có `errors` thì thoát
   `1`, không thì `0`.
8. Không có gì đổi ở share ⇒ báo cáo bốn mảng rỗng và inbox giữ nguyên từng tệp (nội dung, mtime, inode).

Test dựng share Samba thật (`fdekit.customer_site("lab-open", memory_mb=1024, extra_services=("fileshare",))`, SMB3,
share chỉ đọc) và chạy script của bạn trên host trong sandbox (`testkit.run_sandboxed`), tới share qua cổng host
`s.fileshare_host`, 5 lần liên tiếp với cùng `--state`. Giữa các lần, test sửa share (thêm, sửa, chỉ đổi mtime, xoá,
tước quyền đọc của một tệp) và đóng vai worker của quillo (chuyển tệp từ inbox sang `inbox/done/`). Nội dung tệp sinh
ngẫu nhiên mỗi lần chạy test. Cả bài ~15 s trên máy của repo.

## Tiêu chí đạt

`test_incremental_sync`, mỗi lần chạy xong trong 60 s:

- Lần 1 (inbox rỗng): `added` đúng 5 tệp thật của share (không có tệp rác), inbox chứa đúng 5 tệp đó cùng nội dung,
  đúng thư mục.
- Lần 2: worker đã chuyển 2 tệp sang `done/`, người dùng thả một tệp vào `inbox/Tài chính/`, một tệp không đổi bị tước
  quyền đọc trên share ⇒ báo cáo rỗng, thoát `0`, inbox không đổi.
- Lần 3: một tệp sửa nội dung, một tệp chỉ đổi mtime, hai tệp bị xoá ở nguồn (một đã sang `done/`, một còn chờ), một
  tệp mới ở thư mục con mới, một tệp mới không đọc được ⇒ đúng `added`/`updated`/`deleted`/`errors`, thoát `1`; tệp còn
  chờ bị gỡ, `done/` và tệp của người dùng nguyên vẹn, tệp chỉ đổi mtime không bị giao lại.
- Lần 4: tệp lỗi đọc được rồi ⇒ chỉ nó trong `added`, thoát `0`.
- Lần 5: báo cáo rỗng, inbox không đổi.

## Gợi ý

### Gợi ý 1

Worker của quillo dọn inbox sau khi nạp. Vậy connector biết "đã giao tệp này rồi" bằng cách nào?

### Gợi ý 2

Liệt kê thư mục qua SMB đã trả về thông tin của từng tệp. Mỗi lời gọi lấy thông tin riêng cho một tệp là thêm một lượt
mở handle trên server, và với `smbclient` bạn phải truyền `port=` ở **mọi** lời gọi (một lời gọi quên `port` sẽ thử
cổng 445).

### Gợi ý 3

Script có thể chết giữa chừng (mất mạng, máy restart). Ghi tệp vào inbox và ghi tệp trạng thái thế nào để lần sau chạy
lại vẫn đúng, và worker không bao giờ nạp một tệp chép dở?
