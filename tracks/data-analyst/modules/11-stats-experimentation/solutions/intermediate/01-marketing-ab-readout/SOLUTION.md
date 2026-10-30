# Lời giải: đọc kết quả A/B chiến dịch quảng cáo

## Cách làm

1. **`summarize`**: `groupby("group")` đếm người và cộng `converted`; `rate = conversions / users`.
2. **`srm_check`**: số kỳ vọng = tỉ lệ **thiết kế** × tổng quan sát, rồi `stats.chisquare`. Lấy quan sát theo thứ
   tự khoá của `expected_share` để Series và dict theo thứ tự nào cũng ra cùng kết quả. Tỉ lệ thiết kế phải lấy từ
   brief/cấu hình thí nghiệm, không từ dữ liệu: lấy từ dữ liệu thì SRM luôn "đạt".
3. **`segment_balance`**: `pd.crosstab(segment, group)` rồi `chi2_contingency(correction=False)` (Yates chỉ áp dụng
   bảng 2×2 và làm kiểm định bảo thủ hơn; ghi rõ để kết quả không phụ thuộc mặc định của thư viện).
4. **`diff_ci`**: khoảng Wald với phương sai riêng (ước lượng, không giả định H0); p với tỉ lệ gộp (giả định H0
   "hai nhóm như nhau"), giống `proportions_ztest`. Vì vậy trong vài trường hợp sát ngưỡng, CI có thể chạm 0 trong
   khi p hơi dưới 0.05; với cỡ mẫu này không xảy ra.
5. **`decide`**: thứ tự điều kiện là quy tắc. Kiểm SRM trước (dữ liệu hỏng thì không có kết luận), guardrail thứ
   hai, rồi `ci_high < mde` trước `ci_low > 0` để "có ý nghĩa nhưng nhỏ hơn mức đáng làm" ra `do_not_ship`.

## Kết quả trên bộ thật

| Kiểm tra / ước lượng | Kết quả |
| --- | --- |
| Người dùng | `ad` 564 577 (96.0000%), `psa` 23 524; mỗi `user_id` một dòng |
| SRM so với 96/4 | chi2 = 7e-8, p = 0.9998: tổng thể chia đúng (gần như chính xác tuyệt đối, dấu hiệu bộ dữ liệu đã được lấy mẫu lại theo tỉ lệ) |
| SRM nếu brief ghi 95/5 | chi2 = 1 238, p = 3e-271 |
| Cân bằng theo `most_ads_day` | chi2 = 235.6, 6 bậc tự do, p = 5e-48; tỉ lệ `psa` 3.50% (thứ Bảy) tới 4.71% (thứ Năm) |
| Cân bằng theo `most_ads_hour` | chi2 = 192.3, 23 bậc tự do, p = 1e-28 |
| Tỉ lệ chuyển đổi | `ad` 2.555%, `psa` 1.785% |
| Chênh lệch | **+0.769 điểm %** [0.595; 0.943], p = 1.7e-13 |
| Tương đối | **+43.1%** (khoảng xấp xỉ +33% tới +53% nếu chia CI cho tỉ lệ nhóm psa) |
| Chuyển đổi tăng thêm trong nhóm `ad` | khoảng **4 343** [3 360; 5 326] trên 14 423 chuyển đổi của nhóm |
| Quyết định (MDE giả định 0.5 điểm %) | `ship` |

Theo ngày, chênh lệch dương ở cả 7 ngày; thứ Năm (+0.14, CI [−0.31; +0.59]) và Chủ nhật (+0.40, CI [−0.11; +0.92])
có khoảng tin cậy chứa 0. Đừng đọc đây là "quảng cáo không hiệu quả thứ Năm": nhóm `psa` mỗi ngày chỉ khoảng 3 000
người, và với 7 phân khúc thì vài khoảng chứa 0 là chuyện bình thường.

**Mất cân bằng theo ngày**: `most_ads_day` được đo **sau** khi chia nhóm (ngày người dùng thấy nhiều quảng cáo
nhất). Nếu PSA và quảng cáo được hệ thống phân phối như nhau, phân phối ngày phải giống nhau giữa hai nhóm. Lệch rõ
nghĩa là hai nhóm được phục vụ khác nhau theo thời gian (ví dụ PSA hết lượt hiển thị vào cuối tuần), hoặc cách chia
nhóm thay đổi theo thời gian. Đây không phải lý do bỏ kết quả tổng (randomization ở cấp người dùng vẫn cho so sánh
tổng không chệch nếu chia đúng), nhưng là lý do (1) hỏi đội kỹ thuật cách chia nhóm và phân phối PSA, (2) không
đọc kết quả theo ngày như nhân quả, (3) ghi vào phần giới hạn.

**Correlation không phải nhân quả**: chuyển đổi tăng mạnh theo `total_ads` ở **cả hai** nhóm (`psa`: 0.28% ở 1-5
lần tới 11.9% ở hơn 100 lần; tương quan 0.18 trong nhóm psa). Người dùng nhiều thì vừa thấy nhiều vị trí quảng cáo
vừa có xu hướng mua; số quảng cáo đã thấy là kết quả của hành vi, không phải biến được chia ngẫu nhiên. So sánh
nhân quả hợp lệ duy nhất trong bộ này là `ad` với `psa`. Chênh lệch giữa hai nhóm lớn hơn ở phân khúc thấy nhiều
(+5.9 điểm ở 51-100 lần), gợi ý (không chứng minh) rằng tần suất có vai trò; muốn biết phải chạy thí nghiệm chia
ngẫu nhiên **tần suất**.

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `overall-lift` | b | 0.769 điểm %; +43.1% là lift tương đối (phương án d nhầm thành điểm %), 2.55% là tỉ lệ nhóm `ad` |
| `srm-reading` | c | Chênh 1 điểm % của 588 nghìn người là gần 5 900 người: chi2 = 1 238. Cỡ mẫu lớn làm SRM **nhạy hơn** |
| `day-balance` | a | 3.50% thứ Bảy, 4.71% thứ Năm |
| `day-imbalance-meaning` | d | Không bỏ cả thí nghiệm, cũng không bỏ qua; biến đo sau khi chia nhóm phản ánh cách hai nhóm được phục vụ |
| `decision` | a. ship | SRM đạt, `ci_high` 0.94 ≥ 0.5, `ci_low` 0.60 > 0 |
| `significant-but-small` | b | CI không chứa 0 (có ý nghĩa), nhưng cả khoảng nằm dưới 0.5 |
| `dose-causation` | c | Nhóm `psa` không thấy quảng cáo nào mà vẫn tăng từ 0.28% lên 11.9% theo `total_ads`: đó là hành vi người dùng, không phải quảng cáo |
| `incremental` | d. Khoảng 4 300 | 0.0077 × 564 577 = 4 343. 14 423 là tổng chuyển đổi nhóm ad, phần lớn sẽ xảy ra kể cả không có quảng cáo |

## Ba câu cho CMO (mẫu)

"Quảng cáo tăng tỉ lệ mua từ 1.79% lên 2.55% (+0.77 điểm %, khoảng tin cậy 0.60-0.94), tức khoảng 4 300 đơn tăng
thêm trong 565 nghìn người thấy quảng cáo; với điều kiện cách chia nhóm được xác nhận, đây là hiệu ứng thật, không phải ngẫu nhiên. Nên tiếp tục, với điều
kiện chi phí cho mỗi đơn tăng thêm (không phải mỗi đơn) thấp hơn biên lợi nhuận. Cần đội kỹ thuật kiểm vì sao tỉ lệ
nhóm đối chứng lệch theo ngày (3.5-4.7%) trước khi dùng kết quả để tối ưu lịch chạy quảng cáo."
