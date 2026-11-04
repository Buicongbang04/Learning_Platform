# M02: Bundle offline và installer idempotent

## Mục tiêu

Báo cáo M01 đã qua tay IT khách: cài được, máy không ra internet. Giờ bạn chuẩn bị **thứ sẽ mang vào**: một bundle
dựng trên laptop của bạn, chứa đúng bản `quillo` team product giao, mọi công cụ máy khách thiếu, installer và script
kiểm tra; cộng một danh sách sha256 để phía khách biết bundle tới nơi còn nguyên.

Trước khi mang tới khách, FDE tập cài trên lab của chính mình. Milestone này chấm installer trên máy lab `lab-open`
(có mạng, có Docker và compose, không có registry nội bộ): installer phải chạy lại được bao nhiêu lần cũng được mà
không phá thứ đang chạy, vì ở hiện trường bạn **sẽ** phải chạy lại (mất kết nối giữa chừng, IT hỏi "chạy lại cho chắc").

Dựa trên [module 02](../../modules/02-packaging-delivery/README.md): manifest sha256, image tarball, installer idempotent
có preflight và log; và báo cáo M01 của bạn (preflight của installer kiểm đúng những gì báo cáo nói).

## Việc cần làm

1. **Lấy bản phát hành.** Team product giao `quillo-1.0.0.tar` (dựng bằng
   `nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist` ở repo
   học) cùng sha256 của nó qua một kênh riêng. `delivery/fetch_release.sh` chép tệp từ thư mục `QUILLO_RELEASE_DIR`,
   kiểm sha256 với giá trị bạn ghim trong repo, **trừ khi** biến `QUILLO_RELEASE_SHA256` được đặt (khi đó dùng giá trị
   đó: bản dựng lại có sha khác, xem README sản phẩm). Sai sha thì dừng, không để lại gì trông như bundle hoàn chỉnh.
   Tệp tar **không** vào Git.
2. **Mang công cụ máy khách thiếu.** Binary docker compose độc lập v5.6.1 linux/amd64, sha256
   `47737f4236e6d3ccea7291995203f8f018058783b4c3a9469119811a0b5db8c0` (bản đã ghim ở module 03). Nếu biến `COMPOSE_BIN`
   trỏ tới một binary sẵn có thì dùng nó, ngược lại tự tải từ GitHub Releases; cả hai trường hợp đều kiểm sha ghim.
3. **`make bundle`** dựng bundle cho một site vào `BUNDLE_DIR`:

   ```bash
   make bundle SITE=lawfirm-staging BUNDLE_DIR=dist/bundle-lawfirm-staging QUILLO_RELEASE_DIR=~/releases
   ```

   - `SITE` chọn cấu hình theo site. Cần ít nhất hai site: `lab` (máy lab của bạn: không có registry nội bộ, image
     nạp tại chỗ) và `lawfirm-staging` (máy của khách, dùng ở M03). Cấu hình site (registry, địa chỉ bind, cổng…) đi
     trong bundle; installer đọc nó, không hỏi gì khi chạy.
   - Bundle là một **thư mục**, ở gốc có: `quillo-1.0.0.tar` (giữ nguyên byte), `REQUIREMENTS.yaml` (đúng tệp trong
     bản phát hành, để preflight dùng), `install.sh`, `verify.sh`, `tools/docker-compose`, các tệp khác bạn cần, và
     `SHA256SUMS` theo định dạng `sha256sum` (đường dẫn tương đối từ gốc bundle) liệt kê **mọi** tệp trong bundle trừ
     chính nó.
   - **Tái lập được:** dựng lại cùng đầu vào vào cùng `BUNDLE_DIR` (đè lên bundle cũ) cho `SHA256SUMS` giống hệt từng
     byte. Không đưa thời gian, tên máy hay thứ tự ngẫu nhiên vào tệp nào được liệt kê.
   - `make bundle` chỉ ghi vào thư mục cha của `BUNDLE_DIR` (và thư mục cache của chính repo khi phải tải compose).
4. **`delivery/install.sh`** (chép vào bundle thành `install.sh`), chạy bằng root trên máy đích từ thư mục bundle:
   kiểm toàn vẹn → preflight theo `REQUIREMENTS.yaml` và cấu hình site → nạp image (và đưa lên registry nội bộ nếu site
   có) → `compose up` → kiểm `/healthz`. Project compose tên `quillo` (như `compose.yaml` của sản phẩm), API trả lời ở
   cổng 18080 của máy đích, **gọi được từ ngoài máy** (test gọi qua cổng forward của VM). Ghi log mỗi lần chạy. Chạy lại
   cùng bản: thoát `0`, không tạo lại hay restart container nào. Mật khẩu/token sinh tại chỗ, không đi trong bundle.
   Truy hết đường lỗi: lỗi ở bước nào thì dừng ở đó, nói rõ, ghi log; không thoát im lặng bằng `set -e` sau khi đã đổi
   máy.
5. **`delivery/verify.sh`** (chép vào bundle thành `verify.sh`), chạy bằng user `fde` trên máy đích: `/healthz` trả 200
   đúng version, đủ năm dịch vụ `db`, `llm`, `embed`, `api`, `worker` đang chạy; thoát `0` khi tất cả đạt, khác `0` khi
   có gì sai.
6. **`make install`** và **`make verify`** chạy hai script đó trên máy đích qua biến `SSH` (một tiền tố lệnh ssh đầy đủ,
   vd. `ssh -p 2222 fde@staging`; rỗng thì chạy tại máy hiện tại), bundle ở thư mục `REMOTE_BUNDLE` trên máy đích:

   ```bash
   make install SSH="ssh fde@staging" REMOTE_BUNDLE=/home/fde/bundle    # chạy: $(SSH) sudo bash $(REMOTE_BUNDLE)/install.sh
   make verify  SSH="ssh fde@staging" REMOTE_BUNDLE=/home/fde/bundle
   ```

Tự tập trên lab: `with fdekit.vm("lab-open", memory_mb=5120, forwards=(18080,)) as m:` rồi `m.put(bundle, "/home/fde/bundle")`.

## Kết quả nộp

`Makefile` (target `bundle`, `install`, `verify` thật), `delivery/fetch_release.sh`, `delivery/install.sh`,
`delivery/verify.sh`, cấu hình site và mọi script phụ, đã commit (không có tệp tar).

```bash
uv run pytest tracks/fde/capstone -k m02 -q      # ~2 phút, boot một VM lab-open 5120 MB
```

## Tiêu chí đạt

Mọi lệnh `make` của test chạy trên máy bạn trong sandbox bubblewrap (repo chỉ đọc, môi trường dựng lại từ đầu, chỉ
thư mục tạm của test ghi được) với `make -C <repo> <target> BIẾN=giá trị…`; test đặt `QUILLO_RELEASE_DIR` là
`tracks/fde/product/dist`, `QUILLO_RELEASE_SHA256` là sha256 của `quillo-1.0.0.tar` trong đó, `COMPOSE_BIN` là
`data/raw/fde-tools/docker-compose-v5.6.1/docker-compose-linux-x86_64`.

- [ ] `test_m02_bundle_reproducible`:
  - `make bundle SITE=lawfirm-staging BUNDLE_DIR=<tạm>/bundle …` thoát `0` trong 120 s; chạy lần hai cùng
    `BUNDLE_DIR` cũng thoát `0` và `SHA256SUMS` giống hệt từng byte lần đầu;
  - `SHA256SUMS` đúng định dạng `sha256sum`, liệt kê đúng tập tệp trong bundle (không thiếu, không thừa, trừ chính nó),
    mọi sha khớp;
  - có `quillo-1.0.0.tar` (sha bằng bản phát hành), `REQUIREMENTS.yaml` (giống hệt tệp trong tar),
    `install.sh`, `verify.sh`, `tools/docker-compose` (sha bằng bản ghim);
  - `QUILLO_RELEASE_SHA256` sai (64 số 0) thì `make bundle` thoát khác `0` và `BUNDLE_DIR` không có `SHA256SUMS`.
- [ ] `test_m02_installer_idempotent`: bundle `SITE=lab` chép vào `/home/fde/bundle` của một VM `lab-open` 5120 MB:
  - `make install SSH=<lệnh ssh của test> REMOTE_BUNDLE=/home/fde/bundle` thoát `0` trong 250 s;
  - `/healthz` qua cổng 18080 forward ra máy bạn trả 200 với `version` `1.0.0`;
  - project compose `quillo` có đủ `db`, `llm`, `embed`, `api`, `worker`, tất cả đang chạy;
  - chạy `make install` lần hai thoát `0`, mọi container giữ nguyên ID và `StartedAt`;
  - `make verify SSH=… REMOTE_BUNDLE=/home/fde/bundle` thoát `0` trong 60 s.
- [ ] Chưa có bản phát hành hoặc binary compose đã ghim thì test skip kèm lệnh cần chạy.
