# Lời giải: decoupling thật hay "xuất khẩu" phát thải?

## Cách làm

- **`period_change`**: lọc dòng quốc gia, lấy hai ảnh chụp theo năm rồi ghép:

```python
a = nations.loc[nations["year"] == start, ["country", *cols]]
b = nations.loc[nations["year"] == end, ["country", *cols, "population"]]
both = a.merge(b, on="country", suffixes=("_start", "_end"), validate="one_to_one")
both = both.dropna(subset=[f"{c}_{s}" for c in cols for s in ("start", "end")])
both = both[both["population"] >= min_population]
```

  `validate="one_to_one"` biến một lỗi dữ liệu (một nước hai dòng cùng năm) thành `MergeError` thay vì nhân dòng. Cách
  khác cũng đúng: `pivot` hai năm cho từng cột (cũng báo lỗi khi khoá trùng). `dropna` chỉ trên các cột cần, không trên
  cả bảng (79 cột OWID gần như dòng nào cũng có ô rỗng).
- **`classify`**: `np.select` lấy điều kiện đúng **đầu tiên**, nên đặt `gdp <= 0` trước: một nước GDP giảm mà CO2 cũng
  giảm (Ukraine, Hy Lạp) không phải "tách rời", chỉ là kinh tế co lại. `em < gdp` dùng dấu `<` chặt: tăng bằng nhau là
  `coupled`.
- **`decoupling_table`**: gọi `classify` hai lần trên hai cột phát thải, cờ `offshoring` là phép AND hai điều kiện.

## Con số chính (2005 → 2022, từ 10 triệu dân, 75 nước)

| Nhãn theo CO2 sản xuất | Số nước | Ví dụ |
| --- | --- | --- |
| absolute | 17 | Anh −45.5% CO2 / +21.0% GDP; Đức −23.0% / +32.7%; Mỹ −17.5% / +32.8%; Ba Lan −2.4% / +106.6% |
| relative | 39 | Trung Quốc +99.1% / +213.5%; Ấn Độ +136.8% / +179.2% |
| coupled | 16 | Việt Nam +236.7% / +169.8%; Campuchia, Nepal, nhiều nước châu Phi |
| gdp_decline | 3 | Hy Lạp, Ukraine, Venezuela |

Bảng chéo sản xuất × tiêu dùng: 14 nước `absolute` cả hai cách đo; 3 nước rơi xuống `relative` khi tính theo tiêu dùng
(Australia −0.3% sản xuất / +3.8% tiêu dùng, Mexico −2.1% / +8.7%, Ba Lan −2.4% / +1.4%); Đài Loan đi ngược lại
(`relative` theo sản xuất, `absolute` theo tiêu dùng). Czechia giảm 24.4% CO2 sản xuất nhưng CO2 tiêu dùng gần như
không đổi (−0.04%): vẫn được tính `absolute`, nhưng nằm sát ngưỡng.

Độ nhạy:

| Lựa chọn | Số nước | absolute (sản xuất) | absolute cả tiêu dùng |
| --- | --- | --- | --- |
| 2005 → 2022, từ 10 triệu dân | 75 | 17 | 14 |
| 2008 → 2022, từ 10 triệu dân | 75 | 19 | 17 |
| 2010 → 2022, từ 10 triệu dân | 75 | 19 | 16 |
| 2005 → 2022, từ 1 triệu dân | 117 | 37 | 26 |

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `absolute-count` | b | 17; 39 là `relative`, 3 là `gdp_decline` |
| `offshoring-countries` | c | Australia, Mexico, Ba Lan; Anh, Pháp, Đức, Mỹ, Nhật, Canada giảm cả CO2 tiêu dùng |
| `vietnam-class` | d | +237% > +170%: CO2 tăng nhanh hơn GDP |
| `uk-change` | a | Anh giảm sâu nhất trong nhóm absolute; Ukraine giảm sâu hơn nhưng GDP cũng giảm nên là `gdp_decline` |
| `sensitivity` | b | 117 nước, 37 absolute: nhiều nước nhỏ châu Âu (Đan Mạch, Phần Lan, Thuỵ Sĩ...) vào mẫu |
| `consumption-meaning` | b | Phát thải "theo người tiêu dùng cuối": cộng hàng nhập, trừ hàng xuất. (d) là `co2_including_luc` |
| `why-validate` | a | Kiểm khoá; không làm nhanh hơn và không lọc nước |
| `what-not-to-claim` | c | Dữ liệu mô tả **cái gì** đã xảy ra, không chứng minh **vì sao** (chính sách, chuyển dịch ngành, khủng hoảng 2008, giá năng lượng đều có thể góp phần) |

## Đoạn gửi quỹ đầu tư (mẫu)

Từ 2005 tới 2022, trong 75 nước từ 10 triệu dân có đủ dữ liệu, 17 nước tăng GDP mà giảm CO2 trên lãnh thổ (dẫn đầu là
Anh: CO2 −45%, GDP +21%), và 14 nước trong số đó vẫn giảm khi tính cả phát thải của hàng nhập khẩu; ba nước còn lại
(Australia, Mexico, Ba Lan) giảm rất ít trên lãnh thổ nhưng CO2 tiêu dùng vẫn tăng. Trung Quốc và Ấn Độ tách rời tương
đối (CO2 tăng chậm hơn GDP), còn Việt Nam thuộc nhóm CO2 tăng nhanh hơn GDP (+237% so với +170%). Con số nhạy với lựa
chọn: bắt đầu từ 2008 thì có 19 nước, hạ ngưỡng xuống 1 triệu dân thì có 37 nước. Phân tích chỉ mô tả, không cho biết
chính sách nào gây ra mức giảm, và năm cuối 2022 còn chịu ảnh hưởng hậu COVID.

## Lỗi hay gặp

- Quên bỏ dòng tổng: `World`, `European Union (27)`, `High-income countries` thành "nước" trong bảng.
- `dropna()` trên cả bảng: mất gần hết các nước vì 79 cột.
- Lọc dân số theo năm đầu thay vì năm cuối (khác đề, và khác kết quả với nước dân số giảm).
- Phân loại `absolute` trước khi kiểm GDP: Ukraine, Hy Lạp thành "tách rời thành công".
- Kết luận nhân quả hoặc chỉ báo một con số (17) mà không nói nó đổi theo năm đầu và ngưỡng.
