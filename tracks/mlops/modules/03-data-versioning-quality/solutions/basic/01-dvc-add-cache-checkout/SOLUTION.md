# Lời giải: dvc add, cache, checkout

`track.sh`:

```bash
dvc add "$FILE"
git add "$FILE.dvc" "$(dirname "$FILE")/.gitignore"
git commit -q -m "track $FILE"
```

`dvc add` làm ba việc: băm nội dung (md5), chép (hoặc link) tệp vào `.dvc/cache/files/md5/<2 ký tự>/<phần còn lại>`,
và ghi con trỏ `<tệp>.dvc` (vài dòng YAML: `md5`, `size`, `path`). Nó cũng thêm tệp vào `.gitignore` cùng thư mục để Git
không bao giờ thấy dữ liệu. Thiếu `git add` cho `.gitignore` thì người khác clone về sẽ vô tình `git add` dữ liệu 2 GB.

`restore.sh`:

```bash
git checkout "$REV" -- "$FILE.dvc"
dvc checkout "$FILE"
```

`git checkout <rev> -- <đường dẫn>` chỉ lấy một tệp từ commit khác, `HEAD` đứng yên. `dvc checkout` so `md5` trong con trỏ với
tệp thật và dựng lại từ cache nếu khác. Phiên bản cũ vẫn còn trong cache vì DVC không xoá khi bạn `dvc add` bản mới, nên
quay lại là tức thì, không cần mạng. Con trỏ `.dvc` giờ khác `HEAD` (đó là phần thay đổi chưa commit): nếu muốn giữ, commit;
nếu không, `git checkout HEAD -- <tệp>.dvc && dvc checkout` để quay lại bản mới nhất.

Lỗi hay gặp: dùng `git checkout <rev>` (không có `--`) rồi quên `dvc checkout`, nên code ở phiên bản cũ nhưng dữ liệu vẫn là bản mới.
