# Lời giải: backup và kế hoạch chỗ chứa trước nâng cấp ở bệnh viện

## Chỗ hỏng (chỉ ghi ở đây)

Đĩa 8 GB của `hospital` không chứa nổi bundle 1.1.0 cộng bản backup mà vẫn giữ mức trống 15% IT yêu cầu. Số đo trên
snapshot `09-production-trust-hospital` (2026-11-11), trước khi test thêm 20–120 MiB dữ liệu xuất của bệnh viện:

| Thứ | Byte |
| --- | --- |
| Size của `/` | 8 132 173 824 |
| Mức trống tối thiểu (15%) | 1 219 826 073 |
| Đang trống khi boot | ~2 337 673 216 |
| Chỗ dùng được trên mức sàn | ~1 117 847 143 |
| `quillo-1.1.0.tar` | 1 168 076 800 (giải nén ra thêm chừng đó nữa) |
| Database `quillo` (`pg_database_size`, 12 hợp đồng, 362 chunk) | ~11 664 407 |
| Bản dump `-Fc` | ~1 405 541 |
| Đã dùng: `~/quillo-1.0.0.tar` (lưu trữ), `~/quillo-1.0.0/images/` (tar đã nạp), `~/quillo-1.0.0/models/` | 1 168 076 800, 530 472 448, 637 550 560 |

Chép nguyên bundle mới lên máy đã vượt mức sàn ~50 MB trước cả khi backup; giải nén nó thì hết đĩa thật (Postgres đang
chạy trên cùng đĩa sẽ dừng ghi). Bản dump nhỏ, nhưng "dump + bundle" là không vừa. Hai thứ trong máy lớn nhất mà dễ nghĩ
tới để xoá (bundle lưu trữ 1.0.0 và `images/` của bản cài) đều bị cấm đụng trước cửa sổ bảo trì.

## Hướng làm

1. **Đo trên máy, không giả định**: Size/Available của `/`, `pg_database_size`, rồi backup. `ops/backup.sh` tự từ chối khi
   đích không còn 2 × kích thước database; script kiểm thêm mức sàn của IT trước khi chạy.
2. **Backup online** bằng `ops/backup.sh /home/fde/backups` (pg_dump chạy trong container db, snapshot nhất quán, không
   dừng api/worker), giữ trên máy bệnh viện, thư mục 0700, tệp 0600, kèm `.sha256`.
3. **Restore thử** vào database tạm `restore_drill` trong cùng container db (không đụng database `quillo`), so số tài liệu
   và chunk, rồi xoá database tạm. Database 12 MB nên restore thử tốn vài giây và vài chục MB.
4. **Tính `stage` từ hai manifest và Docker của máy**: bỏ `chart/`; bỏ tệp có cùng sha256 với `~/quillo-1.0.0/manifest.json`
   (model GGUF, `ops/`, `migrations/0001`…); với `images/*.tar`, đọc `manifest.json` bên trong tar trên laptop lấy digest
   config, hỏi máy `docker image inspect <digest>`: `pgvector` và `llama.cpp` đã có (tar khác sha256 chỉ vì `docker save`
   lại, image giống hệt), chỉ `quillo-api` là mới. `stage` còn `.env.example`, `images/quillo-api.tar`,
   `migrations/0002_v1_1_tags.sql`: ~65 MB, máy còn ~1,0 GB trên mức sàn.
5. Mọi thứ đọc từ bundle chạy trên laptop; dữ liệu bệnh viện (dump, kết quả restore) chỉ có số đếm đi qua SSH.

Mã: `pre_upgrade.sh` cạnh tệp này.

## Phương án khác (đều giữ đủ bốn quy định)

- Không dùng image ID mà đặt cả ba `images/*.tar` vào `stage` (tar khác sha256 nên quy tắc không cho vắng): ~530 MB, vẫn
  còn ~0,6 GB trên mức sàn. Đúng, chỉ tốn chỗ và thời gian chép hơn.
- Backup vào thư mục khác trên `/` (vd. `/var/backups/quillo`, cần sudo để tạo và chown về `fde`): được, miễn đúng định
  dạng, quyền và không nằm trong `~/quillo-1.0.0/`.
- Kiểm dump bằng `pg_restore --list` thay cho restore thử: nhanh hơn nhưng chỉ chứng minh tệp đọc được, không chứng minh
  restore ra đúng dữ liệu. Bài này test tự restore để chấm, còn lời giải làm restore thử để chính bạn biết trước.

Không hợp lệ dù "chạy được": chép dump về laptop (dữ liệu bệnh viện rời máy), dừng api để backup (bác sĩ đang dùng), xoá
`images/` hay bundle lưu trữ để lấy chỗ (đụng bản cài đang chạy trước cửa sổ bảo trì).
