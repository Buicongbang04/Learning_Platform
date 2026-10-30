---
title: Market basket trên Online Retail II - support, confidence, lift và luật nào đáng hành động
level: intermediate
services: []
files:
  - path: starter/basket_rules.ipynb
    note: 4 hàm TODO + đọc luật
  - path: tests/test_basket_rules.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/12-product-customer-analytics/exercises/intermediate/02-market-basket-rules/starter/basket_rules.ipynb
  - uv run pytest tracks/data-analyst/modules/12-product-customer-analytics/exercises/intermediate/02-market-basket-rules -q
---

## Mục tiêu

Tự tính support, confidence, lift để hiểu chúng nói gì và không nói gì, khai thác luật mua kèm cho cả catalogue bằng
`mlxtend`, kiểm luật có ổn định qua mùa, rồi chọn luật đưa cho merchandiser theo quy mô và hành động được.

## Đề bài

Merchandiser hỏi: **"Nên bày gì cạnh gì, combo nào đáng làm cho catalogue mùa tới?"**. Dữ liệu: bộ `online-retail-ii`
(UCI, CC BY 4.0), sheet `Year 2010-2011`, dòng hợp lệ theo định nghĩa dùng chung (`clean_sales` viết sẵn). Một hoá
đơn là một giỏ; chỉ xét mã hàng hoá (bắt đầu bằng 5 chữ số). Mở `starter/basket_rules.ipynb`:

1. `basket_matrix(lines)`: bảng `bool` giỏ × mã hàng hoá.
2. `rule_stats(basket, a, b)`: `support`, `confidence`, `lift` của luật `a ⇒ b`, tính tay từ hai cột.
3. `mine_rules(basket, min_support)`: FP-Growth + `association_rules` của `mlxtend`, chỉ luật một mã ⇒ một mã, cột
   `antecedent`, `consequent`, `support`, `confidence`, `lift`, sắp theo lift; bảng rỗng đúng cột khi không có cặp nào.
4. `stable_rules(r1, r2)`: luật có mặt ở cả hai bảng.
5. Chạy các cell khám phá: mã phổ biến nhất, luật lift cao nhất và support cao nhất, số luật theo `min_support`,
   scatter support × lift, luật của hai nửa năm. Đọc theo câu hỏi cuối notebook. Báo cáo bài học: làm phần trắc
   nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên giỏ nhỏ sinh trong test pass: bỏ mã phí và hoá đơn chỉ có phí, một mã nhiều dòng vẫn là một, lift đối
  xứng còn confidence thì không, chỉ luật một-một có lift ≥ 1, bảng rỗng đúng cột.
- Trên bộ thật: 19 773 giỏ × 3 900 mã; 176 luật với min support 2%; luật lift cao nhất 16.13 giữa hai màu tách trà
  Regency; hai nửa năm có 172 và 340 luật, chung 106.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`pairs = lines[["Invoice", "StockCode"]].astype(str)`, lọc `pairs.StockCode.str.match(r"^\d{5}")`, `drop_duplicates()`,
rồi `pd.crosstab(pairs.Invoice, pairs.StockCode).gt(0)` (hoặc `pivot_table` với `aggfunc="any"`). Với hai cột `bool`,
`(basket[a] & basket[b]).mean()` là support.

### Gợi ý 2

`association_rules` trả `antecedents`, `consequents` là `frozenset`: lọc `apply(len) == 1` rồi lấy phần tử duy nhất
bằng `next(iter(s))`. Kiểm trước khi gọi: nếu không itemset nào có từ 2 mã thì trả `pd.DataFrame(columns=...)`.
`merge(on=["antecedent", "consequent"], suffixes=("_1", "_2"))` cho luật chung.
