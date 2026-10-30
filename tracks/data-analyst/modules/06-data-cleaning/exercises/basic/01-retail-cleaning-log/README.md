---
title: Làm sạch Online Retail II có nhật ký - đối soát doanh thu với kế toán
level: basic
services: []
files:
  - path: starter/cleaning_log.ipynb
    note: 3 hàm TODO + đọc nhật ký
  - path: tests/test_cleaning_log.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/06-data-cleaning/exercises/basic/01-retail-cleaning-log/starter/cleaning_log.ipynb
  - uv run pytest tracks/data-analyst/modules/06-data-cleaning/exercises/basic/01-retail-cleaning-log -q
---

## Mục tiêu

Biến "em đã làm sạch dữ liệu" thành một bảng nhật ký người khác kiểm được: mỗi bước loại dòng có lý do, số dòng,
số tiền, và cộng lại khớp từ tổng thô tới con số cuối cùng. Đồng thời tập các phép chuẩn hoá kiểu và chuỗi mà dữ
liệu đọc từ Excel luôn cần.

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2009-2010`** (525 461 dòng). Kế toán trưởng hỏi vì sao doanh thu hàng hoá của
team data lệch sổ kế toán. Mở `starter/cleaning_log.ipynb`, làm lần lượt:

1. `normalize(tx)`: `Invoice`, `StockCode` (viết hoa), `Country` thành chuỗi đã bỏ khoảng trắng hai đầu;
   `Description` bỏ khoảng trắng hai đầu và gộp khoảng trắng liền nhau; `Customer ID` thành `Int64`.
2. `clean_with_log(tx)`: chuẩn hoá, rồi lần lượt bỏ dòng theo 5 lý do `cancelled`, `non_positive_quantity`,
   `non_positive_price`, `fee_code`, `exact_duplicate` (mỗi dòng ghi cho lý do đầu tiên nó vi phạm). Trả
   `(clean, log)`; `log` có cột `reason`, `rows_removed`, `rows_left`, `revenue_removed`.
3. `missing_report(df)`: số ô thiếu và tỉ lệ thiếu theo cột, sắp giảm dần.
4. Chạy các cell `explore`: bảng đối soát số thô → số cuối, bar số dòng bị loại theo lý do, doanh thu từng mã phí,
   dữ liệu thiếu trước và sau làm sạch. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Thiếu `Customer ID` không phải lý do loại dòng. Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: mã chữ thường `post`, `m` bị bắt như mã phí; hai dòng chỉ khác khoảng
  trắng hoặc hoa thường của mã bị coi là trùng; dòng huỷ có mã phí được ghi cho `cancelled`; nhật ký cộng lại khớp.
- Trên bộ thật: nhật ký loại 10 206 / 2 121 / 1 569 / 2 273 / 6 830 dòng, còn 502 462 dòng; doanh thu hàng hoá
  9 805 717.59 GBP; 102 908 dòng còn lại thiếu `Customer ID`.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Viết các quy tắc thành một dict `{lý do: hàm nhận df trả mặt nạ}` rồi lặp theo `REASONS`. Sau mỗi bước gán
`df = df[~mask]`, nên bước sau chỉ thấy các dòng còn lại; đó là điều làm "lý do đầu tiên" đúng và làm nhật ký cộng
lại khớp.

### Gợi ý 2

`df.duplicated(keep="first")` so mọi cột, coi hai ô thiếu là bằng nhau. `astype("Int64")` (chữ I hoa) giữ ô thiếu
là `<NA>`; `astype(int)` sẽ báo lỗi khi gặp `NaN`. Mô tả: `.str.strip().str.replace(r"\s+", " ", regex=True)`.
