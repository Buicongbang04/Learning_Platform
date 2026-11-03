# Lời giải: DVC remote trên MinIO

```bash
dvc remote add -d storage "$URL"
dvc remote modify storage endpointurl "$ENDPOINT"
dvc push "$FILE"
```

- `remote add -d` ghi `url` và đặt `core.remote = storage` trong `.dvc/config`; `modify endpointurl` thêm dòng trỏ SDK S3 vào MinIO thay vì AWS.
  Cả hai nằm trong `.dvc/config`, được commit: đồng đội clone về là có cấu hình remote.
- Khoá truy cập **không** thuộc về `.dvc/config`. Có ba chỗ hợp lệ: biến môi trường `AWS_*` (như bài này, hợp với CI), `~/.aws/credentials`,
  hoặc `dvc remote modify --local storage access_key_id ...` (vào `.dvc/config.local`, đã nằm trong `.gitignore` do `dvc init`).
- Nội dung trên remote được lưu theo hash: `<tiền-tố>/files/md5/ab/cdef...`. Hai repo cùng đẩy một tệp giống hệt sẽ dùng chung một đối tượng (dedup theo nội dung).
- `dvc pull` trên máy cache trống đọc con trỏ `.dvc` trong Git, tải đúng đối tượng về cache rồi dựng tệp. Nếu quên `dvc push` trước khi
  đồng đội pull, họ gặp lỗi "missing cache" dù Git đã đủ: đó là lỗi hay gặp nhất khi làm việc nhóm.
- Đổi `endpointurl` rồi chạy trong CI: dùng `dvc remote modify --local` hoặc biến môi trường thay vì sửa `.dvc/config` của repo.
