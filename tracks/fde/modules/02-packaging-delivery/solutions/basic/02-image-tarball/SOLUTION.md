# Lời giải: Soi image tarball trước khi mang đi

Lời giải ở `image_tar.py` cạnh tệp này:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/basic/02-image-tarball -q
```

## Cách làm

1. Mở tar một lần, lập bảng `tên -> TarInfo` của các tệp thường, đọc `manifest.json` (bỏ tiền tố `./` nếu có: `podman
   save` và vài công cụ cũ ghi kiểu đó).
2. Duyệt `Config` + `Layers`: không có thì `thiếu blob`; nằm dưới `blobs/sha256/` thì băm theo khối và so với tên.
3. Đọc config blob (chỉ khi blob đó còn nguyên) để lấy `os/architecture`, so với nền tảng cần.
4. Mọi lỗi đọc (`TarError`, `EOFError`, `OSError`, JSON hỏng, thiếu khoá) gom thành **một** dòng `không đọc được`: khi tar
   đã hỏng thì các phát hiện khác không còn đáng tin.

Ba vị trí cắt trong test cho ba kiểu hỏng khác nhau: cắt giữa layer ⇒ `tarfile` thấy layer nhưng đọc nội dung thì lỗi
`unexpected end of data` và mất luôn `manifest.json` phía sau; cắt trước `manifest.json` ⇒ tar "hợp lệ" nhưng thiếu tệp;
cắt giữa `manifest.json` ⇒ JSON hỏng. Lời giải nào chỉ dựa vào "`tarfile.open` có lỗi không" sẽ lọt ca thứ hai.

## Ngoài hiện trường

- **Sai kiến trúc là lỗi số một** của image build trên laptop Apple Silicon: `exec format error` lúc `docker run` ở máy
  khách x86. Ghim `--platform linux/amd64` khi build và khi `docker save`, rồi kiểm như bài này trước khi đóng bundle.
- **Lưu theo tag, không theo ID.** `docker save <image-id>` cho tar có `RepoTags: null`; khách `docker load` xong thấy
  `<none>:<none>` và compose không tìm được image.
- **Digest của tar ≠ digest trên registry.** sha256 của tệp `.tar` đổi theo cách đóng gói (thứ tự, timestamp); thứ bất biến
  là digest của manifest/config/layer bên trong. Manifest của bundle (bài 01) ghi sha256 của tệp tar để kiểm vận chuyển;
  danh sách image ghi tag **kèm** digest để kiểm nội dung.
- `docker save` của Docker ≥25 ghi cả `manifest.json` cũ lẫn OCI layout, nên `podman load`, `skopeo copy
  docker-archive:…` và `ctr images import` đều đọc được.
