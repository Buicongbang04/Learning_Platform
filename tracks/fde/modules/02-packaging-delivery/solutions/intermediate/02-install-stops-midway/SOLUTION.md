# Lời giải: Hiện trường "cài dừng giữa chừng, service không lên"

Lời giải ở `install.sh` cạnh tệp này (cùng installer với lời giải intermediate 01):

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/intermediate/02-install-stops-midway -q
```

Đo 2026-11-04: `lab-open` 26 s, `hospital` 42 s (starter: `lab-open` pass, `hospital` fail sau 33 s).

## Nguyên nhân: đĩa 8 GB của bệnh viện, không phải lỗi code

Máy `hospital` có đĩa ảo 8 GB, `/` và `/tmp` cùng một filesystem (Ubuntu 20.04 không mount `/tmp` riêng). Đo trong VM
bằng `df -P -B1M /`:

| Thời điểm | Còn trống |
| --- | --- |
| Vừa boot | 6 168 MiB |
| Sau khi cài 1.0.0 (model 4 MiB) | 6 160 MiB |
| Sau khi chép bundle 1.1.0 (`beacon-1.1.0.tar` = 2 400 MiB model + vài KB) | 3 760 MiB |

Installer cũ cần thêm **hai lần** kích thước bundle: giải nén vào `mktemp -d` (`/tmp`, 2 400 MiB), rồi `cp -a` sang
`/opt/beacon/current` (thêm 2 400 MiB). Tổng 4 800 MiB > 3 760 MiB: `cp` báo `No space left on device` khi đã chép được
khoảng 1,3 GiB model. Trên `lab-open` (đĩa 20 GB, ~18 GiB trống) cùng các bước đó dư chỗ, nên QA không bao giờ thấy.

Vì sao **mất dịch vụ**: installer dừng `beacon` và xoá `/opt/beacon/current` *trước* khi chép bản mới; `set -e` thoát ngay
ở lệnh `cp` lỗi, để lại `current` dở dang và dịch vụ đã dừng. `trap` dọn `/tmp`, nên lúc IT nhìn lại thì đĩa đã trống,
"không thấy gì bất thường".

## Cách sửa (lời giải)

1. **Không chép hai lần.** Giải nén thẳng vào `releases/.<v>.partial` nằm cạnh chỗ cài (cùng filesystem với `/opt`),
   kiểm sha256 tại chỗ, rồi `mv -T` (đổi tên, không tốn chỗ). Cần thêm 1× bundle thay vì 2×: 2 520 MiB (kể cả biên 5% +
   64 MiB) < 3 760 MiB. Sau khi cài còn ~1 360 MiB.
2. **Preflight dung lượng từ manifest**, trước mọi thay đổi: `size` trong manifest cho biết cần bao nhiêu mà không giải
   nén. Thiếu chỗ ⇒ dừng với thông báo có số liệu (`cần 2520 MiB, còn 1200 MiB ở /opt/beacon/releases`).
3. **Dịch vụ cũ chạy tới phút cuối.** Chỉ đổi symlink `current` + restart sau khi bản mới đã nằm đủ và đúng trên đĩa;
   không lên thì quay về. Bundle cụt (1.2.0) chết ở bước giải nén/kiểm tra, dịch vụ 1.1.0 không bị đụng.

Các cách sửa khác cũng đạt test: giải nén trong `/tmp` rồi `mv` (cùng filesystem nên là đổi tên); giải nén thẳng từ tar
qua pipe vào chỗ cài. **Không** đạt: đổi `TMPDIR` sang `/var/tmp` (cùng đĩa), "dọn bớt log" của khách, hay xin khách
xoá bundle 1.0.0 (không đủ, và không phải việc của khách).

## Quy trình ngoài hiện trường

1. **Khôi phục dịch vụ trước, điều tra sau.** Chạy lại installer 1.0.0 (bundle cũ còn trên máy) hoặc trỏ lại release cũ:
   khoa cần dùng được ngay, nguyên nhân để sau.
2. **Đọc output đầy đủ**: dòng `cp: error writing ... No space left on device` có trong `/var/log/beacon/install.log`; IT chỉ
   gửi "báo lỗi rồi thoát". Luôn xin log, đừng xin ảnh chụp màn hình.
3. **So hai máy bằng số**: `df -h /`, `df -h /tmp`, `findmnt /tmp` trên cả lab và khách. Survey module 01 đã có
   `disk_free_gb_max = 7` cho `hospital`; preflight của sản phẩm phải dùng con số đó *với kích thước bundle cụ thể*.
4. **Trả lời khách** (ngắn, không đổ lỗi): "Bản cập nhật mang model mới ~2,4 GB; installer cũ cần tạm gấp đôi chỗ trống
   và đĩa của máy không đủ. Chúng tôi đã khôi phục 1.0.0 lúc …, gửi installer mới cần ~2,5 GB và tự kiểm chỗ trống trước
   khi đụng vào bản đang chạy. Về lâu dài đề nghị nới đĩa lên ≥20 GB vì mỗi bản model sau sẽ lớn hơn."
5. **Sửa quy trình QA**: thêm máy "đĩa nhỏ" vào ma trận kiểm thử; một lab "không tật" chỉ chứng minh được happy path.
