# Lời giải: trung bình của trung bình trên Rossmann

## Cách làm

1. **`open_days`**: mặt nạ `(Open == 1) & (Sales > 0)`, `.copy()`. 54 dòng ghi mở cửa nhưng doanh số 0 bị bỏ: một
   "ngày bán" không có doanh số là lỗi ghi nhận hoặc ngày không hoạt động, giữ lại sẽ kéo mean xuống.
2. **`full_coverage_stores`**: `pd.to_datetime(Date)`, lọc trong cửa sổ, `groupby(Store).nunique()` trên ngày, giữ
   cửa hàng có số ngày bằng `len(pd.date_range(start, end))`. Đếm ngày khác nhau, không đếm dòng.
3. **`mean_two_ways`**: `row_mean = groupby(by)[value].mean()`; `unit_mean` là `groupby([by, unit]).mean()` rồi
   `groupby(level=0).mean()`.
4. **`ratio_two_ways`**: bỏ dòng `den <= 0`, `pooled = sum(num) / sum(den)`,
   `mean_of_ratios = (num / den).groupby(by).mean()`.

## Câu trả lời cho CEO

| Cách so nửa cuối 2014 với nửa cuối 2013 | Cửa hàng (2013 → 2014) | Kết quả |
| --- | --- | --- |
| Tổng, mọi cửa hàng có dữ liệu (dashboard Finance) | 1 115 → 935 | 1 200.5 → 1 041.8 triệu EUR, **−13.2%** |
| TB mỗi cửa hàng-ngày, mọi cửa hàng (Ops) | 1 115 → 935 | 6 961 → 7 198 EUR, **+3.4%** |
| Tổng, 935 cửa hàng đủ dữ liệu | 935 → 935 | 1 016.3 → 1 041.8 triệu EUR, **+2.5%** |
| TB mỗi cửa hàng-ngày, 935 cửa hàng | 935 → 935 | 7 012 → 7 198 EUR, **+2.7%** |

- **Finance sai** vì so hai tập cửa hàng khác nhau: 180 cửa hàng (84 loại a, 81 loại d, 14 loại c, 1 loại b) không
  có dòng nào từ 01/07/2014 tới 31/12/2014. Dữ liệu thiếu, không phải cửa hàng bán kém.
- **Ops đúng hướng nhưng phóng đại**: 180 cửa hàng vắng mặt vốn bán thấp hơn (6 690 so với 7 012 EUR/ngày ở nửa cuối
  2013), nên khi chúng biến mất, mean tự tăng (mix effect).
- **Con số cho hội đồng quản trị**: like-for-like (cùng 935 cửa hàng) **+2.5%** tổng, +2.7% mỗi cửa hàng-ngày, kèm
  ghi chú 180 cửa hàng thiếu dữ liệu nửa cuối 2014 và đề nghị team dữ liệu tìm nguyên nhân (đóng cửa sửa chữa, đổi
  hệ thống, lỗi pipeline).

Headline mẫu: **"Doanh số like-for-like nửa cuối 2014 tăng 2.5%; con số −13% là do 180 cửa hàng thiếu dữ liệu"**.

## Loại cửa hàng và doanh số mỗi khách

| Loại | Cửa hàng | Ngày bán/cửa hàng | `row_mean` | `unit_mean` | Khách TB/ngày | EUR/khách (`pooled`) | `mean_of_ratios` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| a | 602 | 759 | 6 926 | 6 913 | 795 | 8.71 | 8.85 |
| b | 17 | 915 | 10 233 | 10 112 | 2 022 | 5.06 | 5.13 |
| c | 148 | 763 | 6 933 | 6 918 | 816 | 8.50 | 8.63 |
| d | 348 | 744 | 6 822 | 6 824 | 606 | 11.25 | 11.28 |

- **Loại b bán nhiều vì đông khách**, không vì khách chi nhiều: 2 022 khách/ngày (gấp 2.5 lần loại a) nhưng mỗi khách
  chỉ 5.06 EUR. Đây là hồ sơ cửa hàng ở nơi đông người qua lại; 14.2% ngày bán của loại b là Chủ nhật (loại khác gần
  như không mở Chủ nhật). Với 17 cửa hàng, mọi kết luận về loại b nên kèm n.
- **`row_mean` và `unit_mean` lệch nhiều nhất ở loại b** (121 EUR) vì các cửa hàng loại b có số ngày bán chênh lệch
  lớn: cửa hàng mở Chủ nhật có nhiều ngày hơn và nặng hơn trong `row_mean`. Ở loại a, c, d hai con số gần nhau vì số
  ngày mỗi cửa hàng gần như đều.
- **Loại d ngược lại**: ít khách nhất (606/ngày) nhưng mỗi khách chi nhiều nhất (11.25 EUR). "Doanh số mỗi cửa hàng"
  gần bằng nhau giữa a, c, d che hai mô hình kinh doanh khác hẳn.
- **Cả chuỗi**: 9.12 EUR/khách (tổng/tổng) so với 9.49 (mean các tỉ số); câu hỏi "mỗi khách mang lại bao nhiêu" dùng
  9.12.

## Sửa dashboard

Hiện **số đơn vị có dữ liệu** cạnh mọi tổng (một dòng nhỏ dưới chart là đủ), thêm đường **like-for-like** (cửa hàng có
dữ liệu đủ cả hai kỳ so sánh), và cảnh báo tự động khi số cửa hàng báo cáo giảm quá ngưỡng (ví dụ 2%). Không đổi tổng
thành mean (vẫn bị mix effect), không xoá cửa hàng có lỗ hổng (mất 16% chuỗi khỏi mọi báo cáo), và không điền số thiếu
mà không đánh dấu (biến dữ liệu bịa thành con số chính thức).

## Đáp án trắc nghiệm

- `stores-reporting` (c) 935. (d) 180 là số cửa hàng **thiếu**.
- `balanced-total` (a) +2.5%. (b) là con số của dashboard; (c) là mean mỗi cửa hàng-ngày trên mọi cửa hàng.
- `why-mean-higher` (b): 6 690 so với 7 012 EUR/ngày. (c) sai: cả hai cách đều chỉ dùng ngày bán.
- `ceo-answer` (c).
- `unit-vs-row` (d) loại b: 10 233 so với 10 112.
- `type-b` (a): đông khách, giỏ nhỏ. (b) đảo ngược số của loại d; (d) n nhỏ là lưu ý, không phải lời giải thích.
- `per-customer-chain` (b) 9.12. (a) là mean các tỉ số; (c) là của riêng loại a; (d) không phải EUR/khách.
- `dashboard-fix` (d).
