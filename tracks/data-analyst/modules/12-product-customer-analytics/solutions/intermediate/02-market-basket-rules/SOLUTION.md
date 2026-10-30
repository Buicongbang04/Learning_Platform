# Lời giải: market basket trên Online Retail II

## Cách làm

1. **`basket_matrix`**: ép `Invoice`, `StockCode` sang chuỗi (xlsx trộn số và chuỗi), lọc mã hàng hoá bằng
   `^\d{5}`, `drop_duplicates()` cặp giỏ × mã, `pd.crosstab(...).gt(0)`. Lọc mã trước khi dựng bảng nên hoá đơn chỉ có
   `POST` không thành một giỏ rỗng (giỏ rỗng làm mọi tỉ lệ nhỏ đi).
2. **`rule_stats`**: ba tỉ lệ `mean()` trên cột `bool`. Support là xác suất chung, confidence chia cho xác suất của
   vế trái, lift chia tiếp cho xác suất vế phải. Lift = 1 là độc lập.
3. **`mine_rules`**: `fpgrowth` (nhanh hơn `apriori` trên 3 900 cột) rồi `association_rules(metric="lift",
   min_threshold=1.0)`; lọc luật một-một; đổi `frozenset` thành chuỗi. Kiểm trước trường hợp không có itemset hai mã:
   `association_rules` trên bảng không có cặp nào không cho luật nào, và trả bảng rỗng đúng cột giúp code phía sau
   (merge, sort) không vỡ.
4. **`stable_rules`**: `merge` inner theo cặp mã.

## Số liệu trên bộ thật

| Chỉ số | Giá trị |
| --- | --- |
| Giỏ × mã | 19 773 × 3 900; trung vị 15 mã mỗi giỏ |
| Mã phổ biến nhất | WHITE HANGING HEART T-LIGHT HOLDER (85123A) 11.1%; JUMBO BAG RED RETROSPOT 10.6%; REGENCY CAKESTAND 3 TIER 10.1% |
| Luật (min support 3% / 2% / 1%) | 20 / **176** / 1 788 |
| Lift cao nhất | GREEN ⇔ PINK REGENCY TEACUP AND SAUCER: support 3.2%, lift 16.13; confidence PINK ⇒ GREEN 82.6%, GREEN ⇒ PINK 62.4% |
| Tiếp theo | hai mẫu GARDENERS KNEELING PAD (lift 15.6); PINK ⇒ ROSES REGENCY TEACUP (14.5) |
| Support cao nhất | JUMBO BAG RED RETROSPOT ⇔ JUMBO BAG PINK POLKADOT: support 4.2%, lift 6.4 |
| Lift thấp nhất | JUMBO BAG RED RETROSPOT ⇔ WHITE HANGING HEART T-LIGHT HOLDER: support 2.0%, confidence 18-19%, lift 1.7 |
| Hai nửa năm | 12/2010-06/2011: 172 luật; 07-12/2011: 340 luật; chung **106** |
| Chỉ có ở nửa sau | PAPER CHAIN KIT 50'S CHRISTMAS ⇔ PAPER CHAIN KIT VINTAGE CHRISTMAS: support 4.5%, lift 7.3 |

**Đọc luật**:

- Lift cao nhất là biến thể màu của cùng sản phẩm: khách sỉ mua đủ bộ. Hành động là bán theo set, không phải gợi ý
  (khách đã tự mua).
- Luật support cao nhất (hai mẫu Jumbo bag, 4.2% giỏ, lift 6.4) ảnh hưởng nhiều giỏ hơn luật lift cao nhất: ưu tiên
  theo doanh thu kỳ vọng (support × giá trị), lift chỉ cần đủ rõ.
- Confidence 18-19% giữa hai món bán chạy nhất gần như chỉ phản ánh độ phổ biến của chúng (11% mọi giỏ có món kia).
- Nửa sau có gần gấp đôi số luật nửa đầu và chỉ 106 luật chung: mùa Giáng sinh có giỏ lớn hơn và đồ trang trí đi cùng
  nhau. Dùng luật của đúng mùa cho catalogue của mùa đó.

**Đề xuất mẫu cho merchandiser**: "Làm set Jumbo bag 3 mẫu (Red retrospot, Pink polkadot, Vintage doily) cho
catalogue mùa thu: cặp đầu có trong 4.2% giỏ cả năm, cặp Red retrospot với Vintage doily 4.5% giỏ ở nửa sau. Đo bằng
A/B test trên trang sản phẩm: doanh thu mỗi người xem, guardrail giá trị đơn."

## Đáp án trắc nghiệm

- `top-item` (c) **WHITE HANGING HEART T-LIGHT HOLDER, 11.1%**.
- `top-lift` (a) **82.6%, lift 16.1**. (b) là chiều GREEN ⇒ PINK, (c) là support, (d) ghép sai lift.
- `asymmetric` (c): confidence chia cho tỉ lệ giỏ có vế trái (PINK 3.9% giỏ, GREEN 5.1%), nên hai chiều khác nhau;
  lift chia cho tích hai tỉ lệ nên đối xứng. (d) sai: một hoá đơn không có thứ tự mua.
- `popular-pair` (b): lift 1.7 là đi cùng nhau thường hơn ngẫu nhiên một chút. (a) nhầm "phổ biến" với "đi cùng";
  (c) thay thế là lift < 1; (d) không có ngưỡng 50%: confidence phải so với tỉ lệ nền.
- `min-support` (d) **20, 176 và 1 788**: hạ một nửa ngưỡng làm số luật tăng 10 lần, phần lớn là luật hiếm.
- `halves` (a) **172 và 340, chung 106**.
- `variant-action` (d): bán theo set. (a) gợi ý thứ khách đã tự mua; (b) không liên quan tới luật; (c) lift cao là
  thật, chỉ là không phải cơ hội gợi ý.
- `prove-uplift` (b): luật là tương quan; người mua A có thể đã định mua B. So trước-sau lẫn mùa vụ; số lần bấm không
  phải doanh thu; confidence không đo tác động.
