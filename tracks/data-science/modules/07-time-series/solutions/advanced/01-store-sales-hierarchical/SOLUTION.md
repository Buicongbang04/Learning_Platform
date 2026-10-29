# Hướng làm: dự báo phân cấp cho Rossmann

Bài Advanced không có đáp án duy nhất. Dưới đây là hướng làm, các số tham chiếu chạy trên dữ liệu
thật khi soạn bài, và rubric.

## 1. Dữ liệu

- 20 cửa hàng: loại a {2, 3, 5, 6, 7}, b {85, 259, 262, 274, 335}, c {1, 4, 21, 25, 34},
  d {15, 18, 23, 26, 29}. 133 tuần (nhãn Chủ nhật 2013-01-13 tới 2015-07-26). Tổng Total
  131 986 711 €; tuần cuối 893 630 €.
- Cửa hàng 25 có 3 tuần doanh thu bằng 0, cửa hàng 259 có 1 tuần (đóng cửa cả tuần, tuần 2013-02-03
  và cụm tuần cuối tháng 1, đầu tháng 2/2014). Loại b chỉ có 17 cửa hàng trên toàn chuỗi, nhưng mỗi
  cửa hàng lớn (cửa hàng 262 bán trung bình khoảng 145 nghìn €/tuần, gấp 5 lần cửa hàng 1).
- Doanh thu tuần có mùa vụ năm rất mạnh (Giáng sinh, hè), nên seasonal naive 52 tuần mạnh hơn hẳn
  mọi model chỉ nhìn vài tuần gần nhất.

## 2. Kết quả tham chiếu

Horizon 6 tuần, hai origin. MAE (€/tuần) trung bình trên các node của mỗi cấp.

Origin test 2015-06-21 tới 2015-07-26:

| Base | Cách | Total | Loại | Cửa hàng |
| --- | --- | --- | --- | --- |
| Holt damped mọi node | base | 131 077 | 32 781 | 6 891 |
| | bottom_up | 131 047 | 32 762 | 6 891 |
| | ols | 131 085 | 32 771 | 6 884 |
| Seasonal naive 52 mọi node | mọi cách | 51 525 | 13 588 | 3 457 |
| Hỗn hợp: Total + loại dùng seasonal naive 52, cửa hàng dùng Holt | base | 51 525 | 13 588 | 6 891 |
| | bottom_up | 131 047 | 32 762 | 6 891 |
| | ols | 50 353 | 12 975 | 3 738 |
| | wls_struct | 55 081 | 14 482 | 3 980 |
| | wls_var | 100 739 | 25 185 | 5 625 |

Origin test 2015-05-10 tới 2015-06-14, cấu hình hỗn hợp: base 35 540 / 12 861 / 6 505; bottom_up
108 416 / 30 405 / 6 505; ols 34 768 / 12 457 / 3 602; wls_struct 33 890 / 14 334 / 3 749; wls_var
79 260 / 24 076 / 5 289.

`wls_var` dùng phương sai residual in-sample một bước (Holt) hoặc residual năm trước (seasonal
naive 52).

## 3. Đọc kết quả

1. **Base forecast tuyến tính và giống nhau ở mọi node thì đã coherent.** Seasonal naive 52 của
   Total đúng bằng tổng seasonal naive 52 của các cửa hàng, nên reconcile không đổi gì. Đây là kiểm
   tra nhanh để biết code reconcile đúng.
2. **Holt damped mọi node**: base gần coherent (lệch tối đa khoảng 1 300 € trên tổng gần 900 nghìn),
   reconcile gần như không đổi MAE. Reconcile không biến model tệ thành model tốt.
3. **Cấu hình hỗn hợp là nơi reconcile có giá trị**: cấp trên có thông tin tốt (mùa vụ năm), cấp
   cửa hàng thì không. `bottom_up` vứt thông tin cấp trên nên tệ ở mọi cấp. `ols` kéo dự báo cửa hàng
   về phía thông tin mùa vụ của cấp trên: MAE cửa hàng giảm từ 6 891 xuống 3 738 (origin 1) và từ
   6 505 xuống 3 602 (origin 2), gần bằng seasonal naive 52 chạy riêng từng cửa hàng.
4. **`wls_var` tệ** vì residual in-sample một bước của Holt rất nhỏ so với sai số 6 tuần, nên
   phương pháp tin nhầm vào cấp cửa hàng. Trọng số phải phản ánh sai số **ở đúng horizon**; residual
   in-sample một bước là xấp xỉ kém. MinT với ma trận hiệp phương sai co (shrinkage) ước lượng từ
   sai số backtest h bước là hướng mở rộng tốt.
5. Kết luận cho lãnh đạo: dùng seasonal naive 52 (hoặc model có mùa vụ năm) cho mọi node; nếu đội
   cửa hàng muốn dùng model riêng, bắt buộc reconcile bằng OLS để con số cửa hàng khớp tổng và hưởng
   thông tin cấp trên.

## 4. Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Code và test | 15 | Mọi test pass; `reconcile` dùng `solve` thay vì nghịch đảo tường minh khi có thể |
| Base forecast | 15 | Ít nhất hai cấu hình, có lý do chọn (mùa vụ năm, đóng cửa cả tuần) |
| Backtest | 20 | Ít nhất hai origin, MAE theo từng cấp, cùng horizon cho mọi cách |
| Phân tích cơ chế | 25 | Giải thích được khi nào reconcile không đổi gì, khi nào giúp, vì sao `bottom_up` hoặc `wls_var` có thể tệ |
| Báo cáo | 20 | Khuyến nghị ở câu đầu, ngôn ngữ vận hành, có giới hạn (20 cửa hàng, tuần đóng cửa, chỉ 2 năm rưỡi lịch sử) |
| Không quá lời | 5 | Không kết luận chung cho mọi chuỗi từ hai origin |

Từ 70 điểm: mức DS mid-level. Từ 85: senior.

## 5. Mở rộng

- MinT-shrink (Wickramasuriya, Athanasopoulos & Hyndman 2019) với hiệp phương sai sai số backtest.
- Thêm cấp `Assortment` hoặc bang (cấu trúc grouped, không còn là cây).
- Reconcile khoảng dự báo, không chỉ dự báo điểm.
