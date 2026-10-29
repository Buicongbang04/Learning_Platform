# Lời giải: 2SLS cho lợi suất của giáo dục

## Kết quả trên Card thật

| Ước lượng | Lợi suất mỗi năm học (log lương) | SE |
| --- | --- | --- |
| OLS, có biến kiểm soát | 0.0747 | 0.0035 |
| Wald (`nearc4`, không kiểm soát) | 0.188 | |
| First stage: `nearc4` → `educ` | +0.320 năm, F = 13.26 | 0.088 |
| 2SLS, có biến kiểm soát | **0.1315** | 0.0550 |

CI 95% của 2SLS khoảng [0.024, 0.239]: rộng gấp khoảng 16 lần CI của OLS. Đó là cái giá của IV: chỉ
dùng phần biến thiên của `educ` do `nearc4` gây ra, mà phần đó rất nhỏ (partial R² của first stage
chỉ 0.0044).

## Vì sao 2SLS **lớn hơn** OLS

Nếu chỉ có ability bias, ta kỳ vọng 2SLS nhỏ hơn OLS (OLS lệch lên). Card đưa ra hai lời giải thích
cho chiều ngược lại:

- **LATE, không phải ATE**: IV đo tác động trên **complier**: người đi học thêm *vì* sống gần
  trường. Đó thường là người có chi phí đi học cao (gia đình nghèo hơn), nên lợi ích biên của một
  năm học với họ có thể cao hơn trung bình.
- **Sai số đo lường** của `educ` kéo OLS về 0 (attenuation bias), IV sửa được phần này.

Câu trả lời senior trong phỏng vấn phải nói rõ: 2SLS ước lượng tác động cho **ai**.

## Ba giả định và cách kiểm tra

| Giả định | Kiểm được? | Ở bài này |
| --- | --- | --- |
| Relevance: z ảnh hưởng tới d | Có, bằng first stage F | F = 13.26: vượt ngưỡng 10 quen thuộc, nhưng chưa thoải mái. Stock–Yogo và Lee et al. (2022) cho thấy với F quanh 10, t-test 5% thực chất có size cao hơn 5%; nên dùng CI Anderson–Rubin |
| Exclusion: z chỉ tác động y qua d | **Không** kiểm được bằng dữ liệu | Sống gần trường có thể gắn với thành phố lớn, thị trường lao động tốt hơn: vì thế phải kiểm soát `smsa66`, vùng |
| Monotonicity: không ai học **ít** đi vì sống gần trường | Không kiểm được | Hợp lý về nghiệp vụ |

Một kiểm tra gián tiếp cho exclusion: so covariate trước "điều trị" theo instrument. Trên Card, người
sống gần trường có IQ trung bình 103.2 so với 100.6, cha học 10.4 so với 9.2 năm, sống ở thành phố
năm 1966 nhiều hơn hẳn (80% so với 33%). Instrument **không** ngẫu nhiên như một thí nghiệm; nó chỉ
có giá trị nếu sau khi kiểm soát các biến địa lý, phần còn lại "gần như ngẫu nhiên".

## Instrument yếu

Khi F nhỏ, 2SLS lệch về phía OLS và CI thông thường sai. Mô phỏng trong test: instrument mạnh cho
F khoảng 650–890, instrument yếu (n = 2 000, hệ số 0.05) cho F dưới 7 qua 15 seed. Quy tắc thực
hành: luôn báo cáo F của first stage; nếu dưới 10 (hoặc dưới khoảng 104 theo Lee et al. 2022 nếu
muốn t-test 5% đúng size) thì báo CI Anderson–Rubin.

## Trong sản phẩm số

IV xuất hiện thường nhất dưới dạng **encouragement design**: random việc *mời* dùng tính năng (z),
không random việc *dùng* (d). Ví dụ Olist random gửi email giới thiệu chương trình seller ưu tiên;
email là instrument cho việc tham gia. Thí nghiệm có non-compliance cũng vậy: ITT chia cho tỉ lệ
tuân thủ chính là Wald estimator, ước lượng tác động trên complier.
