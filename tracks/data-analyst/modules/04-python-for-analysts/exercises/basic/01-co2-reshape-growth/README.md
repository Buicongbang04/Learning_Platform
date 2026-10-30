---
title: Việt Nam trong ASEAN về CO2 - reshape long ↔ wide và tăng trưởng theo nước
level: basic
services: []
files:
  - path: starter/co2_growth.ipynb
    note: 5 hàm TODO (bỏ dòng tổng, to_wide, to_long, growth_table, yoy) + đọc kết quả
  - path: tests/test_co2_growth.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py owid-co2
  - uv run jupyter lab tracks/data-analyst/modules/04-python-for-analysts/exercises/basic/01-co2-reshape-growth/starter/co2_growth.ipynb
  - uv run pytest tracks/data-analyst/modules/04-python-for-analysts/exercises/basic/01-co2-reshape-growth -q
---

## Mục tiêu

Trả lời câu hỏi "Việt Nam phát thải CO2 cỡ nào so với ASEAN, tăng nhanh hay chậm?" bằng ba thao tác pandas DA dùng
hằng ngày: bỏ dòng tổng khỏi bảng công khai, đổi hình dạng long ↔ wide, và tính tăng trưởng theo nước (10 năm, CAGR,
từng năm) mà không bị lỗ hổng dữ liệu đánh lừa.

## Đề bài

Bộ `owid-co2` (Our World in Data, CC BY 4.0, ghim commit `382ee6c`): `owid-co2-data.csv`, 50 411 dòng quốc gia-năm,
1750–2024, trộn dòng quốc gia với dòng tổng (`World`, châu lục, nhóm thu nhập) có `iso_code` rỗng. Ban phát triển
bền vững cần bảng 11 nước ASEAN cho báo cáo ESG. Mở `starter/co2_growth.ipynb`:

1. `countries_only(df)`: bỏ dòng tổng.
2. `to_wide(df, value, countries, years)` và `to_long(wide, value)`: long → wide (dùng `pivot`, khoá trùng phải báo
   lỗi) và ngược lại.
3. `growth_table(wide, start, end)`: giá trị hai năm, tăng trưởng và CAGR mỗi nước, sắp theo CAGR.
4. `yoy(long, value)`: tăng trưởng so với **năm** liền trước của cùng nước (không phải dòng trước).
5. Chạy các cell `explore` (bảng ASEAN 2014–2024, dot plot, tăng trưởng từng năm của Việt Nam, ví dụ Eritrea), viết
   ba câu cho ban phát triển bền vững theo phần 5 của notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau
   khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: bỏ dòng tổng giữ nguyên index, `to_wide` theo thứ tự `countries`/`years` và báo lỗi khi
  khoá trùng, vòng long → wide → long, `growth_table` bỏ nước thiếu năm hoặc bắt đầu từ 0, `yoy` trả `NaN` khi thiếu
  năm liền trước và giữ thứ tự dòng.
- Trên bộ thật: 218 quốc gia, cộng CO2 năm 2024 là 37 398 Mt (dòng `World` 38 599 Mt); ASEAN 2014 → 2024 có Lào,
  Campuchia, Việt Nam tăng nhanh nhất, Thái Lan là nước duy nhất giảm; Việt Nam +106.0%, CAGR 7.50%/năm; Việt Nam năm
  2019 +32.8%; Eritrea năm 1994 không có `yoy`.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`df.pivot(index="country", columns="year", values=value)` rồi `.reindex(countries)` và `.reindex(columns=years)`.
Ngược lại: `wide.reset_index().melt(id_vars="country", var_name="year", value_name=value)`, bỏ `NaN`, ép `year` sang
`int`, sắp lại.

### Gợi ý 2

Với `yoy`: tạo bảng "năm trước" bằng cách cộng 1 vào `year` (`long.assign(year=long.year + 1)`), đổi tên cột giá trị,
rồi `merge(..., on=["country", "year"], how="left")` vào bảng gốc. Năm không có năm liền trước thì không ghép được,
tự ra `NaN`. Left merge giữ thứ tự dòng bên trái; gán kết quả theo vị trí (`.to_numpy()`) để giữ index gốc.
