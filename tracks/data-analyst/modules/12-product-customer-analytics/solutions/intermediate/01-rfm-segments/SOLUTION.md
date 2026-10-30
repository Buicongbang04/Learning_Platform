# Lời giải: RFM segmentation bằng luật nghiệp vụ

## Cách làm

1. **`rfm_table`**: `groupby("Customer ID")` trên dòng có mã khách. Recency dùng `dt.normalize()` trước khi trừ, để
   khách mua 15:00 ngày 09/12 có recency 1 chứ không phải 0.4 ngày. Frequency là `Invoice.nunique()`: một hoá đơn
   20 dòng hàng vẫn là một lần mua.
2. **`score_rfm`**: `np.searchsorted(edges, x, side="left")` đếm số mốc mà `x` vượt (với `side="left"`, `x` bằng
   mốc thì chưa vượt). R = 5 trừ số đó, F = 1 cộng số đó. M: `rank(method="first")` rồi `qcut` 5 nhóm, nên đúng 20%
   mỗi mức kể cả khi nhiều khách cùng giá trị. Làm trên `rfm.copy()`.
3. **`assign_segment`**: duyệt luật theo thứ tự, luật đầu tiên có R và F khớp thắng. Thứ tự là một phần của định
   nghĩa: champions đứng trước loyal và potential_loyalist.
4. **`segment_summary`**: `groupby("segment").agg(...)` rồi chia tổng; sắp theo doanh thu để người đọc thấy ngay
   segment quan trọng.

## Số liệu trên bộ thật

4 338 khách, doanh thu 8 911 426 GBP, ngày chốt 10/12/2011. Trung vị recency 51 ngày, trung vị 2 đơn, trung vị
monetary 674 GBP (mean 2 054 GBP: lệch phải mạnh). Mốc quintile M: 250, 490, 942, 2 058 GBP.

| Segment | Khách | % khách | % doanh thu | Trung vị R (ngày) | Trung vị F |
| --- | --- | --- | --- | --- | --- |
| champions | 507 | 11.7% | **46.8%** | 5 | 9 |
| loyal | 536 | 12.4% | 22.7% | 30 | 7 |
| potential_loyalist | 634 | 14.6% | 9.2% | 16 | 3 |
| hibernating | **1 164** | 26.8% | 6.4% | 226.5 | 1 |
| at_risk | 278 | 6.4% | 4.9% | 139 | 3 |
| need_attention | 305 | 7.0% | 4.6% | 54 | 3 |
| about_to_sleep | 700 | 16.1% | 4.4% | 58 | 1 |
| promising | 140 | 3.2% | 0.5% | 23 | 1 |
| cant_lose | 7 | 0.2% | 0.3% | 157 | 12 |
| new | 67 | 1.5% | 0.3% | 8 | 1 |

Phân bố điểm: R 1-5 = 861, 588, 1 261, 760, 868; F 1-5 = **1 493**, 835, 896, 723, 391. Champions và loyal cộng lại
24.1% khách, 69.5% doanh thu. 10 khách lớn nhất chiếm 17.3% doanh thu năm (khách lớn nhất 280 206 GBP).

**Đề xuất ba chiến dịch cho CRM** (một cách trả lời tốt):

1. **Giữ champions và loyal** (1 043 khách, 69.5% doanh thu): quản lý tài khoản, early access, gợi ý mua kèm (bài
   Intermediate 02). Không giảm giá đại trà. Đo bằng retention 90 ngày và doanh thu giữ được.
2. **Gọi điện 142 khách at_risk có M từ 4** (và 7 khách cant_lose): hỏi lý do, ưu đãi có thời hạn cho từng tài
   khoản. Đo bằng win-back rate 60 ngày so với nhóm đối chứng giữ lại ngẫu nhiên.
3. **Đơn thứ hai cho new/promising/potential_loyalist**: email theo nhịp mua. Đo tỉ lệ có đơn tiếp theo trong 30 ngày.

Hibernating đông nhất nhưng chỉ 6.4% doanh thu: chỉ chiến dịch chi phí thấp, hoặc bỏ qua.

**Ghi chú định nghĩa**: "new" chỉ có nghĩa "một đơn trong năm, mua trong 14 ngày"; 21/67 khách đã mua trước 12/2010.
M bị khách sỉ kéo; tách khách sỉ trước khi chấm quintile nếu CRM chăm sóc hai nhóm khác nhau.

## Đáp án trắc nghiệm

- `champions-share` (b) **11.7% khách, 46.8% doanh thu**. (a) là champions + loyal, (c) là loyal, (d) là hibernating.
- `largest-segment` (d) **hibernating, 1 164 khách**.
- `one-order` (a) **1 493 khách (34%)**: lý do không chấm F bằng quintile. (b) là cỡ một quintile M.
- `at-risk-value` (c) **142 khách**: gần một nửa at_risk có giá trị cao, đáng liên hệ trực tiếp.
- `top10` (b) **khoảng 17.3%**.
- `new-caveat` (c): đặt tên theo đúng điều dữ liệu biết. (a) bỏ khách thật; (b) giữ một cái tên sai cho CRM; (d) hai
  nhóm có hành vi khác hẳn (1 đơn so với từ 5 đơn).
- `champions-action` (d): giữ quan hệ. (a) cho tiền những người sẽ mua dù sao; (b) bỏ mặc nhóm mang lại gần một nửa
  doanh thu; (c) là hành động cho at_risk.
- `quintile-drift` (a): mốc quintile M phụ thuộc mọi khách khác. R và F dùng mốc cố định, chỉ đổi khi số của chính
  khách đó đổi (R tăng theo thời gian là hành vi thật: khách chưa quay lại). Đây là lý do module dùng ngưỡng cho R, F.
