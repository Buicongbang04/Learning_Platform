# Hướng làm: độ tập trung doanh thu và ngưỡng VIP

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết bốn hàm, các con số tham chiếu trên bộ thật, các quyết
định cần cân nhắc và rubric chấm memo.

## Bốn hàm

- **`customer_revenue`**: `Invoice.astype(str)`, mặt nạ dòng hợp lệ (không `C`, `Quantity > 0`, `Price > 0`, có
  `Customer ID`), `(Quantity * Price).groupby(Customer ID).sum()`, `sort_values(ascending=False)`, đặt tên Series và
  index.
- **Hàm phụ kiểm giá trị**: `np.asarray(dtype=float)`, `ValueError` khi rỗng, NaN, âm, tổng 0. Ba hàm còn lại dùng chung.
- **`lorenz_curve`**: sắp tăng, `customer_share = arange(n + 1) / n`, `revenue_share = [0] + cumsum / tổng`.
- **`gini`**: công thức hạng; tương đương `1 - 2 × diện tích dưới Lorenz` (quy tắc hình thang).
- **`top_share`**: sắp giảm, `k = ceil(q * n - 1e-9)`, tổng k giá trị đầu / tổng.

## Con số tham chiếu (sheet `Year 2010-2011`)

| Đại lượng | Giá trị |
| --- | --- |
| Doanh thu hợp lệ (mọi dòng) / của khách có mã | 10 666 703 / 8 911 426 GBP; khách vãng lai **16.5%** |
| Khách có mã | 4 338; doanh thu median 674, mean 2 054 GBP |
| Top 1% (44 khách) / 10% (434) / 20% (868) | 32.0% / 61.4% / **74.6%** |
| Khách cần cho 80% doanh thu | 1 133 (26.1%) |
| 50% khách nhỏ nhất | 7.8% doanh thu |
| Gini | **0.715** |
| Ba khách lớn nhất | 14646 (Hà Lan, 280 206 GBP, 73 hoá đơn), 18102 (Anh, 259 657), 17450 (Anh, 194 551); cộng 8.2% |
| Ngưỡng 5 000 / p90 3 647 / 3 000 / 2 500 / 2 000 GBP | 275 / 434 / 556 / 704 / 903 khách; 53.9% / 61.4% / 65.9% / 70.5% / 75.4% |
| Nhóm p90 (434 khách) | median 12 hoá đơn, 1.6% mua một lần, 3.9% mua lần đầu từ 07/2011, 354 ở Anh |
| Khách mua lần đầu từ 07/2011 | 1 378 (31.8% số khách), 11.0% doanh thu |
| Cohort mua lần đầu tháng 12/2010 (885 khách) | Gini 0.733, top 20% mang 76.0% |

**Câu chuyện mẫu**: doanh thu tập trung mạnh nhưng không đúng "20/80" (20% → 75%); ngưỡng p90 (khoảng 3 600 GBP/năm)
cho 434 khách vừa ngân sách và mang 61% doanh thu của khách có mã. Nhóm này mua đều, gần như không có khách một lần.

## Các quyết định cần cân nhắc

- **Exposure (thời gian quan sát)**: khách mua lần đầu cuối năm có ít tháng để chi, nên độ tập trung trên một năm lịch
  bị phóng đại một phần và khách mới tốt bị bỏ sót. Kiểm lại trên cohort có đủ 12 tháng (Gini 0.733, tập trung **không**
  giảm: kết luận vững). Đề xuất xét VIP theo doanh thu 12 tháng trượt.
- **Mẫu số**: 16.5% doanh thu đến từ khách vãng lai; "61% doanh thu" là của khách có mã. Ghi rõ, hoặc báo cả tỉ trọng
  trên toàn bộ doanh thu (51%).
- **Doanh thu gộp hay ròng**: theo định nghĩa dùng chung là gộp; khách trả hàng nhiều được xếp cao hơn thực tế. Một
  phiên bản trừ hàng trả (cộng dòng `C...` theo khách) nên dùng trước khi chốt danh sách.
- **Phụ thuộc khách lớn**: khách lớn nhất 3.1%, ba khách đầu 8.2%; đó là rủi ro tập trung cần nêu (mất một khách là mất
  vài phần trăm doanh thu), không chỉ là cơ hội.
- **Ngưỡng là quyết định kinh doanh**: phân vị là cách đề xuất, nhưng ngưỡng cuối nên là một con số tròn dễ truyền đạt
  và ổn định giữa các năm (p90 năm sau sẽ khác).
- **Không suy luận nhân quả**: chương trình VIP có làm khách chi nhiều hơn không phải đo bằng thử nghiệm (giữ một nhóm
  đối chứng ngẫu nhiên trong số khách đạt ngưỡng).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Trả lời câu "20/80" | 15 | Top 20% share có số, số khách cần cho 80%, nói rõ đúng/sai thế nào |
| Đo độ tập trung | 15 | Ít nhất ba mức top share và Gini; có một câu diễn giải cho người không biết thống kê |
| So ngưỡng VIP | 20 | So ít nhất hai ngưỡng theo số khách và doanh thu; chọn ngưỡng khớp ngân sách và giải thích |
| Kiểm chất lượng nhóm VIP | 15 | Kiểm hành vi nhóm (số hoá đơn, mua một lần, quốc gia) để chắc đây là khách quay lại thật |
| Rủi ro và giới hạn | 20 | Nêu ít nhất ba: exposure khách mới, khách vãng lai ngoài mẫu số, gộp/ròng, phụ thuộc vài khách lớn |
| Memo | 15 | Headline trả lời thẳng có con số; người đọc không cần biết tên cột; việc cần làm có người làm và thời điểm xem lại |

Từ 70 điểm trở lên là memo có thể gửi Head of CRM.

## Sai lầm hay gặp

- Báo "20% khách mang 75% doanh thu" mà không nói mẫu số là khách có mã (16.5% doanh thu không có mã khách).
- Tính doanh thu khách trên mọi dòng, kể cả hoá đơn huỷ (dòng âm) hoặc chưa bỏ `Price <= 0`.
- Lấy top 10% theo số dòng giao dịch thay vì theo doanh thu.
- Đặt ngưỡng VIP mà không kiểm khách lớn nhất có mua đều không: một đơn sỉ một lần không cần quản lý tài khoản.
