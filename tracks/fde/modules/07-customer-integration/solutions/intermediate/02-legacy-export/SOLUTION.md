# Lời giải: export CSV của hệ thống cũ → tài liệu cho quillo

Lời giải ở `legacy_export.py` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/07-customer-integration/exercises/intermediate/02-legacy-export -q
```

Đo 2026-11-11 trên máy của repo: hai test trên host < 1 s; `test_quillo_ingests_documents` ~20 s (boot snapshot ~10 s,
worker nạp 12 tài liệu ngắn ~5 s).

## Ba chỗ hỏng của export (chỉ có ở đây)

1. **`HOPDONG.CSV` là Windows-1258 (cp1258)**, bảng mã tiếng Việt của Windows. Nó không có đủ chỗ cho mọi chữ có dấu
   dựng sẵn: chữ mang dấu thanh được lưu thành **chữ cơ sở + dấu thanh tổ hợp** (`ế` = `ê` 0xEA + dấu sắc 0xEC). Giải mã
   bằng `cp1258` cho đúng chữ trên màn hình nhưng ở dạng tổ hợp (NFD một phần): `"Số" != "Số"` khi so code point. Phải
   `unicodedata.normalize("NFC", …)` sau khi giải mã. Bỏ bước này thì tài liệu "nhìn đúng" nhưng tìm kiếm theo từ khoá,
   so khớp tên khách hàng, embedding đều lệch (đã chạy thử: test bắt ngay ở `samples`).
2. **`DOITAC.CSV` là Windows-1252 (cp1252)**, không phải Latin-1. Hai bảng mã trùng nhau trừ khoảng 0x80–0x9F, nơi cp1252
   đặt `€`, `“ ”`, `–`, `Œ œ`. Đọc bằng `latin-1` không bao giờ báo lỗi (mọi byte đều hợp lệ) nhưng biến `€` thành ký tự
   điều khiển U+0080. Đọc bằng `utf-8` thì lỗi ngay ở `é`.
3. **Định dạng địa phương**: dấu `;` (Excel tiếng Việt/tiếng Pháp dùng `;` vì `,` là dấu thập phân), ô có `;`, `"` và
   xuống dòng `\r\n` bên trong (trích dẫn kiểu CSV), ngày `dd/mm/yyyy` (có khi không có số 0 đầu: `5/3/2024`), tiền Việt
   `1.250.000.000`, tiền euro `12500,50`, và dòng tổng cuối export không có số hợp đồng.

## Cách làm

1. Đọc **byte**, giải mã đúng bảng mã của từng hệ thống với `errors="strict"` (sai bảng mã thì dừng to, không lặng lẽ
   sinh rác), chuẩn hoá NFC, rồi mới đưa cho `csv.reader(..., delimiter=";")` qua `io.StringIO(text, newline="")` để
   module `csv` tự xử lý xuống dòng trong ô.
2. Ngày: `datetime.strptime(v, "%d/%m/%Y")` (nhận cả `5/3/2024`). Tìm trong mẫu một bản ghi ngày > 12 để chắc thứ tự
   ngày/tháng; `03/05/2024` một mình không nói được gì.
3. Tiền: bỏ dấu chấm nghìn của VND rồi `int`; euro bỏ phân cách nghìn, đổi `,` thành `.`, `Decimal(...).quantize(0.01)`
   (không dùng `float` cho tiền).
4. Ghi tệp bằng tệp tạm `.…part` + `os.replace`, bỏ qua khi nội dung không đổi: chạy lại mỗi đêm không chạm tệp nào, worker
   không bao giờ thấy tệp ghi dở.

Cách đoán bảng mã khi khách chỉ gửi tệp: thử `decode` các ứng viên trên các byte ≥ 0x80 và xem chữ nào ra đúng tiếng Việt/
tiếng Pháp; hoặc hỏi IT "máy xuất export chạy Windows ngôn ngữ gì, phần mềm có phải Unicode không". Thư viện dò bảng mã
(`charset-normalizer`, có sẵn trong môi trường) đoán đúng cả hai tệp mẫu (`cp1258`, `cp1252`), nhưng đó vẫn là phỏng đoán
thống kê: tệp ngắn hay ít ký tự có dấu có thể bị đoán sang bảng mã gần giống. Chốt bảng mã theo hệ thống nguồn rồi ghi cứng
trong cấu hình, kiểm bằng vài bản ghi đã đối chiếu; đừng dò lại mỗi đêm.

## Biến thể sai đã chạy thử

- Giải mã `cp1258` nhưng không NFC: `test_samples` trượt ở ký tự thứ ~40 của tài liệu đầu (`'Số' vs 'Số'`).
- `DOITAC.CSV` bằng `latin-1`: trượt ở tài liệu có `€`/`“`/`Œ`.
- `pandas.read_csv(sep=";", encoding="cp1258")` rồi `pd.to_datetime` mặc định: trượt ngay vì thiếu NFC; sửa NFC rồi thì
  còn ngày, vì `to_datetime("03/05/2024")` mặc định đọc tháng trước (5 tháng 3) nếu không `dayfirst=True`/`format=`.

## Ở khách thật

- Hỏi IT có cấu hình export ra UTF-8 được không (nhiều phần mềm cũ có tuỳ chọn "Unicode"/"UTF-8 with BOM"); được thì
  vẫn giữ đường đọc bảng mã cũ cho dữ liệu lịch sử.
- Export là **ảnh chụp toàn bộ**: bản ghi bị xoá ở hệ thống cũ chỉ đơn giản là không còn trong lần export sau. Muốn xoá
  tài liệu tương ứng trong quillo thì so tập mã giữa hai lần export (như connector ở bài basic 02).
- Dữ liệu trong export là dữ liệu cá nhân và bí mật thương mại (tên khách, giá trị hợp đồng): tệp chỉ đi từ thư mục chia
  sẻ sang máy quillo trong mạng của khách; không mang về máy mình "để debug", dùng tệp mẫu đã ẩn danh (như `samples/`).
