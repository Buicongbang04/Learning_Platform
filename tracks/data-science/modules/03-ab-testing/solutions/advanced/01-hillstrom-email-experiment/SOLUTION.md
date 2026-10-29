# Hướng làm: thí nghiệm email Hillstrom

Bài Advanced không có đáp án duy nhất. Dưới đây là hướng làm, các số tham chiếu trên dữ liệu thật,
và rubric.

## 1. Độ tin cậy

- SRM: 21 307 / 21 387 / 21 306, chi-square p ≈ 0.90. Không có SRM.
- Balance check: `history` trung bình 240.9–242.8, `recency` 5.75–5.77, `newbie` 50.2–50.3% ở cả
  ba nhánh. Random hoạt động đúng.
- `spend`: chỉ 0.9% khách có chi tiêu (578 người), trong đó từ $30 tới $499, median $81.

## 2. Bảng tác động

Phương pháp hợp lý: hiệu trung bình kèm CI Welch cho cả ba metric (với metric 0/1 tương đương
z-test không pooled), Holm trên 6 kiểm định.

| Nhánh | visit | conversion | spend ($/khách) |
| --- | --- | --- | --- |
| Mens E-Mail | +7.7 điểm % [7.0, 8.3] | +0.68 điểm % [0.50, 0.86] | +0.77 [0.49, 1.05] |
| Womens E-Mail | +4.5 điểm % [3.9, 5.2] | +0.31 điểm % [0.15, 0.47] | +0.42 [0.17, 0.68] |

Cả 6 p-value đều rất nhỏ (lớn nhất ≈ 0.001), nên kết luận không đổi sau Holm.

Lỗi nặng cần tránh: tính "chi tiêu trung bình **của người mua**" rồi so giữa nhánh. Email thay đổi
*ai* mua, nên hai nhóm người mua không còn so sánh được (selection bias sau random).

## 3. Heterogeneous effect

Tác động lên visit (điểm %) và spend ($/khách) so với không gửi:

| Nhóm khách | Mens E-Mail | Womens E-Mail |
| --- | --- | --- |
| Đã từng mua hàng nam (`mens = 1`) | +8.2 / +0.90 | +2.2 / +0.26 |
| Chưa từng mua hàng nam | +7.1 / +0.62 | +7.4 / +0.63 |
| Đã từng mua hàng nữ (`womens = 1`) | +8.3 / +0.84 | +7.3 / +0.54 |
| Chưa từng mua hàng nữ | +6.9 / +0.68 | +1.1 / +0.28 |

Đọc: email nam hiệu quả trên diện rộng; email nữ chỉ hiệu quả với khách đã từng mua hàng nữ (hoặc
chưa mua hàng nam). Một chiến lược chọn lọc hợp lý: email nữ cho khách chỉ mua hàng nữ, email nam
cho phần còn lại. Đây là **giả thuyết** cần thí nghiệm xác nhận, vì được tìm ra sau khi nhìn dữ
liệu nhiều lát cắt.

## 4. Quy ra tiền

Lợi nhuận tăng thêm trên mỗi khách = 30% × spend lift − $0.10.

- Email nam cho tất cả: 0.3 × 0.77 − 0.10 ≈ $0.13 mỗi khách → khoảng **$13 000 trên 100 000 khách**,
  CI khoảng [$4 600, $21 600] (từ CI của spend).
- Email nữ cho tất cả: ≈ $0.027 mỗi khách → khoảng $2 700, CI chứa 0.

Lời giải tốt sẽ tính CI cho lợi nhuận (bootstrap hoặc biến đổi tuyến tính CI của spend), và chỉ ra
rằng chiến lược chọn lọc cần được ước tính trên dữ liệu chưa dùng để chọn (hoặc thí nghiệm mới).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Kiểm tra độ tin cậy | 15 | SRM, balance check, nhận xét về `spend` |
| Phương pháp đúng | 20 | Metric trên mỗi khách được random; CI; Holm; giải thích lựa chọn |
| Heterogeneous effect | 20 | So tác động giữa segment đúng cách; nêu rủi ro "đi câu" khi chia nhỏ |
| Quy ra tiền | 20 | Lợi nhuận có tính chi phí, có khoảng không chắc chắn |
| Báo cáo | 20 | Khuyến nghị ở câu đầu, ngôn ngữ kinh doanh, có giới hạn và bước tiếp theo |
| Không quá lời | 5 | Không gọi kết quả segment là "đã chứng minh" |

Đạt từ 70 điểm trở lên là mức làm việc được ở vị trí DS mid-level; trên 85 là mức senior.

## Bước tiếp theo nên đề xuất

- Thí nghiệm xác nhận chiến lược chọn lọc so với "email nam cho tất cả".
- Uplift model (module 06) để nhắm khách theo tác động dự đoán thay vì theo vài cột hồ sơ.
- Đo hiệu ứng dài hạn: tỉ lệ huỷ đăng ký email, chi tiêu sau 2 tuần.
