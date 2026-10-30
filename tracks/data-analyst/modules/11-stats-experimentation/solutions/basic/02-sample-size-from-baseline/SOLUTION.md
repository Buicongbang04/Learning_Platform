# Lời giải: sample size và thời lượng từ baseline thật

## Cách làm

1. **`repeat_rate`**: ngày mua đầu = `min(invoice_date)` theo khách. Khách đủ điều kiện khi ngày đầu
   `>= cohort_start` và ngày đầu + cửa sổ `<= data_end`. Ghép ngày đầu vào bảng hoá đơn, lọc hoá đơn có giờ
   **lớn hơn** ngày đầu và trong cửa sổ, lấy tập khách duy nhất, rồi `eligible.index.isin(...)`. Hai quyết định
   quan trọng:
   - **Cắt phải (right censoring)**: khách mua đầu ngày 1/12/2011 chưa có 60 ngày để quay lại. Giữ họ trong mẫu
     số là đếm họ như "không quay lại", kéo baseline xuống.
   - **Cắt trái**: dữ liệu bắt đầu 1/12/2009, nên "khách mới" tháng 12/2009 gồm cả khách cũ đã mua trước đó.
     Cohort bắt đầu từ 2010-01-01 giảm (không loại hết) lỗi này.
   - Hoá đơn khác nhưng **cùng giờ** với đơn đầu (khách tách đơn) không phải là quay lại; điều kiện `>`
     chứ không `>=`.
2. **`weekly_new_customers`**: ngày đầu trong `[start, end)`, `to_period("W-SUN")` (tuần thứ Hai-Chủ nhật),
   `value_counts().sort_index()`.
3. **`sample_size_per_arm`**: công thức hai tỉ lệ (phương sai gộp dưới H0, phương sai riêng dưới H1), làm tròn
   lên. Kết quả lệch dưới 1% so với `NormalIndPower` của `statsmodels` (dùng Cohen's h, biến đổi arcsine).
4. **`weeks_needed`**: `ceil(n_per_arm * arms / (weekly * share))`, không ít hơn 2 tuần để có trọn hai chu kỳ
   ngày trong tuần.
5. **`mde_for_weeks`**: số người mỗi nhóm `floor(weeks * weekly * share / arms)`; cỡ mẫu giảm đơn điệu khi MDE
   tăng, nên tìm nhị phân MDE nhỏ nhất thoả.

## Số liệu trên bộ thật

| Số liệu | Giá trị |
| --- | --- |
| Hoá đơn hợp lệ có mã khách / số khách | 36 969 / 5 878 |
| Quay lại trong 30 / 60 / 90 ngày | 21.1% (4 762 khách) / **35.2%** (4 563) / 43.9% (4 326) |
| Khách mới mỗi tuần, 47 tuần năm 2011 | 1 488 khách, TB **31.7**, trung vị 29, thấp nhất 12, cao nhất 67 |

Baseline 35.2%, 31.7 khách mới mỗi tuần, alpha 0.05 hai phía, power 0.8:

| MDE tuyệt đối | Tương đối | Khách mỗi nhóm | Số tuần gom khách |
| --- | --- | --- | --- |
| 2 điểm % | +5.7% | 9 063 | 573 |
| 3 điểm % | +8.5% | 4 051 | 256 |
| 5 điểm % | +14.2% | 1 474 | **94** |
| 10 điểm % | +28.4% | 377 | 24 |

Ngược lại, chạy 4 tuần chỉ phát hiện được **+24.7 điểm %** (35% → 60%), 12 tuần +14.2 điểm, 26 tuần +9.6
điểm, 52 tuần +6.7 điểm. Lưu lượng cũng không đều: tháng 9-11 nhiều khách mới hơn (12 tuần cuối TB 47/tuần),
nên kế hoạch dựa trên trung bình cả năm là ước lượng thận trọng; dùng trung bình mùa cao điểm thì phải nói rõ.

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `baseline-60` | b. 35.2% | 21.1% là cửa sổ 30 ngày, 43.9% là 90 ngày |
| `weekly-traffic` | b. Khoảng 32 | 1 488 / 47 = 31.7; 12 và 67 là tuần thấp nhất, cao nhất |
| `weeks-5pp` | c. 94 tuần | 1 474 × 2 / 31.7 = 93.1, làm tròn lên 94. 573 tuần là MDE 2 điểm |
| `mde-4-weeks` | d. 25 điểm % | 4 tuần × 31.7 / 2 = 63 khách mỗi nhóm, chỉ đủ thấy +24.7 điểm |
| `censoring` | a | Khách chưa đủ cửa sổ chưa có cơ hội quay lại; tính họ là "không quay lại" làm baseline thấp giả tạo |
| `readout-timing` | c | Khách vào tuần thứ 12 cần thêm 60 ngày để đo metric, nên kết quả có sau khoảng 12 tuần + 60 ngày (gần 5 tháng). Đây là lý do metric có cửa sổ dài làm thí nghiệm chậm |
| `recommendation` | d | Nói thẳng con số: 4 tuần chỉ thấy hiệu ứng khoảng 25 điểm, không thực tế cho một email. Hạ alpha làm thí nghiệm **kém** nhạy hơn; nhìn p-value hằng ngày và dừng sớm là peeking, tăng false positive |
| `mde-scaling` | b. 4 lần | Cỡ mẫu tỉ lệ với 1/MDE²: giảm MDE một nửa thì cỡ mẫu gấp khoảng 4 (1 474 → 5 817 ở baseline này) |

## Trả lời trưởng nhóm CRM (mẫu)

"Chạy 4 tuần thì không biết được: mỗi tuần chỉ có khoảng 32 khách mới, 4 tuần chỉ phát hiện được nếu email
kéo tỉ lệ mua lại 60 ngày từ 35% lên khoảng 60%, mức không thực tế. Muốn thấy +5 điểm phải gom khách gần 2 năm.
Đề xuất: (1) thử trên **mọi khách đang hoạt động** (vài nghìn người một lần) với metric mua trong 30 ngày, hoặc
(2) gửi email cho tất cả khách mới nhưng giữ một nhóm holdout 10-20% trong 6-12 tháng để đo dần, chấp nhận chỉ
thấy hiệu ứng lớn."

## Sai lầm hay gặp

- Tính baseline trên mọi khách, kể cả khách mua tuần trước: baseline thấp giả tạo, cỡ mẫu sai.
- Tính thời lượng = thời gian gom khách, quên cửa sổ đo của metric.
- Dùng MDE tương đối (+5%) và tuyệt đối (+5 điểm) lẫn lộn: +5% của 35.2% chỉ là +1.8 điểm, cần hơn 11 nghìn
  khách mỗi nhóm.
