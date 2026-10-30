# Hướng làm: win-back theo phân khúc RFM

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết hai hàm, chuỗi phân tích tham chiếu, các con số
trên bộ thật (theo lựa chọn gợi ý trong đề), các quyết định cần cân nhắc và rubric chấm memo.

## Hai hàm

- **`segment_outcomes`**: lọc dòng trong `[start, end)` và có `Customer ID` thuộc `segments.index`; doanh thu theo
  khách; dựng bảng một dòng mỗi khách của `segments` với doanh thu (0 nếu không mua) và cờ active; `groupby` phân
  khúc. Mẫu số là **mọi** khách của phân khúc, không chỉ khách có mua: "doanh thu mỗi khách" phải gồm cả khách đã đi.
- **`campaign_value`**: số khách active = `customers × active_share`; doanh thu mỗi khách active = `revenue / active`
  (0 khi không ai active, tránh chia cho 0); lợi nhuận thêm = `customers × uplift × doanh thu mỗi khách active ×
  margin`. `uplift` dạng Series thì `reindex(outcomes.index).fillna(0)`.

## Chuỗi phân tích và con số tham chiếu

Phân khúc: RFM (ngưỡng và bảng luật của bài Intermediate 01) trên 01/06/2010-31/05/2011, ngày chốt 01/06/2011;
4 338 khách. Kết quả: 01/06-09/12/2011 (cửa sổ `[2011-06-01, 2011-12-10)`).

| Phân khúc | Khách | % quay lại mua | Doanh thu mỗi khách (GBP) | % doanh thu |
| --- | --- | --- | --- | --- |
| champions | 312 | 95.2% | 5 391 | 35.6% |
| loyal | 574 | 92.2% | 2 557 | 31.1% |
| at_risk | 615 | 62.0% | 690 | 9.0% |
| hibernating | 1 747 | 35.4% | 209 | 7.7% |
| potential_loyalist | 340 | 76.2% | 643 | 4.6% |
| need_attention | 228 | 73.7% | 850 | 4.1% |
| new | 47 | 53.2% | **3 898** | 3.9% |
| about_to_sleep | 391 | 47.6% | 328 | 2.7% |
| promising | 67 | 58.2% | 546 | 0.8% |
| cant_lose | 17 | 64.7% | 1 324 | 0.5% |

- **Bẫy "new"**: 168 470 GBP của phân khúc new là **một** hoá đơn (581483, khách 16446, 09/12/2011) bị huỷ 12 phút
  sau (module 08, Advanced 01). Bỏ hoá đơn đó, new còn 314 GBP mỗi khách. Ai xếp "new" là nhóm giá trị thứ hai mà
  không kiểm là đã rơi vào bẫy.
- **Tách at_risk theo M**: M từ 4: 361 khách, 69.3% quay lại, 1 008 GBP mỗi khách, 85.8% doanh thu của at_risk;
  M 1-3: 254 khách, 51.6%, 236 GBP.
- **Champions và loyal tự quay lại 92-95%**: chiến dịch giảm giá cho họ chủ yếu trả tiền cho đơn đằng nào cũng có
  (uplift gần 0, chi phí là toàn bộ giá trị ưu đãi).
- **Kịch bản** (giả định uplift 10%, biên 35%, 15 GBP mỗi khách cho cuộc gọi): at_risk M từ 4 có lợi nhuận gộp thêm
  khoảng 18 400 GBP, chi phí 5 415, net khoảng 13 000 GBP; at_risk M 1-3 net khoảng 270 GBP. Cùng uplift 10% cho
  champions thì "net" khoảng 57 000 GBP trên giấy, nhưng đó là ảo giác vì uplift thật gần 0.

Headline mẫu: **"Dồn win-back vào 361 khách at_risk giá trị cao: 69% tự quay lại, mỗi khách 1 008 GBP trong 6 tháng"**.

## Các quyết định cần cân nhắc

- **Không nhìn trước đáp án**: phân khúc chỉ từ dữ liệu trước ngày chốt.
- **Mùa vụ**: cửa sổ kết quả chứa mùa cao điểm 9-11, tỉ lệ quay lại cao hơn bình thường. So sánh **giữa** phân khúc
  vẫn hợp lệ; con số tuyệt đối thì không dùng cho nửa đầu năm.
- **Doanh thu gộp hay ròng**: hoá đơn bị huỷ về sau làm sai một phân khúc nhỏ; bỏ hoặc ghi chú.
- **Uplift không đo được từ dữ liệu quá khứ**: chỉ có thử nghiệm. Đề xuất nhóm đối chứng ngẫu nhiên (10-20%) và metric
  chính là doanh thu mỗi khách trừ giá trị ưu đãi, guardrail là biên lợi nhuận.
- **Kênh theo giá trị**: khách sỉ giá trị cao đáng một cuộc gọi; nhóm giá trị thấp chỉ đáng email.
- **Khách lớn**: báo trung vị hoặc tách khách sỉ khi trung bình bị vài khách quyết định.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Khung thời gian đúng | 15 | Phân khúc chỉ từ dữ liệu trước ngày chốt; cửa sổ kết quả nêu rõ; nhắc mùa vụ của cửa sổ |
| Bằng chứng theo phân khúc | 20 | Bảng tỉ lệ quay lại và doanh thu mỗi khách cho các phân khúc chính; tách ít nhất một phân khúc theo giá trị (M) |
| Kiểm ngoại lệ | 15 | Phát hiện doanh thu của một phân khúc bị một khách/hoá đơn quyết định (hoá đơn 581483) và xử lý |
| Đề xuất | 20 | Chọn nhóm có giá trị thu hồi cao và chưa tự quay lại hết; nói rõ vì sao không chi cho champions/loyal; kênh hợp với giá trị khách |
| Đo lường | 15 | Nhóm đối chứng ngẫu nhiên, metric chính trừ chi phí ưu đãi, guardrail, thời điểm đọc kết quả |
| Giả định và memo | 15 | Mọi số không đến từ dữ liệu ghi "giả định"; headline trả lời thẳng câu hỏi; người đọc không cần biết tên cột |

Từ 70 điểm trở lên là memo gửi được cho Head of CRM.

## Sai lầm hay gặp

- Chọn champions vì "net" lớn nhất trong bảng kịch bản với cùng một uplift cho mọi phân khúc.
- Dùng RFM tính trên cả năm (gồm cả 6 tháng sau ngày chốt) rồi đo kết quả trên chính 6 tháng đó.
- Báo "phân khúc new mang lại 3 898 GBP mỗi khách" mà không kiểm hoá đơn lớn.
- Đề xuất chiến dịch không có nhóm đối chứng: mọi khách quay lại đều bị tính là nhờ chiến dịch.
