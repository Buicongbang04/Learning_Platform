# Lời giải: cài shellcheck từ release chính thức và chứng minh đã kiểm

Nhật ký mẫu ở `install-log.md`, tệp hash ở `shellcheck.sha256` cạnh tệp này. Cả hai ghi cho `v0.11.0` trên
`linux.x86_64`; máy khác nền tảng hoặc phiên bản thì `SOLUTION=1` skip đúng một test (so hash binary), vì binary của
bạn khác binary trong lời giải.

## Cách làm

1. **Chốt phiên bản và nền tảng trước khi tải.** Ghi vào biến: `SC_VERSION=0.11.0`, `SC_PLATFORM=linux.x86_64`. Không
   dùng URL kiểu `latest`: hôm nay và tuần sau tải ra hai tệp khác nhau, hash ghim sẵn không còn đúng, và bạn không
   tái lập được máy.
2. **Có hash chuẩn trước khi tải.** shellcheck không phát hành tệp checksum riêng. Hash trong bảng của `## 0. Cài đặt`
   lấy từ trường `digest` mà GitHub tự tính cho mỗi asset (hiện trên trang release và qua API). Lệnh `curl ... | jq`
   trong log đọc lại trường này để đối chiếu với hash đã ghim: hai nguồn khớp nhau thì mới tải.
3. **Tải vào thư mục tạm riêng** (`mktemp -d`), không tải vào thư mục đang làm việc: tệp tải về là dữ liệu chưa tin
   được, không để nó nằm cạnh script của bạn.
4. **Kiểm rồi mới giải nén và cài.** `sha256sum -c` đọc tệp `<hash>  <tên>` và in `<tên>: OK`; sai thì in `FAILED` và
   trả mã khác 0. Trong script thật, dòng kiểm đứng trước `tar` và script chạy với `set -e`, nên hash sai là dừng.
5. **Cài bằng `install -m 0755`** thay cho `cp` rồi `chmod`: một lệnh, quyền đúng ngay từ đầu, ghi đè bản cũ an toàn.
   Đích là `~/.local/bin`, nằm trong home nên không cần `sudo`, và nằm trong `PATH` mặc định của nhiều distro (Ubuntu
   thêm nó qua `~/.profile` khi thư mục tồn tại).
6. **Xác nhận bản đang chạy chính là bản đã kiểm.** `which shellcheck` phải trả `~/.local/bin/shellcheck`; hash của
   tệp đó ghi vào `shellcheck.sha256` để test so với tệp thật. Đây là chỗ hay sai nhất: máy đã có bản apt
   (`/usr/bin/shellcheck`) đứng trước trong `PATH`, bạn cài xong vẫn chạy bản cũ mà không biết.
7. **Ghi cách gỡ.** Binary đơn lẻ thì gỡ bằng một `rm`; `hash -r` xoá cache đường dẫn của shell hiện tại.

## Checksum chống được gì

| Rủi ro | Checksum SHA-256 đã ghim | Chữ ký (GPG, cosign, attestation) |
| --- | --- | --- |
| Tải hỏng giữa chừng | Có | Có |
| Mirror, proxy hoặc CDN tráo tệp | Có, nếu hash lấy từ kênh khác kênh tải | Có |
| Tài khoản phát hành bị chiếm, release bị thay cả tệp lẫn hash | Không, nếu bạn ghim hash sau khi release bị thay | Có, nếu khoá ký không bị lộ |
| Mã độc có sẵn trong mã nguồn upstream | Không | Không |

Vì vậy hash nên được ghim **một lần** vào repo (hướng dẫn, Ansible, Dockerfile) và review như code, không tải lại
mỗi lần cài. jq phát hành cả `sha256sum.txt` lẫn `jq-attestation.json` (kiểm bằng `gh attestation verify`), mạnh hơn
shellcheck ở hàng thứ ba.

## Vì sao cấm pipe script vào `sudo bash`

- Script chạy với quyền root trước khi bạn kịp đọc; server trả nội dung khác nhau theo User-Agent được (đọc trên
  trình duyệt thấy sạch, `curl` nhận bản khác).
- Kết nối đứt giữa chừng thì shell chạy nửa script; dòng `rm -rf /opt/tool` bị cắt còn `rm -rf /` là kịch bản có thật.
- Không có phiên bản, không có hash, không tái lập được. Lần sau chạy lại ra máy khác.

Khi nhà cung cấp chỉ phát hành script cài đặt: tải về tệp, đọc, kiểm hash hoặc chữ ký nếu có, rồi mới chạy, và ưu
tiên tuỳ chọn cài vào thư mục user.

## Những chỗ test bắt

- Phiên bản ghi trong log khác bản đang chạy: hay gặp khi cài xong quên mở shell mới, hoặc có hai bản trong `PATH`.
- Nền tảng sai: tải `aarch64` cho máy `x86_64` thì binary không chạy (`cannot execute binary file: Exec format error`).
- Bước kiểm checksum đứng sau bước cài: kiểm sau khi đã chạy thì không còn ý nghĩa.
- Dòng binary trong `.sha256` không khớp tệp `which` trả về: bạn đang chạy một tệp khác tệp đã kiểm.
