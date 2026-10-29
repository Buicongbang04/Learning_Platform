# Hướng làm: thí nghiệm cấp cửa hàng trên Rossmann

Bài Advanced không có đáp án duy nhất. Dưới đây là hướng làm, số tham chiếu trên dữ liệu thật và
rubric.

## Ba hàm được chấm

- `store_panel`: lọc `Open == 1` **trước** khi tính trung bình. Nếu tính cả ngày đóng cửa (Sales =
  0), cửa hàng đóng cửa sửa chữa vài ngày trông như "doanh số giảm", và số ngày Chủ nhật trong cửa
  sổ làm nhiễu metric.
- `estimate`: ba nhánh dùng chung một hàm Welch. CUPED tính `theta` trên dữ liệu gộp;
  post-stratification theo `pd.qcut(pre, 10)`.
- `power_study`: `rng.permutation` một mảng cân bằng sẵn (đúng 557 cửa hàng treatment). Random hoàn
  toàn bằng `rng.random() < 0.5` cũng đúng, nhưng với ít đơn vị thì cỡ nhóm dao động làm mất power.

## Số tham chiếu trên dữ liệu thật

1 115 cửa hàng, `y` trung bình 7 014.2, tương quan `pre`–`y` là 0.9908.

| Phương pháp | SE | MDE (power 80%) | MDE / mean |
| --- | --- | --- | --- |
| Hiệu trung bình | 146.3 | 410.0 | 5.84% |
| Post-stratification 10 decile `pre` | 56.0 | 156.8 | 2.23% |
| CUPED với `pre` | 19.8 | 55.5 | 0.79% |

Tỉ lệ $$|z| > 1.96$$ qua 1 000 lần chia trên dữ liệu thật:

| Phương pháp | A/A (lift 0) | lift 1% | lift 2% | lift 5% |
| --- | --- | --- | --- | --- |
| Hiệu trung bình | 5.0% | 6.7% | 15.5% | 65.6% |
| Post-stratification | 4.6% | 23.3% | 70.7% | 100% |
| CUPED | 5.4% | 93.6% | 100% | 100% |

Chia tầng theo `StoreType` chỉ giải thích 4.0% variance của `y`; theo decile `pre` giải thích
85.9%. CUPED khai thác trọn tương quan 0.99 ($$\rho^2 = 0.98$$), còn decile chỉ dùng thông tin "ở
khoảng nào", mất phần biến thiên trong decile.

Thiết kế mạnh nhất: **stratified sampling theo decile `pre` khi gán, CUPED (hoặc hồi quy có `pre`)
khi phân tích**. Gán theo tầng bảo đảm hai nhánh cân bằng về quy mô cửa hàng ngay từ đầu (quan trọng
khi chỉ có 1 115 đơn vị và lãnh đạo sẽ nhìn bảng so sánh), CUPED lo phần độ nhạy.

## Các quyết định thiết kế cần cân nhắc

**Metric.** Doanh số trung bình ngày mở cửa, không phải tổng doanh số (phụ thuộc số ngày mở). Cân
nhắc thêm số khách (`Customers`) và giá trị giỏ (`Sales / Customers`, metric tỉ số: delta method
theo cửa hàng nếu tính trên tổng).

**Thời lượng.** Trọn số tuần. Ngày lễ trong kỳ thí nghiệm (ngày 4/6/2015 là ngày lễ với 766 trên 1 115 cửa hàng; kỳ trước có hai ngày lễ toàn quốc 14/5 và 25/5) làm
lệch cả hai nhánh như nhau nếu random đúng, nhưng làm `pre` và `y` kém tương quan hơn. Nên kiểm lại
tương quan trên vài cặp cửa sổ lịch sử khác nhau.

**Spillover.** Hai cửa hàng gần nhau ở hai nhánh: khách có thể chuyển sang cửa hàng bày đẹp hơn,
phóng đại tác động. Rossmann không có toạ độ cửa hàng, nhưng thiết kế tốt nêu rủi ro này và đề xuất
random theo cụm khu vực nếu có dữ liệu.

**Novelty.** Cách bày mới thu hút khách quen tò mò tuần đầu; nhân viên cũng cần thời gian quen. Đề
xuất xem tác động theo tuần và cân nhắc bỏ tuần đầu khỏi phân tích chính (định trước).

**Guardrail.** Số khách, tỉ lệ hết hàng, giờ công nhân viên.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Ba hàm đúng và test xanh | 15 | Test pass, code đọc được |
| Kiểm chứng bằng dữ liệu thật | 20 | A/A cho cả ba cách, power ở nhiều mức lift, nhận xét A/A đúng khoảng 5% |
| Thiết kế gán và phân tích | 20 | Chọn rõ cách gán (có/không chia tầng, theo gì) và cách phân tích, có lý do bằng con số |
| Hiểu vì sao | 15 | Giải thích bằng $$\rho^2$$ / phần variance giải thích được, so `StoreType` với decile |
| Rủi ro | 15 | Ít nhất 3 rủi ro cụ thể của thí nghiệm cửa hàng (spillover, ngày lễ, đóng cửa, novelty) kèm cách phòng |
| Kế hoạch phân tích | 10 | Kiểm định, quy tắc quyết định, guardrail, xử lý cửa hàng thiếu dữ liệu, định trước |
| Trình bày | 5 | Người vận hành đọc được, có khuyến nghị ở đầu |

Từ 70 điểm trở lên là thiết kế đủ để đưa vào review.

## Sai lầm hay gặp

- Báo cáo "CUPED giảm 98% variance nên chỉ cần khoảng 21 cửa hàng thay vì 1 115": tương quan đo trên một cặp tháng; với
  vài chục đơn vị, ước lượng `theta` và SE đều kém tin cậy, và một cửa hàng bất thường chi phối kết
  quả.
- Dùng `pre` là kỳ **chồng** lên kỳ thí nghiệm (ví dụ trung bình tháng 5 và 6): covariate chứa tác
  động.
- Không kiểm A/A trên dữ liệu thật mà tin công thức: với ít đơn vị và phân phối lệch, A/A là cách
  rẻ nhất để biết phương pháp có giữ đúng 5% không.
