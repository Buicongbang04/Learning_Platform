# Lời giải: doanh thu bị nhân bản, kiểm grain và fan-out

## Cách làm

1. **`key_profile`**: `df.groupby(keys, dropna=False).size()` cho số dòng mỗi khoá; `dropna=False` để khoá thiếu
   (khách vãng lai) không bị bỏ qua âm thầm. `duplicated_keys = (sizes > 1).sum()`,
   `is_unique = len(sizes) == len(df)`. Ép kiểu Python để kết quả in ra báo cáo và so sánh được.
2. **`join_inflation`**: `left.merge(right, on=on, how="left", suffixes=("", "_right"))`. Left join vì đó là
   phép mà dashboard dùng (không làm mất dòng), và hậu tố rỗng cho bên trái để cột `measure` giữ tên gốc kể cả khi
   `right` có cột trùng tên.
3. **`invoice_header`**: `groupby("Invoice", as_index=False).agg(...)` với `first` cho thuộc tính, `min` cho giờ,
   `size` và `sum` cho số đo, rồi `sort_values(..., ignore_index=True)`.
4. **`aov`**: `revenue.sum() / Invoice.nunique()`: tổng hợp lên grain hoá đơn rồi mới chia.

Lời giải đầy đủ ở `fanout_audit.ipynb` cùng thư mục.

## Vì sao như vậy

- **Ứng viên khoá phải được kiểm, không được đoán.** `(Invoice, StockCode)` lặp ở 9 566 cặp; thêm `Quantity`,
  `Price` vẫn còn 4 845 cặp lặp. Cặp lặp nhiều nhất là hoá đơn 555524, mã 22698: 20 dòng, mỗi dòng 1 cái, cùng giờ.
  Trông như lỗi trùng, nhưng khả năng cao là quầy ghi mỗi lần quét một dòng; xoá đi là mất 19 cái hàng đã bán. Chỉ
  nghiệp vụ xác nhận được, nên model giữ mọi dòng và khoá bằng số thứ tự dòng nguồn.
- **Fan-out không đều, nên còn tệ hơn sai số đều.** Tổng tăng 12.27%, nhưng theo quốc gia (12 nước lớn nhất) dao
  động từ 6.7% (Japan) tới 24.5% (Spain), tuỳ khách nước đó mua bao nhiêu mã có nhiều mô tả. `85123A` (mã hàng bán
  chạy, hai mô tả WHITE/CREAM) bị nhân đôi: 104 519 thành 209 038 GBP. Merchandising so sánh quốc gia hay sản phẩm
  trên dashboard đó sẽ rút kết luận sai, không chỉ "số to hơn một chút".
- **Sửa ở model, không ở dashboard.** Chia cho 1.123 hay thêm `DISTINCT` vào truy vấn dashboard là băng dán: hệ
  số đổi theo thời gian, và `DISTINCT` trên dòng doanh thu sẽ xoá nhầm dòng thật. Cách bền: dựng bảng sản phẩm một
  dòng mỗi mã (bài Basic 02) và gắn test `unique` để lần sau build đỏ.
- **Metric ở grain của nó.** Trung bình `revenue` mỗi dòng (20.12 GBP) trả lời "một dòng hàng đáng bao nhiêu",
  không phải "một đơn đáng bao nhiêu" (534.40 GBP). Gắn tổng hoá đơn vào từng dòng rồi cộng nhân mỗi hoá đơn theo
  số dòng của nó: 728 triệu GBP, gấp 68.25 lần. Con số này lớn hơn trung bình 26.6 dòng mỗi hoá đơn vì hoá đơn
  nhiều dòng thường cũng là hoá đơn giá trị lớn: phép nhân có trọng số lệch về phía hoá đơn lớn.

## Con số tham chiếu (bộ thật, sheet `Year 2010-2011`)

| Đại lượng | Giá trị |
| --- | --- |
| Dòng hợp lệ, doanh thu | 530 105, 10 666 702.54 GBP |
| `(Invoice, StockCode)`: khoá khác nhau, khoá lặp, nhiều nhất | 519 603; 9 566; 20 (hoá đơn 555524, mã 22698) |
| `naive_dim` | 4 161 dòng, 3 922 mã, 220 mã lặp, tối đa 4 mô tả (ví dụ `23236`) |
| Join `naive_dim` | 584 319 dòng (+54 214), 11 975 984.25 GBP, +12.27% |
| Fan-out theo quốc gia (12 nước lớn nhất) | Japan 6.7%, France 10.0%, United Kingdom 12.2%, Spain 24.5% |
| Hoá đơn | 19 960; trung bình 26.6 dòng, trung vị 15, lớn nhất 1 114 |
| AOV, trung bình dòng | 534.40, 20.12 GBP |
| Tổng hoá đơn cộng lặp | 728 003 912 GBP, gấp 68.25 lần |

## Đáp án trắc nghiệm

- `naive-inflation` (b) **khoảng 12.3%**. 3.7% (a) là tỉ trọng mã phí; 68 lần (c) là lỗi header.
- `country-spread` (d) **Spain**, 24.5%; Japan (b) thấp nhất, 6.7%.
- `header-multiple` (a) **khoảng 68 lần**. 26.6 (b) là số dòng trung bình mỗi hoá đơn: nếu mọi hoá đơn cùng giá trị
  thì hệ số đúng bằng số đó, nhưng hoá đơn nhiều dòng cũng là hoá đơn lớn.
- `aov-value` (c) **aov 534.40, trung bình dòng 20.12**. 541.11 (b) là trung bình của 13 AOV tháng.
- `repeated-scan` (b): giữ và hỏi. Xoá (a) hay gộp thành Quantity 1 (c) làm mất hàng đã bán nếu đó là quét từng cái;
  gộp đúng phải cộng `Quantity` (thành 20), và đó vẫn là quyết định nghiệp vụ. Bỏ cả hoá đơn (d) xoá doanh thu thật.
- `fix-location` (d): sửa ở bảng sản phẩm và chặn bằng test. (a) hệ số đổi theo dữ liệu; (b) `DISTINCT` xoá nhầm
  dòng thật trùng giá trị; (c) không sửa gì.
