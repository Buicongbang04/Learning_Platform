---
title: ML hay bảng trung bình? Đánh giá lời chào model dự báo nhu cầu thuê xe theo giờ
level: advanced
services: []
files:
  - path: starter/bike_demand.ipynb
    note: 3 hàm TODO + phân tích tự do (dữ liệu có sẵn lúc dự báo, sai số ở đâu)
  - path: starter/MEMO.md
    note: Memo cho Operations Manager - trả lời ngắn, so sánh, dữ liệu lúc dự báo, rủi ro, đề xuất
  - path: tests/test_bike_demand.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/advanced/02-bike-ml-or-baseline/starter/bike_demand.ipynb
  - uv run pytest tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/advanced/02-bike-ml-or-baseline -q
---

## Mục tiêu

Quyết định có đáng mua một model ML không bằng cách so nó với baseline đang dùng theo đúng cách dự báo sẽ được dùng: chia
theo thời gian, chỉ dùng dữ liệu có sẵn lúc dự báo, tìm sai số nằm ở đâu, và viết khuyến nghị kèm điều kiện kiểm chứng.

## Đề bài

Operations Manager của hệ thống xe đạp công cộng lên lịch xe tải điều phối theo dự báo lượt thuê từng giờ của ngày mai,
hiện bằng một bảng trung bình theo (ngày làm việc, giờ). Một vendor chào model ML "giảm sai số một nửa". Dữ liệu: bộ
`bike-sharing-uci`, `hour.csv` (CC BY 4.0). Học trên dữ liệu trước 01/10/2012, đo trên 01/10–31/12/2012. Mở
`starter/bike_demand.ipynb`:

1. `time_split(hour, cutoff)`: `train` trước mốc, `test` từ mốc; `ValueError` khi một phần rỗng.
2. `profile_baseline(train, test, weeks=None)`: mean `cnt` theo (`workingday`, `hr`) của train (hoặc `weeks` tuần cuối),
   cặp thiếu dùng mean chung.
3. `mae(y_true, y_pred)`: `ValueError` khi khác độ dài, rỗng hoặc có NaN.
4. Phân tích tự do: model của vendor (dựng sẵn, gradient boosting) với và không có thời tiết; thời tiết **đo thực tế** so
   với thứ có sẵn lúc lên lịch; sai số theo tháng, giờ, thời tiết; ngày thiếu dữ liệu; cách cải tiến baseline.
5. Viết `starter/MEMO.md` theo khung: 200-600 từ, dòng đầu là headline có con số, đủ năm mục.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: chia đúng mốc và giữ index, baseline đúng cặp, đúng cửa sổ `weeks`, cặp thiếu dùng mean
  chung, MAE kiểm đầu vào.
- Trên bộ thật: train 15 211 giờ, test 2 168 giờ; MAE baseline 79.95 (toàn bộ train) và 94.13 (8 tuần cuối).
- `MEMO.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`profile.reindex(pd.MultiIndex.from_frame(test[["workingday", "hr"]]))` tra bảng trung bình cho từng dòng test mà không
làm đổi thứ tự; nhớ đặt lại index bằng `test.index`. Cửa sổ `weeks` lấy theo ngày cuối của train, không theo mốc chia.

### Gợi ý 2

Để giả lập "chỉ có dự báo thời tiết", một cách đơn giản trên dữ liệu thật là dùng thời tiết của cùng giờ ngày hôm trước
(dịch 24 giờ theo `dteday + hr`, không theo số dòng, vì có giờ bị thiếu). Đó là cận dưới của chất lượng dự báo; dự báo
thời tiết thật tốt hơn. Tại sao baseline 8 tuần cuối lại tệ hơn baseline toàn bộ train? Nhìn mùa của 8 tuần đó.
