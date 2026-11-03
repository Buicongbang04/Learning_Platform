---
title: Giám sát khi nhãn về muộn bằng baseline cùng thứ và tỉ lệ fallback
level: basic
services: []
files:
  - path: starter/proxy.py
    note: 3 hàm TODO
  - path: tests/test_proxy.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/10-drift-incidents/exercises/basic/02-label-delay-proxy-monitor -q
---

## Mục tiêu

Khi nhãn thật về sau nhiều ngày, bạn vẫn phải phát hiện sớm. Bài này dựng ba mảnh nhỏ: MAE chỉ trên phần đã có nhãn, baseline theo mùa vụ tuần, và cảnh báo
bằng hai proxy (phân phối dự đoán, tỉ lệ fallback) mà không báo động giả vào cuối tuần.

## Đề bài

Điền 3 hàm trong `starter/proxy.py`.

- `labeled_mae(df, now, delay_days)`: `df` có cột `ts` (thời điểm dự đoán, datetime), `pred`, `label` (giá trị thật cuối cùng, dù thực tế nó chưa về). Nhãn của một dòng "đã về" khi
  `ts + delay_days <= now` (so sánh `<=`). Trả MAE (`|pred - label|` trung bình) trên các dòng đã về, hoặc `None` nếu chưa có dòng nào. Đây là cách tránh nhìn trộm nhãn tương lai khi mô phỏng.
- `seasonal_baseline(daily, day, weeks=4)`: `daily` là Series chỉ mục ngày (Timestamp). Lấy giá trị của các ngày `day - 7k` với $$k = 1..weeks$$, **bỏ ngày không có trong chỉ mục**, trả
  `(mean, std)` với `std` là độ lệch chuẩn mẫu (`ddof=1`). Dưới 2 giá trị thì `raise ValueError`.
- `proxy_alerts(pred_mean, fallback_rate, day, z_limit=3.0, fallback_limit=0.02, weeks=4)`: hai Series theo ngày. Trả danh sách lý do, theo đúng thứ tự:
  1. `"pred_mean"` nếu $$|\text{pred\_mean}[day] - \text{mean}| / \text{std} > z\_limit$$ với `mean`, `std` từ `seasonal_baseline(pred_mean, day, weeks)`;
  2. `"fallback"` nếu `fallback_rate[day]` lớn hơn trung bình baseline của `fallback_rate` (cùng `weeks`) cộng `fallback_limit` (chênh tuyệt đối, vd. 0.02 là 2 điểm phần trăm).
  Không lý do nào thì trả danh sách rỗng.

Dữ liệu test là chuỗi 70 ngày có chu kỳ tuần (cuối tuần dự đoán trung bình thấp hơn rõ), sinh trong test.

## Tiêu chí đạt

- `labeled_mae` đúng ở các ranh giới (`<=`, chưa có nhãn nào trả `None`).
- `seasonal_baseline` dùng đúng các ngày cùng thứ, bỏ ngày thiếu, báo lỗi khi dưới 2 điểm.
- Cuối tuần giảm theo mùa vụ không bị báo động; một so sánh ngây thơ "hôm nay với hôm qua" sẽ báo (test chứng minh khoảng chênh lớn hơn 3).
- Dự đoán lệch mạnh chỉ báo `["pred_mean"]`, fallback tăng chỉ báo `["fallback"]`, cả hai thì đúng thứ tự.

## Gợi ý

### Gợi ý 1

`[day - pd.Timedelta(days=7 * k) for k in range(1, weeks + 1)]` rồi lọc bằng `in daily.index`. `np.std(values, ddof=1)` cho độ lệch chuẩn mẫu.

### Gợi ý 2

Tách phần tính z-score và phần so fallback thành hai bước riêng rồi nối vào cùng một danh sách `reasons`; thứ tự thêm quyết định thứ tự trả về.
