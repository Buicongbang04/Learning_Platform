# Lời giải: cảnh báo KPI theo ngày với ngưỡng có mùa vụ

## Cách làm

- **`seasonal_baseline`**: ghép `y.shift(7k)` với `k = 1..weeks` thành các cột rồi lấy median theo dòng với
  `skipna=False`, để ngày chưa đủ `weeks` tuần lịch sử là `NaN` (baseline từ 3 tuần thay vì 4 sẽ âm thầm đổi nghĩa).
  Median thay cho mean: ngày 29/10/2012 (22 lượt, chỉ 1 giờ dữ liệu) nằm trong lịch sử của bốn thứ Hai kế tiếp; mean
  sẽ kéo baseline của cả bốn ngày xuống khoảng 25%, median gần như không đổi.
- **`robust_score`**: `ratio = ln(y / baseline)`. Log làm cú giảm một nửa và cú tăng gấp đôi có cùng độ lớn, và
  biến "lệch bao nhiêu phần trăm" thành phép trừ. Thang đo là `1.4826 × MAD` của `ratio.shift(1)` trên cửa sổ 56
  ngày (`np.nanmedian` để bỏ các ngày chưa có baseline), nên ngày t không tham gia tính thang đo của chính nó.
- **`alert_table`**: lọc `score.abs() > threshold` (so sánh với `NaN` cho `False`), thêm `direction` theo dấu.
- **`alert_episodes`**: `(dates.diff() != 1 ngày).cumsum()` đánh số đợt; mỗi đợt lấy `start`, `end`, số ngày và
  score có trị tuyệt đối lớn nhất (giữ dấu).
- **`hour_coverage`**: `hour.groupby("dteday")["hr"].nunique()`. Đây là bước kiểm độ phủ phải làm **trước** khi
  diễn giải bất kỳ cực trị nào: `day.csv` là tổng của `hour.csv`, và một ngày chỉ có vài giờ trong bản ghi sẽ trông
  như một cú sụt cầu.
- **`triage`**: `np.select` với điều kiện thiếu giờ đứng đầu (ngày không có trong `coverage` tính là 0 giờ), rồi lễ,
  rồi thời tiết, mặc định `investigate`.

## Kết quả trên bộ thật

| Quy tắc | Số ngày báo | Ghi chú |
| --- | --- | --- |
| Cố định `cnt < 2 000` | 98 | 72 ngày vào tháng 1–3 (34 + 26 + 12), 12 ngày tháng 12; tháng 5–7 không báo ngày nào |
| Giảm > 30% so với hôm qua | 65 | Ngày sau ngày bất thường cũng có thể bị báo hoặc bị che |
| Mùa vụ, ngưỡng 3 / 3.5 / 4 / 5 | 58 / 45 / 39 / 25 | Ngưỡng 4: 36 drop, 3 spike, 26 đợt |

- Score có từ 26/02/2011 (4 tuần cho baseline + 4 tuần cho thang đo), 675 ngày.
- **Độ phủ**: 655 ngày đủ 24 giờ, 62 ngày 23 giờ (thường thiếu một giờ đêm không ai thuê), 8 ngày dưới 20 giờ. Ngày
  29/10/2012 chỉ có **1 giờ** (giờ 0, 22 lượt), 30/10/2012 có **11 giờ** (1 096 lượt); 26-28/10 và 31/10 đều đủ 24
  giờ. Bão Sandy có thật, nhưng bản ghi không cho biết các giờ còn thiếu là hệ thống đóng hay mất dữ liệu, nên con số
  22 lượt **không đo cầu**. Score −57.9 (29/10) và −18.9 (30/10) giữ nguyên trong test nhưng là **artifact của dữ liệu
  thiếu giờ**, không phải hai cú sụt cầu lớn nhất. 27/08/2011 (bão Irene, 18 giờ, 1 115 lượt, −9.7) cũng thiếu giờ.
- Cảnh báo lớn nhất trên ngày đủ giờ: 26/12/2012 (441 lượt, `weathersit` 3, 24 giờ) −13.0; tiếp theo 29/10/2011
  (bão tuyết, 627 lượt) −9.2.
- `triage` không kiểm độ phủ: 25 `investigate`, 11 `bad_weather`, 3 `holiday`. Có kiểm độ phủ: 23 `investigate`, 10
  `bad_weather`, 3 `partial_day` (27/08/2011, 29/10/2012, 30/10/2012), 3 `holiday`. Nhiều ngày `investigate` vẫn có lý
  do dễ đoán:
  Giáng sinh rơi vào Chủ nhật (25/12/2011 có `holiday = 0`, nghỉ bù 26/12 mới có `holiday = 1`), 24/12, 27-29/12,
  nắng nóng kỷ lục 22-23/07/2011 (`temp` chuẩn hoá 0.85), cuối tuần Lễ Tạ ơn
  24-25/11/2012. Ba spike tháng 9/2012 là ngày đẹp trời trong giai đoạn tăng trưởng mạnh nhất.

## Đáp án trắc nghiệm

- `fixed-threshold` **b**: 98 ngày, 72 ngày rơi vào tháng 1–3. Ngưỡng cố định đo mùa, không đo bất thường; mùa
  hè một ngày mất nửa lượt thuê (ví dụ 07/10/2012: 3 510 so với baseline 7 620) không bị báo.
- `seasonal-count` **a**: 39 ngày, 26 đợt. 58 là số ngày ở ngưỡng 3; 65 là quy tắc so với hôm qua; 25 là số ngày
  ở ngưỡng 5.
- `worst-day` **c**: `hour.csv` chỉ có 1 giờ cho ngày 29/10/2012. Cảnh báo bắn vì dữ liệu thiếu, nên tin nhắn phải
  nói "dữ liệu ngày 29/10 chỉ có 1 giờ, đang kiểm nguồn" thay vì "cầu giảm 99%". Bão Sandy có thật và có thể hệ
  thống đã đóng, nhưng dữ liệu không cho phân biệt hai khả năng đó. Xoá ngày (d) làm mất dấu vết; bỏ qua (b) thì lần
  sau pipeline hỏng cũng bị bỏ qua.
- `investigate-share` **b**: 23 ngày khi có kiểm độ phủ; 10 là `bad_weather`, 3 là `partial_day`, 3 là `holiday`.
  25 (d) là số `investigate` khi chạy `triage` không có `coverage`: khi kiểm độ phủ, 30/10/2012 và 27/08/2011 chuyển
  từ `investigate` sang `partial_day`, còn 29/10/2012 chuyển từ `bad_weather` sang `partial_day`.
- `christmas-2011` **b**: cờ `holiday` theo lịch nghỉ liên bang; Giáng sinh 2011 rơi vào Chủ nhật nên ngày nghỉ
  chính thức là thứ Hai 26/12. Bài học: cờ lễ trong dữ liệu không phải "ngày người dùng nghỉ"; bảng lịch cho
  cảnh báo nên có cả ngày lễ thật và các ngày quanh lễ.
- `past-only-scale` **d**: một cú rơi cực lớn trong cửa sổ làm MAD tăng, score của chính nó bị chia cho một số lớn
  hơn. MAD vẫn tính được với ngày t (b sai); tốc độ không phải lý do (a).
- `day-over-day` **a**: so với hôm qua bỏ qua chu kỳ tuần và dùng một ngày có thể chính là ngoại lệ làm mốc:
  sau ngày mưa 22/04/2012 (1 027 lượt), thứ Hai 23/04 chỉ có 3 214 lượt, khoảng một nửa thứ Hai tuần trước (6 370),
  nhưng "tăng gấp 3" so với hôm qua nên không bị báo. Tăng ngưỡng (b) chỉ bớt số lượng chứ không sửa lỗi.
- `spikes-sep-2012` **c**: baseline là median 4 tuần trước nên trễ so với xu hướng tăng; spike là tin tốt, không
  cần ai hành động lúc 7 giờ sáng. Thực tế thường gửi drop ngay, gom spike vào báo cáo tuần, hoặc dùng ngưỡng
  khác nhau cho hai chiều.

## Lỗi hay gặp

- Dùng `skipna=True` khi tính baseline: những ngày đầu có baseline từ 1-2 tuần, rất nhiễu.
- Tính MAD trên cả ngày t (quên `shift(1)`), làm các cú rơi lớn nhỏ đi.
- Dùng `y - baseline` thay cho log: cùng −1 000 lượt là bình thường vào tháng 7 nhưng là thảm hoạ vào tháng 1.
- Gửi một tin cho mỗi ngày của một đợt bão hai ngày: người nhận học cách bỏ qua tin nhắn.
- Diễn giải cực trị trước khi kiểm độ phủ: báo "bão làm cầu giảm 99%" trong khi ngày đó chỉ có 1 giờ dữ liệu.
