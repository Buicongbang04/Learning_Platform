---
title: Một sản phẩm, nhiều tên - chuẩn hoá và dedupe fuzzy tên sản phẩm Online Retail II
level: intermediate
services: []
files:
  - path: starter/product_dedupe.ipynb
    note: 4 hàm TODO + kết luận cho Head of Merchandising
  - path: tests/test_product_dedupe.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/06-data-cleaning/exercises/intermediate/01-product-name-dedupe/starter/product_dedupe.ipynb
  - uv run pytest tracks/data-analyst/modules/06-data-cleaning/exercises/intermediate/01-product-name-dedupe -q
---

## Mục tiêu

Phân biệt hai bài toán dedupe hay bị trộn lẫn: **cùng khoá, nhiều nhãn** (chọn nhãn chuẩn là đủ) và **khác khoá,
nhãn gần giống** (fuzzy matching chỉ cho ứng viên, phải kiểm trước khi gộp). Biết dùng blocking để fuzzy matching
chạy được trên máy yếu, và biết vì sao similarity cao không có nghĩa là trùng.

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2010-2011`**. Head of Merchandising cần bảng top sản phẩm theo doanh thu và nhờ
"gộp các món bị ghi nhiều tên". Notebook cho sẵn `valid_lines(tx)` (dòng hợp lệ theo định nghĩa dùng chung,
`StockCode` viết hoa, bỏ mã phí, cột `revenue`). Mở `starter/product_dedupe.ipynb`:

1. `normalize_description(s)`: viết hoa, ký tự ngoài `[A-Z0-9&]` thành một khoảng trắng, bỏ khoảng trắng hai đầu.
2. `canonical_names(lines)`: theo `StockCode`, tên chuẩn là mô tả có nhiều dòng nhất (hoà lấy tên nhỏ nhất theo chữ
   cái) và `n_variants` là số mô tả khác nhau.
3. `fuzzy_pairs(names, threshold=0.9)`: cặp tên cùng từ đầu tiên (blocking) có
   `SequenceMatcher(..., autojunk=False).ratio() >= threshold`; cột `a`, `b`, `score`.
4. `likely_same(a, b)`: `True` khi hai tên chỉ khác thứ tự từ, hoặc khác đúng một từ là lỗi chính tả (không có chữ
   số, dài ít nhất 4 ký tự, ratio của hai từ ít nhất 0.8).
5. Chạy các cell `explore`: số mã gộp được nhờ viết hoa, mã có nhiều tên nhất, doanh thu lệch nếu gom theo mô tả, các
   cặp fuzzy và các cặp qua quy tắc, top 10 sản phẩm. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy
   notebook.

Các hàm không được sửa DataFrame đầu vào. Chỉ dùng thư viện chuẩn `difflib` cho similarity.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: chuẩn hoá giữ ô thiếu, quy tắc hoà của tên chuẩn, blocking theo từ đầu,
  thứ tự và điểm của các cặp, các trường hợp `likely_same` (đổi thứ tự, lỗi chính tả, khác số, từ ngắn, khác hai từ).
- Trên bộ thật: 527 789 dòng, 3 803 mã, 193 mã có hơn một mô tả, mã nhiều tên nhất là `23196`
  (`VINTAGE LEAF MAGNETIC NOTEPAD`); 589 cặp fuzzy ở ngưỡng 0.9, không cặp nào qua `likely_same`.
- Trắc nghiệm trong app: đúng ít nhất 5/7 câu.

## Gợi ý

### Gợi ý 1

`groupby(["StockCode", "desc"]).size()` rồi `sort_values(["StockCode", "n", "desc"], ascending=[True, False, True])`
và `drop_duplicates("StockCode")` cho tên chuẩn có quy tắc hoà tái lập được. Dùng `.to_numpy()` khi dựng DataFrame
mới để không bị lệch index.

### Gợi ý 2

Block: `unique.groupby(unique.str.split(" ").str[0])`. Túi từ: `Counter(a.split()) - Counter(b.split())` cho các từ
chỉ có ở `a` (kể cả số lần lặp); `.elements()` biến lại thành danh sách.
