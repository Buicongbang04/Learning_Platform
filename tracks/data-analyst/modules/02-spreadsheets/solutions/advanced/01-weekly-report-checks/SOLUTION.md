# Lời giải: báo cáo tuần có kiểm lỗi

Bài advanced không có workbook lời giải; dưới đây là hướng làm, quyết định, số tham chiếu và rubric.
Bản tham chiếu đã được dựng và chạy qua test (5/5 pass).

## Hướng làm

Cột phụ ở `Data` (một cách làm, không bắt buộc):

| Cột | Ý nghĩa | Công thức (hàng 2) |
| --- | --- | --- |
| I `Valid` | Dòng hợp lệ | `=IF(AND(LEFT(A2,1)<>"C",D2>0,F2>0),1,0)` |
| J `Revenue` | Doanh thu dòng | `=I2*D2*F2` |
| K `Week` | Thứ Hai của tuần | `=INT(E2)-WEEKDAY(E2,2)+1` |
| L `OrderStart` | Dòng hợp lệ đầu của hoá đơn | `=IF(I2=0,0,IF(COUNTIFS(A$1:A1,A2,I$1:I1,1)=0,1,0))` |
| M `CustWeekStart` | Lần đầu khách có dòng hợp lệ trong tuần | `=IF(OR(I2=0,G2=""),0,IF(COUNTIFS(G$1:G1,G2,K$1:K1,K2,I$1:I1,1)=0,1,0))` |
| N `Key` | Khoá 8 cột | `=CONCAT(A2,"\|",B2,"\|",C2,"\|",D2,"\|",TEXT(E2,"yyyy-mm-dd hh:mm"),"\|",F2,"\|",G2,"\|",H2)` |
| O `Dup` | Trùng một dòng phía trên | `=IF(SUMPRODUCT(--(N$1:N1=N2))>0,1,0)` |
| P `CustStart` | Lần đầu khách có dòng hợp lệ trong 5 tuần | như M nhưng bỏ điều kiện tuần |

Weekly: `B2 =SUMIFS(Data!$J:$J,Data!$K:$K,A2)`, `C2` và `D2` là SUMIFS trên L, M; `E2 =B2/C2`;
`F3 =B3/B2-1`; `B7`, `C7` là SUM; `D7 =SUM(Data!P:P)`; `E7 =B7/C7`.

Checks: `B2 =ABS(Weekly!B7-SUM(Data!J:J))<0.01`, `B3 =Weekly!C7=SUM(Data!L:L)`,
`B4 =COUNTIFS(Data!E:E,">="&Weekly!A2,Data!E:E,"<"&(Weekly!A6+7))=COUNTA(Data!A2:A6730)`,
`B5 =COUNTA(Data!A2:A6730)-SUM(Data!I:I)`, `B6 =SUM(Data!O:O)`, `B7 =AND(B2,B3,B4)`.

Lưu ý B3 kiểm cùng một cột L với C7 nên chỉ bắt lỗi cộng/kéo công thức ở Weekly; kiểm độc lập hơn là đếm
hoá đơn hợp lệ khác nhau bằng cách khác (pivot, hoặc `SUMPRODUCT(1/COUNTIF(...))` trên mã hoá đơn hợp lệ).
Rubric cộng điểm cho kiểm tra độc lập.

## Số tham chiếu

| Tuần (thứ Hai) | Doanh thu (GBP) | Đơn | Khách | AOV | WoW |
| --- | --- | --- | --- | --- | --- |
| 31/10 | 33 858.24 | 51 | 42 | 663.89 | |
| 07/11 | 36 910.10 | 61 | 40 | 605.08 | +9.0% |
| 14/11 | 56 727.46 | 87 | 64 | 652.04 | +53.7% |
| 21/11 | 39 423.47 | 58 | 40 | 679.72 | −30.5% |
| 28/11 | 31 936.20 | 57 | 46 | 560.28 | −19.0% |
| 5 tuần | 198 855.47 | 314 | 176 khác nhau (232 lượt khách-tuần) | 633.30 | |

Checks: 209 dòng bị loại (204 dòng huỷ, 5 dòng giá 0), 24 dòng trùng hoàn toàn, khách vãng lai (không có
Customer ID) mang 3 340.46 GBP trong 5 tuần.

Drill-down tuần 14/11 (+19 817 GBP so với tuần trước) theo quốc gia: Australia +5 355.40 GBP (khách 12415, 2 hoá
đơn, tuần trước 0), Japan +4 808.48 GBP (một hoá đơn của khách 12753, tuần trước 0), Germany +4 810.57 GBP, trong khi
Netherlands giảm 9 266.38 GBP so với tuần 07/11. Khoảng một nửa mức tăng đến từ hai đơn lớn ở hai thị trường mua
thưa, không phải xu hướng chung.

Ghi chú mẫu: "Doanh thu khách quốc tế 5 tuần 31/10–04/12/2011 là 198 855 GBP. Tuần 14/11 tăng 53.7% lên
56 727 GBP, chủ yếu do hai đơn lớn từ Australia (5 355 GBP) và Japan (4 808 GBP), hai thị trường mua không
đều; không nên coi là xu hướng. Hai tuần sau giảm 30.5% và 19.0%, về gần mức đầu kỳ. Có 24 dòng trùng
hoàn toàn trong dữ liệu (đang giữ trong doanh thu) cần team hệ thống xác nhận. Đề xuất theo dõi riêng
doanh thu không tính 5 đơn lớn nhất mỗi tuần để thấy xu hướng nền."

## Quyết định cần nêu

- **Doanh thu gộp** theo định nghĩa chung (đơn huỷ loại khỏi doanh thu, không trừ ngược); nói rõ trong
  README của workbook, vì finance có thể dùng doanh thu ròng.
- **Dòng trùng giữ lại và báo ra**: hai dòng giống hệt có thể là hai lần quét hàng thật; tự xoá là đổi số
  liệu không ai biết. Báo số lượng, hỏi chủ hệ thống.
- **D7 là khách khác nhau**: cộng 5 tuần ra 232, đếm một khách nhiều lần.
- **Tuần thứ Hai–Chủ nhật** và đủ 5 tuần: không có tuần dở dang ở đầu/cuối.
- **Khách vãng lai** có trong doanh thu và số đơn nhưng không trong số khách; ghi chú để người đọc không
  chia doanh thu cho số khách ra "doanh thu/khách" sai.

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Độ đúng Weekly | 25 | Toàn bộ test Weekly pass; WoW và AOV đúng; D7 là khách khác nhau |
| Thiết kế workbook | 20 | Cột phụ có tiêu đề rõ, một định nghĩa ở một chỗ, không số gõ tay, tham chiếu `$` đúng, sheet README/ghi chú định nghĩa (doanh thu gộp, tuần thứ Hai, khách vãng lai) |
| Kiểm tra | 25 | B2:B7 đúng (10); ít nhất một kiểm tra đi đường tính độc lập với Weekly (10); ALL OK nổi bật bằng conditional formatting ở đầu Weekly hoặc Checks (5) |
| Ghi chú cho stakeholder | 20 | Nêu tuần bất thường kèm nguyên nhân có số (drill-down quốc gia/hoá đơn) (10); nêu vấn đề chất lượng dữ liệu (dòng trùng, khách vãng lai) (5); có việc tiếp theo cụ thể (5) |
| Trình bày | 10 | Định dạng số/ngày, chart doanh thu tuần có headline là kết luận, không chartjunk |

Trừ điểm: kết luận "xu hướng tăng" từ một tuần (−5); tự xoá dòng trùng không nói (−5); số trong ghi chú
lệch với Weekly (−5).
