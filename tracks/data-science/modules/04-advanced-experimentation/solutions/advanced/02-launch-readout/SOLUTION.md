# Hướng làm: đọc kết quả ra mắt, novelty và heterogeneous effect

Bài Advanced không có đáp án duy nhất. Dưới đây là hướng làm, số tham chiếu với
`make_launch_log(seed=0)` và rubric.

## Các hàm được chấm

- `effect_by_exposure_day`: tính `exposure_day = day − first_day`, nhóm theo nó, Welch trong từng
  nhóm. Bỏ ngày phơi nhiễm thiếu một nhánh; để `se` là `NaN` khi một nhánh chỉ có một dòng.
- `novelty_slope`: lọc `se` hữu hạn và dương, WLS bằng công thức đóng. Điểm ở ngày phơi nhiễm cao
  có ít user (chỉ user vào sớm), `se` lớn, nên tự nhận trọng số nhỏ.
- `user_level` + `interaction_test`: Welch trong từng nhóm để báo cáo, OLS `treat * C(segment)` với
  HC1 và Wald test chung cho các hệ số `treat:` để kiểm định khác biệt.

## Số tham chiếu

| Con số | Giá trị |
| --- | --- |
| Dữ liệu | 253 299 user-ngày, 19 982 user (70.2% existing) |
| Dashboard: chênh lệch phút mọi user-ngày | +0.846 |
| Tác động ngày phơi nhiễm 0 / 3 / 6 | +2.89 / +1.67 / +0.79 |
| Độ dốc WLS ngày 0–20 | −0.098 phút mỗi ngày (SE 0.010) |
| Độ dốc riêng existing / new | −0.114 (SE 0.011) / −0.020 (SE 0.022, p = 0.38) |
| Ngày phơi nhiễm ≥ 14: existing / new | +0.41 / +1.00 |
| Tác động dài hạn, trọng số theo tỉ lệ user | +0.59, CI 95% [0.16, 1.02] với SE theo user |
| Tương tác theo user-level trung bình 4 tuần: segment / platform | p = 0.80 / p = 0.22 |

## Những điều lời giải tốt phải thấy

**Novelty ở user cũ, không ở user mới.** Tác động ngày đầu gần +2.9 phút, giảm đều; user mới không
có giao diện cũ để so nên không có hiệu ứng "lạ mắt". Tách theo segment là cách nhìn ra điều này.

**Con số dashboard phóng đại.** +0.846 trộn những ngày đầu hào hứng. Tác động dài hạn ước lượng
khoảng +0.59, và CI rộng: [0.16, 1.02]. Kế hoạch doanh thu nên dùng con số này kèm khoảng, không
dùng +0.846.

**Bẫy thành phần.** Cửa sổ "ngày phơi nhiễm ≥ 14" chỉ có 11.4% user-ngày từ user mới, so với 16.9%
toàn kỳ, vì user mới vào muộn. Lấy chênh lệch thô trong cửa sổ đó (+0.411) là ước lượng cho một tổng
thể toàn user cũ. Phải ước lượng **từng segment** rồi gộp theo tỉ lệ user thật (70/30).

**Bẫy SE.** Trong cửa sổ cuối, mỗi user có nhiều dòng. SE coi dòng độc lập cho existing là 0.097;
SE đúng (gộp theo user, delta method như bài Basic 02) là 0.236, design effect gần 6. CI sai sẽ hẹp
gấp hơn hai lần.

**Heterogeneous effect bị novelty che.** Theo trung bình 4 tuần mỗi user, existing (+0.93) và new
(+1.02) gần như bằng nhau, p tương tác 0.80: kết luận "tác động đồng đều" là sai. Tác động dài hạn
của user mới gấp khoảng 2.4 lần user cũ; novelty của user cũ bù vào trong 4 tuần. Bài học: phân tích
HTE trên cửa sổ có novelty có thể ra kết luận ngược hoàn toàn. Platform không có khác biệt (p =
0.22); đừng kể chuyện "iOS kém hơn" từ +0.60 so với +1.06.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm đúng và test xanh | 15 | Test pass |
| Phát hiện novelty | 15 | Tác động theo ngày phơi nhiễm (không theo ngày lịch), có kiểm định xu hướng, tách segment |
| Ước lượng dài hạn | 20 | Có cách ước lượng rõ ràng, xử lý thay đổi thành phần segment, CI dùng SE theo user |
| Heterogeneous effect | 15 | Kiểm định tương tác, không suy diễn từ "nhóm này có ý nghĩa"; nhận ra HTE bị novelty che |
| Khuyến nghị | 15 | Quyết định rõ, con số cho kế hoạch kèm khoảng, không dùng con số dashboard |
| Giới hạn và bước tiếp | 15 | Nêu primacy, network effect (chia sẻ truyện giữa user), mùa vụ; đề xuất holdout dài hạn hoặc chạy thêm |
| Trình bày | 5 | PM đọc được, khuyến nghị ở đầu |

Từ 70 điểm trở lên là đạt.

## Tham số sinh dữ liệu (đọc sau khi làm xong)

User cũ (70%): tác động $$3 e^{-e/4} + 0.5$$ phút với $$e$$ là ngày phơi nhiễm; user mới (30%): +1.0
không đổi. Không có khác biệt theo platform. Tác động dài hạn thật của tổng thể là
$$0.7 \times 0.5 + 0.3 \times 1.0 = 0.65$$; ước lượng +0.59 với CI [0.16, 1.02] chứa giá trị này.
