# Lời giải tham khảo: take-home 3 giờ - cắt 20% mã hàng

Bài Advanced không có một đáp án duy nhất. Dưới đây là hướng làm, các quyết định cần cân nhắc, số liệu tham chiếu (tính
trên dữ liệu thật, để người chấm kiểm số của ứng viên) và rubric.

## Hướng làm

1. **15 phút đầu: viết lại câu hỏi và giả định.** "Cắt mã nào, rủi ro gì" → hai câu: (1) tiêu chí chọn mã cắt; (2) cắt thì
   mất gì: doanh thu trực tiếp và khách. Ghi giả định cho chỗ đề không nói: kỳ phân tích, doanh thu gộp, mã nào là hàng hoá,
   không có tồn kho và giá vốn.
2. **Làm sạch có chủ đích.** Định nghĩa dùng chung (bỏ huỷ, số lượng/giá không dương) cộng lọc mã hàng hoá: `POST`, `DOT`,
   `M`, `AMAZONFEE`, `BANK CHARGES`, phiếu quà `gift_0001_*` không phải mã có thể "cắt". Chuẩn hoá `85123a` thành `85123A`.
3. **Phương án ngây thơ trước**, đo bằng `cut_impact`, để có mốc so sánh.
4. **Một phương án tốt hơn**, có tiêu chí giải thích được trong một câu.
5. **Viết bài nộp**: tóm tắt trước, bảng so sánh phương án, khuyến nghị có cách đo, giới hạn.

## Số liệu tham chiếu (12/2010-11/2011)

| Chỉ số | Giá trị |
| --- | --- |
| Dòng hàng hoá sau làm sạch (cả sheet / 12 tháng) | 527 725 / 502 695 |
| Doanh thu hàng hoá 12 tháng | 9 655 545 GBP |
| Số mã hàng hoá | 3 789 |
| Mã có đúng 1 khách có mã mua | 325 |
| 100 khách lớn nhất | 39.5% doanh thu khách có mã |

| Phương án | Số mã | Doanh thu mất trực tiếp | Khách bị ảnh hưởng | Doanh thu của các khách đó |
| --- | --- | --- | --- | --- |
| A: 20% doanh thu thấp nhất (757 mã, mã cao nhất 83.78 GBP/năm) | 757 | 0.25% | 954 (22.2%) | 29.8% |
| B: A trừ mã từng được 100 khách lớn nhất mua | 516 | 0.15% | 638 (14.9%) | 12.6% |

Trong phương án A có **79 mã bắt đầu bán từ tháng 9/2011**: thấp vì mới, không vì chậm. Một ứng viên tốt bắt được điều này.

Insight chính mà bài nộp tốt cần có: **về tiền, cắt mã bán chậm gần như miễn phí (0.25%); về khách, danh sách ngây thơ
chạm vào nhóm khách mang gần 30% doanh thu.** Rủi ro không nằm ở doanh thu mất trực tiếp mà ở hành vi của khách bị ảnh
hưởng. Phương án B giảm rủi ro đó hơn một nửa (29.8% → 12.6%) mà vẫn cắt được hai phần ba số mã mục tiêu.

## Quyết định cần cân nhắc

- **Kỳ phân tích**: 12 tháng đủ (bỏ 12/2011) hay cả sheet? Cả hai được nếu ghi rõ; trộn kỳ chưa đủ vào xếp hạng thì không.
- **Tiêu chí "chậm"**: doanh thu, số lượng, số hoá đơn hay số khách? Doanh thu là mặc định hợp lý khi không có giá vốn; số
  lượng thấp mà giá cao có thể là hàng giá trị. Giải thích lựa chọn quan trọng hơn lựa chọn.
- **Mã mới**: loại hoặc chuẩn hoá theo số tháng đã bán.
- **Biến thể**: nhiều mã là biến thể màu/cỡ (`85123A`, `85123B`); cắt theo dòng sản phẩm có thể hợp lý hơn từng mã.
- **Khách thiếu mã**: ~25% dòng; không đưa vào "khách bị ảnh hưởng" được, phải nói ra.
- **Phạm vi**: không cần làm market basket, dự báo hay model trong 3 giờ. Nhắc ở "Nếu có thêm thời gian" là đủ.

## Lỗi hay gặp

- Kể quá trình ("đầu tiên tôi load dữ liệu...") thay vì tóm tắt kết luận ở đầu.
- Chỉ báo doanh thu mất 0.25% và kết luận "an toàn", bỏ qua khách bị ảnh hưởng.
- Để `POST`/`DOT` trong bảng mã: `DOT` (phí dotcom) có doanh thu lớn và lọt lên đầu bảng.
- Làm 8 giờ: bài nộp đẹp nhưng nhật ký cho thấy không biết cắt phạm vi.
- Không có khuyến nghị đo được: "nên cân nhắc kỹ" không phải khuyến nghị.

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt tối đa khi |
| --- | --- | --- |
| Tóm tắt cho người ra quyết định | 20 | ≤ 150 từ, kết luận trước, ba con số đúng, có cả mặt tiền và mặt khách, có khuyến nghị |
| Giả định và làm sạch | 15 | Giả định cụ thể và hợp lý; lọc mã phí, chuẩn hoá mã, kỳ đủ; con số làm sạch khớp tham chiếu |
| Phân tích | 25 | Có phương án ngây thơ làm mốc; ít nhất một phương án tốt hơn với tiêu chí rõ; so cùng chỉ số; phát hiện mã mới hoặc biến thể |
| Khuyến nghị | 15 | Hành động cụ thể, theo đợt, có cách đo (nhóm khách bị ảnh hưởng, mốc thời gian) |
| Giới hạn và "nếu có thêm thời gian" | 10 | Nói đúng thứ thiếu (tồn kho, giá vốn, chi phí kho, lý do mua); việc tiếp theo xếp theo giá trị |
| Tái lập và code | 10 | Notebook chạy từ đầu tới cuối; ba hàm qua test; không đường dẫn tuyệt đối; chart có headline |
| Time box | 5 | Nhật ký trung thực, tổng ≤ 3.5 giờ, phân bổ có dành thời gian cho phần viết |

Thang: ≥ 80 mời vòng tiếp; 60-79 tuỳ vị trí; < 60 không đạt. Người chấm đọc tóm tắt trước, chỉ mở notebook khi tóm tắt đủ
thuyết phục hoặc có số đáng ngờ.
