# Hướng làm: uplift modeling trên Hillstrom

Bài Advanced không có đáp án duy nhất. Số tham chiếu dưới đây từ bản cài đặt của người soạn: hai
nhánh Womens E-Mail và No E-Mail (42 693 khách), chia ngẫu nhiên 70/30 bằng
`np.random.default_rng(0).random(n) < 0.3` (12 612 khách test), feature là `recency`, `history`,
`mens`, `womens`, `newbie` và one-hot `zip_code`, `channel`.

## 1. Vì sao cần CATE

Tác động trung bình +4.5 điểm % che khuất một khác biệt lớn: với khách đã từng mua hàng nữ
(`womens = 1`) email làm visit tăng +7.3 điểm %, với khách chưa từng mua hàng nữ chỉ +1.1 điểm %.
Gửi cho tất cả là trả tiền làm phiền gần nửa danh sách mà gần như không thu được gì.

## 2. Kết quả trên tập test

| Xếp hạng | Qini coefficient |
| --- | --- |
| T-learner, logistic regression | 0.0044 |
| T-learner, gradient boosting (HistGradientBoosting, depth 3) | 0.0040 |
| Luật một cột: `womens` | 0.0038 |
| Ngẫu nhiên | ≈ 0 |

Uplift quan sát (visit, điểm %) trong top khách theo T-learner logistic:

| Top | Uplift quan sát | Uplift dự đoán trung bình |
| --- | --- | --- |
| 20% | +8.1 | +8.5 |
| 40% | +7.9 | +8.0 |
| 60% | +6.5 | +7.1 |
| 100% | +4.2 | +4.7 |

Đọc: mô hình xếp hạng có ích, nhưng chỉ hơn luật một cột `womens` một chút; gradient boosting không
hơn logistic. Lời giải tốt nói thẳng điều này: một luật minh bạch đạt gần hết giá trị thường là
lựa chọn tốt hơn cho vận hành.

## 3. Quy ra tiền và nhiễu

Trên tập test, uplift của `spend` cực nhiễu: toàn bộ test cho −$0.06 mỗi khách, top 40% theo
logistic cho +$0.23, top 20% cho −$0.31. Ở hai nhánh này chỉ 0.73% khách có chi tiêu, nên 12 nghìn khách không đủ để
chọn ngưỡng theo spend. Hướng đúng:

- Ước lượng lợi nhuận bằng chuỗi: uplift `visit` (ổn định) × tỉ lệ chuyển đổi khi visit × giá trị
  đơn trung bình, kèm bootstrap; hoặc dùng toàn bộ dữ liệu với cross-fitting.
- Báo cáo khoảng, không phải một con số; nói rõ chiến lược "chọn lọc" cần **thí nghiệm xác nhận**
  (random giữa "gửi theo mô hình" và "gửi cho tất cả"), vì ngưỡng được chọn sau khi nhìn dữ liệu.

## 4. Các lựa chọn phương pháp đáng bàn

- **T-learner** đơn giản nhưng hai mô hình học riêng có thể tạo uplift giả do nhiễu khác nhau. Với
  tác động nhỏ so với baseline (visit 10.6% ở nhóm không nhận email, uplift 4.5 điểm %), nên thử **X-learner**, **DR-learner** hoặc
  causal forest (`econml`) và so Qini.
- **S-learner** (một mô hình có biến treatment) dễ "bỏ quên" treatment khi tác động nhỏ, đặc biệt
  với cây có regularization.
- Không bao giờ chấm Qini trên tập huấn luyện.
- Uplift theo `visit` khác uplift theo lợi nhuận: khách bị email "đánh thức" ghé xem có thể không
  phải khách mua. Chọn outcome theo quyết định kinh doanh.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Cài đặt đúng | 15 | Test pass; đánh giá trên tập test tách riêng |
| So sánh mô hình | 20 | Ít nhất hai mô hình + một luật đơn giản + ngẫu nhiên; Qini và bảng top-k |
| Diễn giải CATE | 15 | Nêu nhóm khách hưởng lợi / không, có kiểm chứng bằng uplift quan sát |
| Quy ra tiền | 20 | Có chi phí email, biên lợi nhuận, khoảng không chắc chắn; nhận ra spend quá nhiễu |
| Phê phán | 15 | Thảo luận overfitting, chọn ngưỡng sau khi nhìn dữ liệu, giới hạn của T-learner |
| Báo cáo | 15 | Khuyến nghị ở đầu, ngôn ngữ kinh doanh, đề xuất thí nghiệm xác nhận |

Từ 70 điểm: đủ để đưa chiến lược nhắm mục tiêu vào thí nghiệm xác nhận.
