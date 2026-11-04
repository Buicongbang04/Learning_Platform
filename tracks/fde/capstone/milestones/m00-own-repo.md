# M00: Repo capstone riêng của bạn

## Mục tiêu

Hợp đồng đầu tiên: phòng pháp chế của một tập đoàn mua `quillo` và muốn thử trên một máy staging do IT của họ quản.
Trước khi đụng vào máy khách, bạn mở một repo Git **riêng** cho cả hợp đồng này, như một dự án triển khai thật: mọi
script khảo sát, bundle, installer, báo cáo gửi khách và runbook bàn giao sẽ nằm ở đây suốt 17 milestone, rồi thành
portfolio public trên GitHub.

Hai điều làm repo này khác một repo bài tập:

- **Tự chứa.** Người khác clone repo về phải chạy được mà không cần repo học: không import `testkit`/`fdekit`, không trỏ
  đường dẫn tuyệt đối vào repo học. Bộ chấm ở repo học chỉ *nhìn vào* repo của bạn qua `FDE_CAPSTONE_DIR`.
- **Sạch secret.** Đây là repo của một hợp đồng với khách có dữ liệu mật. Khoá SSH của lab, `.env`, chứng chỉ, token
  quillo, dữ liệu CUAD và bundle ~1,1 GB không bao giờ được commit; `.gitignore` chặn từ ngày đầu, trước khi có tệp nào
  như vậy.

Dựa trên [module 00](../../modules/00-introduction/README.md) (một tuần của FDE, quillo và các hồ sơ khách) và phần "Capstone là
một repo riêng" trong [README capstone](../README.md).

## Việc cần làm

1. Tạo repo **ngoài** repo học, vd. `~/projects/quillo-lawfirm-deployment`, `git init`. Thư mục này phải là **gốc** của
   repo Git của nó (không phải thư mục con của repo khác).
2. Trỏ bộ chấm vào repo:

   ```bash
   # setup/.env của repo học
   FDE_CAPSTONE_DIR=/home/<bạn>/projects/quillo-lawfirm-deployment
   ```

3. Viết các tệp ở gốc repo và `git add` (hoặc commit) chúng; bộ chấm đọc danh sách tệp bằng `git ls-files`:
   - `README.md` dạng **case study** của một FDE: khách là ai và cần gì, ràng buộc (dữ liệu không rời máy, không
     internet, IT khách quản máy), kiến trúc dự kiến, cách chạy. Ít nhất 4 phần `## ` (ngoài khối code). README sẽ dày
     dần qua các milestone; hôm nay ghi những gì bạn đã biết.
   - `LICENSE` không rỗng (MIT là lựa chọn hợp lý cho script của bạn; bundle quillo và model có giấy phép riêng, ghi
     chú điều đó).
   - `.gitignore` chặn tối thiểu: khoá và chứng chỉ (`*.pem`, `*.key`, `id_*`), `.env` ở mọi thư mục, mọi tệp `.tar`
     (bundle), dữ liệu CUAD và thư mục build của bạn.
   - `Makefile` có bốn target `survey`, `bundle`, `install`, `verify`. Hôm nay mỗi target có thể chỉ là
     `@echo "chưa làm: m01"`; các milestone sau thay bằng lệnh thật.
4. Đặt sẵn thư mục cho các milestone tới (vd. `survey/`, `reports/`, `delivery/`), không bắt buộc.
5. (Nên làm) Tạo repo public trên GitHub và push. Trước lần push đầu: `git ls-files` và đọc lại từng tệp.

Không chép lời giải tham chiếu (`tracks/fde/capstone/solutions/project/`) sang repo của bạn: bạn chỉ có một lần làm
portfolio này.

## Kết quả nộp

Repo Git riêng ở `FDE_CAPSTONE_DIR` với `README.md`, `LICENSE`, `.gitignore`, `Makefile` đã `git add`.

```bash
uv run pytest tracks/fde/capstone -k m00 -q
```

## Tiêu chí đạt

- [ ] `test_m00_layout`: `FDE_CAPSTONE_DIR` là gốc của một repo Git; `git ls-files` có `README.md`, `LICENSE`,
  `.gitignore`, `Makefile` ở gốc; `README.md` có ít nhất 4 dòng bắt đầu bằng `## ` nằm ngoài khối code; `LICENSE` không
  rỗng; `make -n survey bundle install verify` thoát `0`. Lệnh `make` chạy trong sandbox bubblewrap: repo chỉ đọc,
  môi trường dựng lại từ đầu (`HOME` là thư mục repo), nên `Makefile` không được dựa vào biến môi trường riêng của bạn.
- [ ] `test_m00_standalone`: không tệp văn bản nào được `git ls-files` liệt kê chứa dòng bắt đầu bằng `import testkit`,
  `import fdekit`, `from testkit`, `from fdekit`, chuỗi `-m testkit`/`-m fdekit`, tên tệp `testkit.py`/`fdekit.py`,
  đường dẫn tuyệt đối của repo học (`str(ROOT)` của bộ chấm), hay đường dẫn dạng `/DataScience…/tracks`,
  `/DataScience…/setup`, `/DataScience…/testkit`, `/DataScience…/fdekit` (nhắc tên repo học thì không sao).
- [ ] `test_m00_no_secrets_committed`: `git ls-files` không có tệp tên `*.pem`, `*.key`, `id_*`, `.env` hay `.env.*`
  (trừ `.env.example`) ở bất kỳ thư mục nào; không tệp nào chứa dòng `-----BEGIN ... PRIVATE KEY-----`, hay
  `QUILLO_ADMIN_TOKEN=`/`QUILLO_DB_PASSWORD=` theo sau là một giá trị ≥16 ký tự; `git check-ignore --no-index` xác nhận
  `.gitignore` chặn đủ tám đường dẫn `lab.pem`, `keys/id_ed25519`, `tls/server.key`, `.env`, `delivery/.env`,
  `quillo-1.0.0.tar`, `dist/bundle/quillo-1.0.0.tar`, `data/cuad/contract.pdf` (dữ liệu CUAD).
- [ ] Repo trống, chưa đặt `FDE_CAPSTONE_DIR` hay chưa `git init` thì test skip hoặc fail kèm lời nhắc, không bao giờ
  tính là đạt.
