---
title: Point-in-time join bằng pd.merge_asof
level: basic
services: []
files:
  - path: starter/pit.py
    note: Hàm point_in_time_join cần viết
  - path: tests/test_pit.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/06-feature-stores/exercises/basic/01-point-in-time-join -q
---

## Mục tiêu

Tự viết phép nối point-in-time: gắn cho mỗi sự kiện giá trị feature mà hệ thống **đã biết** tại thời điểm sự kiện, không bao giờ
dùng giá trị về sau. Đây là phép nối mà `get_historical_features` của Feast làm hộ bạn; viết tay một lần để hiểu nó chặn lỗi gì.

## Đề bài

Trong `starter/pit.py` viết `point_in_time_join(events, features, key, event_ts="event_ts", feature_ts="feature_ts", tolerance=None)`.

- `events`: mỗi dòng một sự kiện, có cột khoá `key` và cột thời điểm `event_ts`.
- `features`: mỗi dòng một giá trị feature của một thực thể, có cột khoá `key`, cột `feature_ts` là thời điểm giá trị đó **bắt đầu
  khả dụng**, và các cột feature còn lại. Dữ liệu vào không cần đã sắp xếp.
- Với mỗi sự kiện, lấy dòng feature cùng khoá có `feature_ts` **lớn nhất không vượt quá** thời điểm sự kiện (bằng nhau thì
  vẫn lấy). Không có dòng nào thì các cột feature là `NaN`.
- `tolerance` (một `pd.Timedelta`, mặc định `None` là không giới hạn): dòng feature cũ hơn thời điểm sự kiện quá `tolerance`
  thì coi như không có. `pd.Timedelta(0)` nghĩa là chỉ nhận khớp chính xác.
- Kết quả giữ **đúng thứ tự dòng của `events`**, chỉ số `0..n-1`, đủ số dòng của `events`, các cột theo thứ tự: mọi cột của
  `events`, rồi các cột feature (theo thứ tự trong `features`), rồi cột `feature_timestamp` là `feature_ts` của dòng đã chọn
  (`NaT` khi không có). Cột `feature_ts` gốc không xuất hiện trong kết quả.
- Không sửa `events` và `features` truyền vào.
- Dùng `pd.merge_asof`; hai cột thời điểm cùng kiểu `datetime64`.

Test chạy phép nối trên bảng nhỏ có đáp án tay, rồi trên dữ liệu thật: tốc độ trung bình theo zone và giờ của một mẫu tháng 3/2019
(`mlopskit.real_month`), `feature_ts` là cuối giờ (giờ đó mới tính xong), sự kiện là các chuyến khác trong cùng tháng. Test
kiểm không có feature nào có `feature_timestamp` muộn hơn thời điểm sự kiện và kết quả khớp phép tìm vét cạn.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/06-feature-stores/exercises/basic/01-point-in-time-join -q` pass.
- Giải thích được bằng một câu vì sao `pd.merge(events, features, on="zone")` rồi lấy dòng mới nhất cho mỗi zone làm offline
  đẹp giả.

## Gợi ý

### Gợi ý 1

`merge_asof` đòi cả hai bảng **sắp theo cột thời điểm** và trả về theo thứ tự của bảng trái đã sắp. Bạn cần cách nhớ thứ tự gốc
của `events` để trả lại. `by=` lo việc khớp theo khoá.

### Gợi ý 2

Mặc định `direction="backward"` đã đúng ý; kiểm `allow_exact_matches` vì đề nói bằng nhau thì vẫn lấy. Để có cột
`feature_timestamp`, cột `feature_ts` phải còn lại sau phép nối: sao chép nó sang tên khác trước khi nối.
