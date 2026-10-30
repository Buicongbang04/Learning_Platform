# Lời giải: cohort retention heatmap trên Online Retail II

## Cách làm

1. **`cohort_activity`**: bỏ khách null, tạo bảng `customer_id`, `month` (`to_period("M")`), `drop_duplicates()` để
   mỗi khách × tháng một dòng (khách mua 10 hoá đơn trong tháng vẫn là một). Cohort là `min(month)` theo khách, tính
   trên toàn bộ dữ liệu rồi mới lọc `month <= last`: khách mua lần đầu ở 12/2011 có cohort 12/2011 nên không còn dòng
   nào, thay vì bị coi là "chưa từng mua". `k = (month - cohort).n`.
2. **`retention_matrix`**: đếm theo `(cohort, k)`, `unstack(fill_value=0)`, `reindex` cột đủ `0..tuổi lớn nhất`,
   chia cỡ cohort (`k = 0`). Tuổi mỗi ô = `(last - cohort).n - k`; ô tuổi âm là chưa quan sát được, `mask` thành
   `NaN`. Phân biệt `NaN` (chưa tới) với `0` (tới rồi mà không ai mua) là bẫy số 3 của module 03.
3. **`calendar_view`**: `drop(columns=0).stack().dropna()` (pandas 3 giữ `NaN` khi `stack`), cột `month = cohort + k`,
   `pivot`. Đường chéo của heatmap thành cột dọc.
4. **`retention_curve`**: tử số `matrix.fillna(0).mul(sizes, axis=0).sum()` là số khách quay lại ở `k` của các cohort
   đã quan sát; mẫu số `matrix.notna().mul(sizes, axis=0).sum()` là tổng cỡ của chính các cohort đó. Dùng
   `fillna(0)` ở tử số an toàn vì mẫu số chỉ đếm ô quan sát được.

## Số liệu trên bộ thật

| Chỉ số | Giá trị |
| --- | --- |
| Cohort, khách | 24 cohort (12/2009-11/2011), 5 850 khách; nhỏ nhất 01/2011 (71), lớn nhất 12/2009 (955) |
| Ô quan sát được | 300 (cohort tuổi `a` có `a + 1` ô) |
| Hàng 01/2010 | m1 20.6%, sau đó 15-32% tới k = 22 |
| m1 thấp nhất | cohort **12/2010: 9.2%** (76 khách); m1 của nó là tháng 1/2011 |
| Calendar view (trung bình có trọng số theo tháng lịch) | 09-11/2010: 27.2%, 31.4%, 32.5%; 12/2010-02/2011: **19.0%, 15.4%, 14.4%**; 11/2011: 26.0% |
| Đường có trọng số | k = 1: 23.4%; k = 3: 24.9%; k = 6: 22.1%; k = 12: 22.7%; k = 21: 25.5% (3 cohort) |
| Trung bình đơn giản | k = 1: 21.5%; k = 12: 19.5% |
| Điểm cuối | k = 22 (2 cohort): 28.8%; k = 23 (1 cohort, 12/2009): 40.7% |
| Bỏ cohort 12/2009 | k = 1: 21.0%; k = 12: 18.4% |

So cohort cùng tháng hai năm (m1, cỡ cohort):

| Tháng | 2010 | 2011 |
| --- | --- | --- |
| 01 | 20.6% (383) | 16.9% (71) |
| 02 | 23.8% (374) | 16.1% (124) |
| 03 | 19.0% (443) | 18.4% (179) |
| 04 | 19.4% (294) | 25.5% (106) |
| 05 | 15.7% (254) | 23.4% (111) |
| 06 | 17.4% (270) | 23.1% (108) |
| 07 | 15.6% (186) | 21.6% (102) |
| 08 | 20.4% (162) | 27.4% (106) |
| 09 | 22.6% (243) | 27.0% (189) |
| 10 | 25.7% (377) | 32.1% (221) |

**Đọc**:

- Theo hàng: cohort 01/2010 rơi còn 20.6% ở tháng 1 rồi đi ngang trong dải 15-32%. Có nhóm khách lõi ở lại.
- Theo cột: cohort 12/2010 thấp nhất không phải vì khách tháng 12 tệ, mà vì tháng 1 của nó là tháng 1/2011, đáy mùa
  vụ. Calendar view cho thấy mọi cohort cùng tối ở 12-2 và cùng sáng ở 9-11: đặt hàng Giáng sinh của khách sỉ.
- Đường trung bình: đi lên ở k = 22-23 vì chỉ còn 1-2 cohort, và cohort 12/2009 bị cắt trái (chứa khách lâu năm mua
  lại trong tháng đầu của dữ liệu). Cắt ở 3 cohort và báo cả bản bỏ cohort 12/2009.
- Câu trả lời cho Head of CRM: "Từ tháng 4/2011, khách mới quay lại tháng sau tốt hơn cùng tháng năm trước 4-8 điểm
  (ví dụ 04: 25.5% so với 19.4%), nhưng số khách mới ít hơn 1.3-2.8 lần; cohort tháng 1-3/2011 thì kém năm trước. Cần
  xem vì sao số khách mới giảm."

## Đáp án trắc nghiệm

- `lowest-m1` (a) **cohort 12/2010, 9.2%**.
- `why-lowest` (a): tháng 1 của cohort rơi vào tháng 1/2011, ngay sau cao điểm đặt hàng Giáng sinh. (b) cohort nhỏ
  nhất là 01/2011 (71 khách), không phải 12/2010; (d) ô này đã quan sát được.
- `dark-months` (d) **12/2010-02/2011**: trung bình theo tháng lịch 19.0%, 15.4%, 14.4% so với 32.5% ở 11/2010.
- `weighted-k1` (c) **23.4%**. (a) là m1 của cohort 01/2010, (b) là trung bình đơn giản, (d) là m1 của 12/2009.
- `last-point` (b) **k = 21** (3 cohort). k = 22 còn 2, k = 23 còn 1.
- `dec09-high` (c): cắt trái. Dữ liệu bắt đầu 01/12/2009, nên mọi khách mua trong tháng đó (kể cả khách đã mua từ
  nhiều năm) đều bị gán cohort 12/2009. (b) không có "luật" nào như vậy; (d) tháng 1 là đáy mùa vụ.
- `yoy-cohorts` (b): 2011 cao hơn ở 7 cặp tháng 4-10, thấp hơn ở tháng 1-3, và mọi cohort 2011 nhỏ hơn. Chọn hai
  tháng thuận lợi rồi kết luận "2011 tốt hơn" là cherry-picking.
- `blank-cell` (d): cohort 09/2011 tới tháng 11/2011 mới có tuổi 2; ô k = 3 chưa tới. Ô trống khác ô 0.
