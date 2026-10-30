# Lời giải: file export "bẩn" từ ERP

## Cách làm

- `detect_encoding`: kiểm BOM trước (`raw.startswith(codecs.BOM_UTF8)` → `utf-8-sig`, để BOM không dính vào tên cột
  đầu tiên thành `﻿Facture`), thử giải mã UTF-8, thất bại thì `cp1252`. Thứ tự quan trọng: `cp1252` giải mã được
  gần như mọi chuỗi byte, nên nếu thử nó trước thì tệp UTF-8 cũng "đọc được" nhưng `é` thành `Ã©` (mojibake).
- `sniff_delimiter`: đếm từng ứng viên trên **dòng tiêu đề**, không trên cả tệp (mô tả sản phẩm có thể chứa dấu phẩy).
  `csv.Sniffer` cũng làm được việc này nhưng hay đoán sai trên tệp có dòng mở đầu.
- `read_export`: tách dòng, bỏ phần trên dòng `Facture` và dòng `Total`, đưa vào `pd.read_csv` với `sep`, `decimal`
  và `dtype` ghi rõ, đổi tên cột theo `RENAME`, parse ngày bằng `format="%d/%m/%Y %H:%M"`.
- `control_total`: tìm dòng `Total lignes`, tách theo delimiter, lấy số.
- `summarize`: định nghĩa chung của track; `nunique()` của `Customer ID` tự bỏ giá trị thiếu.

## Con số trên tệp thật

| Đại lượng | Giá trị |
| --- | --- |
| Dòng / control total | 1 580 / 1 580 |
| Hoá đơn / hoá đơn huỷ | 76 / 12 (35 dòng) |
| Khách có mã / dòng không mã | 40 / 49 |
| Dòng hợp lệ | 1 544 (bỏ 35 dòng huỷ và 1 dòng giá 0) |
| Doanh thu | 31 758.71 GBP |
| Phí vận chuyển `POST` | 49 dòng hợp lệ, 2 538.00 GBP, 8.0% doanh thu |
| Doanh thu dòng không có `Customer ID` | 421.62 GBP |

Đối chiếu với tệp gốc (sheet `Year 2010-2011`, lọc France và tháng 11/2011): 1 580 dòng, 31 758.71 GBP, khớp tuyệt đối.

## Giải thích trắc nghiệm

- **default-read (b)**: mặc định pandas giải mã UTF-8; byte `0xe9` là `é` trong cp1252 (`Période`) nhưng không hợp lệ
  trong UTF-8, nên lỗi ngay ở dòng đầu. Đây là lỗi "tốt": nó dừng bạn lại.
- **silent-one-column (d)**: tệp không có dấu phẩy nào, pandas coi cả dòng là một cột: 1 583 dòng (gồm dòng mở đầu,
  dòng tiêu đề thật và dòng tổng) × 1 cột, không lỗi. Luôn kiểm `df.shape` và `df.columns` sau khi đọc.
- **forgot-decimal (a)**: `"2,55"` không phải số theo mặc định nên cả cột thành chuỗi. Nhân chuỗi với số nguyên trong
  pandas **không lỗi** mà lặp chuỗi (`"2,55" * 3 = "2,552,552,55"`), tổng chuỗi là ghép chuỗi. Lỗi kiểu này đi tới tận
  báo cáo nếu không kiểm `dtypes`.
- **month-first (c)**: 685 dòng có ngày ≤ 12 parse "được" theo kiểu tháng trước, rơi vào tháng 1, 2, 3, 4, 7, 8, 9, 10;
  chỉ 117 dòng ngày 11/11 trùng hợp đúng. 895 dòng còn lại (ngày > 12) thành `NaT`. Nếu dùng `errors="coerce"` rồi
  `dropna()`, báo cáo mất 57% dòng và chia sai tháng phần còn lại mà không ai biết.
- **revenue (a)**: 31 758.71. 30 697.51 là cộng cả dòng huỷ (giá trị âm), 29 220.71 là bỏ thêm phí vận chuyển,
  32 819.91 là cộng giá trị dòng huỷ như số dương.
- **postage-share (c)**: 2 538 / 31 758.71 = 8.0%. Doanh thu gộp của track tính cả `POST`; khi báo "doanh thu sản
  phẩm" phải nói rõ có bỏ phí vận chuyển hay không.
- **int64-customer (d)**: cột số nguyên có ô trống bị pandas đổi thành `float64` (vì `NaN` là số thực), mã khách thành
  `12674.0`; ghép với bảng khác có mã `12674` (int hoặc chuỗi) sẽ lệch. `Int64` giữ số nguyên và có `<NA>`.
- **control-total (b)**: control total là con số hệ thống nguồn tự đếm. Số dòng đọc được khác nó nghĩa là mất dòng
  (dòng có ký tự lạ, dòng xuống hàng trong mô tả) hoặc thừa dòng (đọc cả dòng tổng như dữ liệu).
