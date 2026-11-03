---
title: "Hiện trường: cài dừng giữa chừng, service không lên"
level: intermediate
services: []
files:
  - path: starter/install.sh
    note: Installer hiện tại của team, chạy tốt trên lab; bạn sửa
  - path: beacon/make_bundle.py
    note: Dựng bundle beacon ngay trong VM (không sửa)
  - path: tests/test_field_install.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - nice -n 15 uv run python -m fdekit prepare hospital
  - uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/intermediate/02-install-stops-midway -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Một ticket thật từ khách, không kèm chẩn đoán. Bạn phải tự tái hiện, tìm nguyên nhân trên máy của khách (không phải máy
lab), sửa installer sao cho nó chạy được ở cả hai nơi, và để lần sau nếu vẫn không cài được thì khách **không mất dịch vụ
đang chạy**.

## Đề bài

Dịch vụ `beacon` và định dạng bundle giống bài intermediate 01 (đọc phần Đề bài ở đó). `starter/install.sh` là installer
team đang dùng: đã qua QA trên máy lab (`lab-open`), cài 1.0.0 rồi nâng lên 1.1.0 (bản kèm model mới) đều ổn.

Ticket từ IT bệnh viện (máy `hospital`):

> Chiều nay bên em chạy `sudo bash install.sh beacon-1.1.0.tar` theo hướng dẫn để nâng cấp từ 1.0.0. Script chạy được
> một lúc thì dừng giữa chừng, báo lỗi rồi thoát. Từ lúc đó beacon không lên nữa, khoa đang không dùng được. Bản 1.0.0
> trước giờ vẫn chạy bình thường. Bên em không sửa gì trên máy.

Sửa `starter/install.sh` (giữ nguyên cách gọi `sudo bash install.sh <bundle.tar>`). Test làm cùng một kịch bản trên
`lab-open` và trên `hospital`, mỗi máy một VM:

1. Dựng trong VM bundle 1.0.0, bundle 1.1.0 (model mới), và bundle 1.2.0 bị chép thiếu (tar cụt).
2. Cài 1.0.0, rồi nâng lên 1.1.0, rồi thử cài 1.2.0.

Mỗi lần chạy installer ≤200 s. Bạn tự boot máy khách để điều tra được: `fdekit.vm("hospital", memory_mb=1024,
forwards=(8088,))` rồi `m.ssh(...)`, hoặc `ssh` bằng `m.ssh_command()`.

## Tiêu chí đạt

`test_upgrade_with_new_model[lab-open]` và `test_upgrade_with_new_model[hospital]`, trên mỗi máy:

- Cài 1.0.0 thoát `0`; `/healthz` trả version `1.0.0` và `weights_sha256` đúng sha256 của model trong manifest.
- Nâng lên 1.1.0 thoát `0`; trong 120 s `/healthz` trả `1.1.0` và `weights_sha256` đúng model mới.
- Cài bundle 1.2.0 bị cụt thoát khác `0`, và sau đó dịch vụ vẫn phục vụ `1.1.0` với đúng model; dịch vụ vẫn `enabled`.

## Gợi ý

### Gợi ý 1

Tái hiện trước khi sửa: chạy đúng kịch bản trên VM `hospital` và đọc **toàn bộ** output của installer, không chỉ mã thoát.
Rồi so hai máy bằng những lệnh bạn đã dùng ở module 01.

### Gợi ý 2

Hỏi hai câu riêng: vì sao cài **thất bại**, và vì sao thất bại lại làm **mất dịch vụ cũ**. Câu sau quan trọng với khách hơn.

### Gợi ý 3

Với mỗi bước của installer, ước lượng nó cần thêm bao nhiêu và ở đâu, rồi cộng lại.
