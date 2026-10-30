---
title: Phân rã doanh thu mùa cao điểm thành price, volume, mix, sản phẩm mới (Online Retail II)
level: intermediate
services: []
files:
  - path: starter/pvm.ipynb
    note: 3 hàm TODO (doanh thu theo mã, PVM bridge, hiệu ứng từng mã) + đọc 4 câu hỏi
  - path: tests/test_pvm.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/13-business-financial-analytics/exercises/intermediate/01-price-volume-mix/starter/pvm.ipynb
  - uv run pytest tracks/data-analyst/modules/13-business-financial-analytics/exercises/intermediate/01-price-volume-mix -q
---

## Mục tiêu

Trả lời câu "doanh thu tăng nhờ giá, nhờ lượng hay nhờ mix?" bằng price-volume-mix bridge ở cấp mã hàng, tách
riêng sản phẩm mới và sản phẩm ngừng bán, rồi kiểm xem "giá" trong bridge có phải là giá niêm yết hay không trước
khi khuyên tăng giá.

## Đề bài

Bộ `online-retail-ii`, **cả hai sheet** (ghép, bỏ phần trùng 01-09/12/2010), quy tắc dòng hợp lệ dùng chung của
track. Chỉ xét hàng hoá (`StockCode` bắt đầu bằng chữ số). So mùa cao điểm tháng 9-11/2011 với tháng 9-11/2010.
Mở `starter/pvm.ipynb`:

1. `product_sales(tx, start, end)`: mỗi mã hàng một dòng, cột `revenue`, `units`, `price` (giá bình quân thực thu).
2. `pvm_bridge(p0, p1)`: năm hiệu ứng `price`, `volume`, `mix`, `new`, `lost` (công thức trong notebook), cộng lại
   đúng bằng thay đổi doanh thu.
3. `product_effects(p0, p1)`: hiệu ứng giá và hiệu ứng lượng của từng mã chung.
4. Chạy các cell `explore`: bridge, waterfall, mã kéo hiệu ứng giá xuống (kèm min / median / max giá của từng mã),
   mã mới lớn nhất. Trả lời bốn câu ở cuối notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy
   notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: lọc dòng hợp lệ, mã phí, kỳ nửa mở, `StockCode` trộn kiểu; bridge đúng công thức và
  cộng đúng tổng; trường hợp không đổi gì; hiệu ứng từng mã cộng lại bằng bridge.
- Trên bộ thật: 3 323 mã ở kỳ 2010, 3 224 mã ở kỳ 2011 (2 481 mã chung); doanh thu hàng hoá 3 405 332 → 3 594 878 GBP;
  bridge giá −117 399, lượng −690 654, mix +82 547, mã mới +1 180 727, mã ngừng −265 676 GBP.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`common = p0.index.intersection(p1.index)`; `p1.drop(common)` là mã mới, `p0.drop(common)` là mã ngừng. Tỉ trọng
số lượng tính trên **sản phẩm chung** của từng kỳ, không phải trên mọi mã.

### Gợi ý 2

Kiểm nhanh: `price + volume + mix` phải bằng doanh thu kỳ 1 trừ kỳ 0 của sản phẩm chung, sai số làm tròn. Nếu
lệch, thường là do lấy tỉ trọng trên toàn bộ mã hoặc nhân `price` với số lượng kỳ 0.
