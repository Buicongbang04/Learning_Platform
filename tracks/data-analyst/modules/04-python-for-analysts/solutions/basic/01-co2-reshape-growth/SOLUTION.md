# Lời giải: Việt Nam trong ASEAN về CO2

## Cách làm

- **`countries_only`**: `df[df["iso_code"].notna()].copy()`. Dòng tổng của OWID (World, châu lục, nhóm thu nhập,
  "International aviation"...) đều có `iso_code` rỗng. Ngoại lệ cần ghi lại: `Kosovo` cũng không có `iso_code` trong
  bộ này nên bị loại; với báo cáo ASEAN không ảnh hưởng.
- **`to_wide`**: `pivot` rồi `reindex` theo danh sách nước và năm được truyền. Dùng `pivot` chứ không phải
  `pivot_table`: nếu bảng có khoá `(country, year)` trùng, `pivot` báo `ValueError`, còn `pivot_table(aggfunc="sum")`
  âm thầm cộng hai dòng và báo cáo sai mà không ai biết.
- **`to_long`**: `reset_index().melt(...)`, bỏ `NaN`, ép `year` sang `int` (sau `reindex(columns=years)` cột vẫn là
  số, nhưng khi đọc từ Excel cột năm thường là chuỗi), sắp lại và đặt lại index.
- **`growth_table`**: chọn hai cột năm, `dropna`, bỏ `start <= 0`, rồi tính `pct_change` và CAGR với số năm là
  `end - start`. Sắp theo CAGR giảm dần.
- **`yoy`**: ghép bảng với chính nó theo `(country, year + 1)`:

```python
prev = long[["country", "year", value]].assign(year=long["year"] + 1).rename(columns={value: "_prev"})
merged = long[["country", "year"]].merge(prev, on=["country", "year"], how="left", validate="many_to_one")
out = long.copy()
out["yoy"] = long[value].to_numpy() / merged["_prev"].to_numpy() - 1
```

  Năm không có năm liền trước không ghép được nên ra `NaN`. `groupby().pct_change()` sai vì nó so với dòng trước:
  Eritrea có dữ liệu 1944 rồi nhảy sang 1994, `pct_change` cho năm 1994 là +3 828% (0.707 so với 0.018 Mt), một con
  số vô nghĩa. Cách khác cũng đúng: `pivot` sang wide, `reindex(columns=range(min, max + 1))` cho đủ năm, chia cột cho
  cột liền trước, rồi `melt` lại.

## Con số chính (OWID, commit `382ee6c`)

| Đại lượng | Giá trị |
| --- | --- |
| Cộng mọi dòng `co2` năm 2024 | 245 672 Mt (6.4 lần World) |
| Dòng World / cộng 218 quốc gia | 38 599 Mt / 37 398 Mt (chênh chủ yếu: hàng không 569 Mt, hàng hải 623 Mt quốc tế) |
| ASEAN 2024 | 2 060.5 Mt; Indonesia 812.2, Việt Nam 370.9 (18.0%), Malaysia 290.2, Thái Lan 267.8 |
| Việt Nam 2014 → 2024 | 180.0 → 370.9 Mt, +106.0%, CAGR 7.50%/năm |
| CAGR cao nhất ASEAN | Lào 18.7% (4.4 → 24.4 Mt), Campuchia 12.6%, Việt Nam 7.5% |
| Giảm duy nhất | Thái Lan −1.7% (272.5 → 267.8 Mt) |
| Đầu người 2024 | Việt Nam 3.67 t, Thái Lan 3.74 t, thế giới 4.73 t, Brunei 26.05 t (cao nhất), Đông Timor 0.48 t |
| Việt Nam từng năm | 2019 +32.8% (255.5 → 339.3 Mt), 2015 +18.5%, 2018 +12.2%, 2021 −13.4% |

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `aggregate-sum` | c | 245 672 / 38 599 = 6.4: mỗi tấn được cộng ở nước, châu lục (hai bộ: OWID và GCP), nhóm thu nhập, World |
| `vn-rank` | b | Indonesia 812 Mt, Việt Nam 371 Mt = 18.0% của 2 060 Mt |
| `fastest-cagr` | a | Lào 18.7%/năm; Campuchia 12.6%; Việt Nam 7.5%; Indonesia 5.0% |
| `vn-per-capita` | b | 3.67 t so với thế giới 4.73 t; Thái Lan 3.74 t; Myanmar 0.58 t và Đông Timor 0.48 t thấp hơn nhiều |
| `vn-jump-year` | c | 2019 +32.8%, gần gấp đôi năm cao thứ hai trong kỳ (2015 +18.5%) |
| `eritrea-gap` | a | Dòng trước của 1994 là 1944; `yoy` đúng thì không có năm liền trước nên `NaN` |
| `pivot-vs-pivot-table` | d | Khoá `(country, year)` phải duy nhất; trùng là dữ liệu bẩn, phải thấy lỗi chứ không được cộng |
| `big-pct-small-base` | b | Lào thêm khoảng 20 Mt, Việt Nam thêm khoảng 191 Mt: báo cả tỉ lệ lẫn mức tuyệt đối |

## Ba câu cho ban phát triển bền vững (mẫu)

1. Năm 2024 Việt Nam phát thải 371 triệu tấn CO2, đứng thứ hai ASEAN sau Indonesia (812 triệu tấn) và chiếm 18% tổng
   ASEAN; tính theo đầu người (3.7 tấn) vẫn dưới trung bình thế giới (4.7 tấn) và ngang Thái Lan.
2. Trong 10 năm, CO2 Việt Nam tăng gấp đôi (+106%, 7.5%/năm), nhanh thứ ba ASEAN sau Lào và Campuchia; nhưng hai nước
   đó tăng trên nền rất nhỏ (Lào thêm 20 triệu tấn, Việt Nam thêm 191 triệu tấn), nên về mức tuyệt đối Việt Nam là
   nguồn tăng lớn nhất ngoài Indonesia.
3. Năm 2019 CO2 Việt Nam tăng vọt 32.8%; cần xem cột `coal_co2` (than) để kiểm giả thuyết các nhà máy nhiệt điện than
   mới vận hành, trước khi viết nguyên nhân vào báo cáo.

## Lỗi hay gặp

- Cộng cả cột không bỏ dòng tổng, hoặc lọc bằng `country != "World"` (vẫn còn châu lục và nhóm thu nhập).
- Dùng `pivot_table` "cho chắc" và che mất khoá trùng.
- Tính CAGR bằng `pct_change / 10`: Việt Nam ra 10.6%/năm thay vì 7.5%.
- `groupby().pct_change()` hoặc `shift()` không kiểm năm liền nhau.
- Chỉ báo tỉ lệ tăng trưởng: một nước nhỏ tăng 457% trông như rủi ro lớn nhất.
