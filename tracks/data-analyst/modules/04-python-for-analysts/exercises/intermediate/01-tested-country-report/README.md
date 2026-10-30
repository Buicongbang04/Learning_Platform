---
title: Hàm báo cáo doanh thu theo quốc gia dùng lại mỗi quý, kèm test bắt được lỗi thật
level: intermediate
services: []
files:
  - path: starter/report.py
    note: 3 hàm TODO (làm sạch, tổng hợp theo quốc gia, so hai kỳ có top + Other)
  - path: starter/checks_report.py
    note: Test của bạn, ít nhất 4 hàm test_*
  - path: tests/test_report.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run pytest tracks/data-analyst/modules/04-python-for-analysts/exercises/intermediate/01-tested-country-report/starter/checks_report.py -q
  - uv run pytest tracks/data-analyst/modules/04-python-for-analysts/exercises/intermediate/01-tested-country-report -q
---

## Mục tiêu

Biến một phân tích hay bị làm lại bằng tay mỗi quý ("doanh thu theo quốc gia, so với quý trước") thành **một module
Python dùng lại được**, có định nghĩa rõ ràng và **test do chính bạn viết**. Test tốt không phải test pass, mà là test
**fail khi có lỗi**: bộ chấm cố ý làm hỏng hàm của bạn theo bốn kiểu lỗi hay gặp và kiểm test của bạn có bắt được không.

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2010-2011`**. Mỗi đầu quý, Head of Sales hỏi cùng một câu: *"Quý vừa rồi các thị
trường thế nào so với quý trước? Thị trường nào mới, thị trường nào mất?"*. Analyst trước làm bằng notebook copy-paste,
mỗi quý ra con số hơi khác một chút. Bạn viết lại thành `starter/report.py`:

1. `clean_transactions(tx)`: dòng hợp lệ theo định nghĩa chung của track (bỏ hoá đơn `C`, `Quantity <= 0`,
   `Price <= 0`; `Invoice` ép `str`), thêm `revenue = Quantity * Price`.
2. `country_summary(tx, start, end)`: mỗi quốc gia một dòng trong kỳ nửa mở `[start, end)`, cột `revenue`, `orders`
   (số hoá đơn khác nhau), `customers` (số `Customer ID` khác nhau), `aov`, `share`; sắp `revenue` giảm dần.
3. `compare_periods(tx, current, previous, top=None)`: ghép hai kỳ bằng **outer merge có `validate`**, cột `revenue`,
   `revenue_prev`, `change`, `growth` (`NaN` khi kỳ trước bằng 0), `status` (`both`, `new`, `lost`); `top=N` gộp phần
   còn lại thành dòng `Other` (`status` = `other`). Docstring trong file ghi đủ định nghĩa.

Rồi viết `starter/checks_report.py`: ít nhất **4** hàm `test_*` trên dữ liệu nhỏ tự tạo, import từ `report`. File có
sẵn một test mẫu (AOV) để bạn theo. Bộ chấm chạy test của bạn trên `report.py` của bạn (phải pass hết), rồi trên bốn
bản `report.py` bị cài lỗi; mỗi bản lỗi phải làm ít nhất một test của bạn fail. Bốn lỗi được giấu trong
`tests/test_report.py`; hãy tự nghĩ trước khi mở file đó: một báo cáo như thế này hay sai lặng lẽ ở đâu?

## Tiêu chí đạt

- `report.py` pass test trên dữ liệu nhỏ: làm sạch theo dòng, kỳ nửa mở, đếm khác nhau, quốc gia mới/mất có doanh thu 0
  ở kỳ thiếu, `growth` `NaN` khi kỳ trước bằng 0, dòng `Other` giữ đúng tổng.
- Trên bộ thật, quý 3/2011 so với quý 2/2011: 30 quốc gia có đơn quý 3, tổng 2 536 950 GBP; Anh 4 192 hoá đơn, 1 939
  khách, 83.1% doanh thu; so hai kỳ có 33 quốc gia (29 cả hai, 1 mới, 3 mất: Bahrain, Brazil, USA), Anh +21.4%; `top=5`
  có dòng `Other` 157 318 GBP.
- `checks_report.py` có ít nhất 4 test, pass trên `report.py` của bạn, và bắt được cả bốn lỗi cài sẵn.

## Gợi ý

### Gợi ý 1

`groupby("Country").agg(revenue=("revenue", "sum"), orders=("Invoice", "nunique"), customers=("Customer ID",
"nunique"))`. So hai kỳ: `cur.merge(prev, left_index=True, right_index=True, how="outer", validate="one_to_one",
indicator=True)`; cột `_merge` cho biết `both`, `left_only`, `right_only`. Điền 0 cho doanh thu thiếu **trước** khi tính
`change`.

### Gợi ý 2

Mỗi test khoá **một định nghĩa** với dữ liệu nhỏ đến mức tính được bằng tay: một hoá đơn huỷ cạnh một hoá đơn thường;
một hoá đơn hai dòng của cùng một khách; một quốc gia chỉ có ở kỳ trước và một chỉ có ở kỳ này; một quốc gia mà doanh
thu kỳ này khác kỳ trước để kiểm mẫu số của `growth`. Muốn chắc test có tác dụng, tự làm hỏng `report.py` một chỗ và
xem test có đỏ không.
