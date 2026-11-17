# Lời giải: nâng cấp 1.0.0 → 1.1.0 tại chỗ ở bệnh viện, rồi rollback

## Chỗ hỏng (chỉ ghi ở đây)

1. **Đĩa không chứa nổi hai bộ image/bundle.** Máy còn ~2,34 GB trống, mức sàn 15% là ~1,22 GB, nên chỉ có ~1,12 GB để
   làm việc. Cách nâng cấp "theo README cài đặt" (chép `quillo-1.1.0.tar` 1,17 GB lên máy, `tar xf`, `docker load` cả ba
   image) vượt mức sàn ngay khi chép xong, rồi hết đĩa thật giữa lúc giải nén: `tar` thoát 2 với `No space left on
   device`, trong khi Postgres của quillo đang ghi trên cùng đĩa. `docker load` còn cần thêm chỗ tạm trong `/var/lib/docker`
   trong lúc nạp.
2. **Hai bộ image phải cùng tồn tại cho tới khi nghiệm thu xong.** Dọn chỗ bằng cách xoá image `quillo-api:1.0.0` (hay
   `docker image prune -a`) sau khi 1.1.0 lên làm rollback hỏng: máy không ra internet, `docker compose up` với
   `QUILLO_VERSION=1.0.0` thử pull và thất bại. Đường lui khi đó là nạp lại từ bundle lưu trữ (`tar -xOf
   ~/quillo-1.0.0.tar quillo-1.0.0/images/quillo-api.tar | docker load`), rollback tham chiếu làm việc đó khi thiếu image.

Bẫy thứ ba không do máy mà do thói quen: "rollback = restore backup". Restore bản dump trước nâng cấp đưa database về
schema 1 và **xoá mọi tài liệu nạp trên 1.1.0** (phụ lục giá của Phòng Vật tư). Migration 0002 chỉ thêm cột có `DEFAULT`,
bản 1.0.0 chạy được trên schema 2 (README sản phẩm, mục "Bản phát hành"), nên rollback chỉ cần đổi image; backup là đường
lui cho trường hợp migration hỏng dữ liệu, không phải bước của rollback.

## Hướng làm

`upgrade.sh` (chạy trên laptop):

1. Đọc `manifest.json` từ bundle trên laptop, kiểm đúng bản 1.1.0; đọc version đang chạy, Size/Available của máy.
2. Backup trước khi đổi bất cứ thứ gì: `ops/backup.sh ~/backups` trên máy (bỏ qua khi máy đã chạy 1.1.0, để chạy lại
   script không tạo backup sau migration rồi nhầm nó là bản "trước nâng cấp").
3. Với mỗi `images/*.tar` của bundle: đọc digest config và tag từ `manifest.json` bên trong tar (trên laptop), hỏi máy
   `docker image inspect` tag đó có đúng digest không. Có rồi thì bỏ qua (pgvector, llama.cpp); chưa có thì kiểm sha256
   theo manifest trên laptop, kiểm chỗ trống (2 × kích thước tar trên mức sàn), rồi stream thẳng
   `tar -xOf "$BUNDLE" … | $SSH "docker load"`: không ghi tệp tạm nào lên đĩa máy ngoài phần docker tự cần.
4. Giữ bản sao cấu hình của bản đang chạy (`compose*.yaml`, `.env.example`, `manifest.json`, `.env`) trong
   `~/quillo-1.0.0/.release-1.0.0/`, rồi thay các tệp nhỏ của 1.1.0 (đã kiểm sha256) bằng ghi `*.new` + `mv` để mỗi tệp
   luôn ở trạng thái cũ hoặc mới, không dở dang.
5. Đổi `QUILLO_VERSION=1.1.0` trong `.env`, `docker compose up -d` (chỉ api và worker được tạo lại; db, llm, embed giữ
   nguyên), chờ `/healthz` báo đúng version.

`rollback.sh`:

1. Đếm tài liệu/chunk trước rollback.
2. Thiếu image `quillo-api:1.0.0` thì nạp lại từ bundle lưu trữ trên máy.
3. Trả cấu hình đã giữ ở bước 4, đổi `QUILLO_VERSION=1.0.0`, `up -d`, chờ version 1.0.0.
4. Đếm lại; số khác trước rollback thì dừng với lỗi. **Không** restore backup, **không** hạ schema: api 1.0.0 log cảnh báo
   `schema mới hơn bản đang chạy` và chạy bình thường; cột `tags` và dữ liệu của nó còn nguyên cho lần nâng cấp lại.

Đo trên máy của repo: cả test ~78 s (boot + chờ quillo ~25 s, `upgrade.sh` ~20 s gồm backup, stream 65 MB image và
`up -d`, `rollback.sh` ~15 s). Đĩa thấp nhất trong lúc nâng cấp còn ~2,2 GB.

Trạng thái khi script dừng giữa chừng (vd. bị Ctrl-C): trước bước 4 máy vẫn chạy 1.0.0 nguyên vẹn, chỉ có thêm backup
và image 1.1.0; trong bước 4 mỗi tệp cấu hình là bản cũ hoặc mới (compose của hai bản giống nhau); sau bước 5 thì
`rollback.sh` chạy được từ bất kỳ điểm nào vì nó không giả định gì ngoài bundle lưu trữ và `.env`. Chạy lại `upgrade.sh`
sau khi đã lên 1.1.0 không làm gì thêm ngoài kiểm.

## Điểm không quay lại

Với 1.0.0 → 1.1.0 không có: migration chỉ mở rộng schema. Nếu một bản sau có migration xoá hay đổi kiểu cột (bước
"contract"), rollback chỉ đổi image sẽ không còn đúng, và đường lui duy nhất là restore backup (mất dữ liệu ghi sau thời
điểm backup). Runbook phải ghi rõ mốc đó và CAB phải duyệt nó như một quyết định riêng.

## Phương án khác (đều giữ quy định của IT)

- Chép lên máy chỉ `images/quillo-api.tar` (65 MB) rồi `docker load -i`, xoá tệp sau khi nạp: đúng, tốn thêm một lần ghi.
- Chép cả ba `images/*.tar` (~530 MB) lên máy, rồi nạp từng cái và xoá ngay: đã chạy qua test, đĩa thấp nhất ~1,65 GB
  (~0,43 GB trên mức sàn), `upgrade.sh` ~26 s. Chậm hơn và phí, nhưng hợp lệ.
- Rollback bằng `docker compose` với tệp compose override ghim tag cũ thay cho sửa `.env`: được, miễn `.env` cuối cùng
  phản ánh bản đang chạy (giám sát và backup đêm của IT đọc nó).
