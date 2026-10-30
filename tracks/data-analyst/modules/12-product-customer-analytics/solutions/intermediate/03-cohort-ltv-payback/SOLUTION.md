# Lời giải: LTV theo cohort và CAC payback

## Cách làm

1. **`simple_ltv`**: kiểm `0 <= retention < 1` (retention 1 cho LTV vô hạn), rồi `aov * f * m / (1 - r)`.
2. **`cohort_ltv`**: tháng, cohort (tháng mua đầu trên toàn bộ dữ liệu), `k`; doanh thu theo `(cohort, k)`,
   `reindex` đủ cột để tháng không ai mua vẫn có cột (luỹ kế giữ nguyên), `cumsum(axis=1)`, chia số khách của cohort,
   rồi `mask` ô có `k` lớn hơn tuổi cohort. Che **sau** khi luỹ kế; nếu che trước, `cumsum` bỏ qua `NaN` và ô chưa quan
   sát được sẽ hiện lại giá trị cũ.
3. **`payback_month`**: ngưỡng doanh thu luỹ kế cần đạt là `cac / margin`; với mỗi hàng lấy `k` đầu tiên đạt, không
   có thì `pd.NA`; Series `Int64` để giữ số nguyên lẫn giá trị thiếu.
4. **`max_cac_table`**: hoàn vốn trong `h` tháng là đọc cột `k = h - 1`. Trung bình có trọng số cỡ cohort = tổng doanh
   thu luỹ kế của các cohort đó chia tổng số khách, tức "một khách mới bất kỳ". Nhân biên để ra CAC tối đa.

## Số liệu trên bộ thật

| Chỉ số | Giá trị |
| --- | --- |
| Khách 12/2010-11/2011 | AOV 473 GBP; 4.13 đơn/khách/năm; retention năm 63.6% (khách 12/2009-11/2010 còn mua) |
| LTV đơn giản, biên 35% (giả định) | **1 878 GBP** lợi nhuận gộp (5 365 GBP doanh thu) |
| Khách mới 01-11/2010, 12 tháng đầu | 3 311 khách; mean **1 449 GBP**, median **708 GBP** doanh thu; 1% khách lớn nhất chiếm 15.8% |
| LTV cohort 01/2010 | 423 GBP (k = 0), 658 (k = 2), 1 122 (k = 5), **2 043** (k = 11) |
| LTV 12 tháng, cohort 2010 | cao nhất 01/2010 (2 043), thấp nhất 12/2010 (824); 05/2010: 1 054 |
| Payback, CAC 200, biên 35% | k = 0-3 cho các cohort 01-11/2010 (09/2010: 0); 12/2010: **4** |
| Payback, CAC 400, biên 35% | 5-13 tháng; 05/2010: 13; **11/2010 và 12/2010 chưa hoàn vốn** tới 11/2011 |
| CAC tối đa (cohort 01/2010 trở đi) | biên 25 / 35 / 45%: 3 tháng 168 / **235** / 302; 6 tháng 237 / **332** / 427; 12 tháng 359 / **502** / 646 GBP |

**Vì sao LTV đơn giản lạc quan** (1 878 GBP lợi nhuận gộp, tức 5 365 GBP doanh thu, so với 1 449 GBP doanh thu năm
đầu của khách mới):

- Retention năm 63.6% đo trên tập khách chứa nhiều khách lâu năm đã "sống sót"; khách mới chỉ khoảng 20-23% quay lại
  tháng sau (bài Basic 02).
- Công thức coi retention không đổi theo tuổi, nhân lên vô hạn năm.
- Trung bình bị khách sỉ kéo: median chỉ bằng một nửa mean.

**Câu trả lời mẫu cho CMO**: "Một khách mới mang lại trung bình khoảng 1 450 GBP doanh thu trong năm đầu (khách điển
hình khoảng 700). Với biên lợi nhuận gộp **giả định** 35%, muốn hoàn vốn trong 6 tháng thì CAC tối đa khoảng 330 GBP,
trong 12 tháng khoảng 500 GBP. Cần số biên và chi phí thật từ tài chính để chốt; cohort cuối 2010 giá trị thấp hơn hẳn
nên ngưỡng nên tính lại theo mùa."

## Các quyết định cần cân nhắc

- **Bỏ cohort 12/2009** khỏi bảng CAC: cắt trái, chứa khách lâu năm (LTV k = 23 là 8 768 GBP).
- **Doanh thu gộp** (không trừ hoá đơn huỷ về sau) làm LTV cao hơn thực tế một chút; nói rõ định nghĩa.
- **Mùa vụ**: cohort tháng 9-10 vào ngay mùa cao điểm nên hoàn vốn nhanh; cohort tháng 11-12 thì chậm. Một ngưỡng CAC
  cho cả năm là trung bình của các mùa khác nhau.

## Đáp án trắc nghiệm

- `simple-ltv-real` (c) **khoảng 1 878 GBP**. (d) là con số trước khi nhân biên; (b) là doanh thu năm đầu của khách mới.
- `new-first-year` (a) **mean 1 449, median 708**. Trung bình bị khách sỉ kéo lên.
- `why-optimistic` (b). (a) AOV không phải nguồn chính của chênh lệch; (c) biên là giả định chung cho cả hai cách;
  (d) không liên quan.
- `slowest-payback` (d) **cohort 12/2010, tháng thứ 4**: vào sau mùa cao điểm, tháng 1-2 mua rất ít.
- `never-payback` (a) **11/2010 và 12/2010**: LTV 12 tháng 940 và 824 GBP, thấp hơn ngưỡng 400 / 0.35 = 1 143 GBP.
- `max-cac-6m` (b) **khoảng 332 GBP**. (a) là 3 tháng, (c) là 12 tháng.
- `ltv-cac-rule` (c): ngưỡng 3 là quy ước SaaS, không phải định luật; LTV là ước tính tương lai; công ty ít tiền mặt
  cần payback ngắn.
- `blended-cac` (d): quyết định chi thêm cho một kênh cần chi phí của khách **thêm** từ kênh đó (thường cao hơn
  trung bình) và giá trị của đúng những khách đó. CAC gộp trộn cả khách tự nhiên có CAC gần 0.
