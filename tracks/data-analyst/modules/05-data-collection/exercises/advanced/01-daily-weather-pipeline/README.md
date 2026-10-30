---
title: Pipeline thu thập hằng ngày - Open-Meteo, dữ liệu thô có metadata, idempotent, run log, backfill
level: advanced
services: []
files:
  - path: starter/pipeline.py
    note: 4 hàm TODO; phần còn lại cho sẵn (schema, CLI)
  - path: starter/RUNBOOK.md
    note: Runbook 6 mục cho người vận hành
  - path: tests/test_pipeline.py
    note: Không sửa; dùng response thật đã lưu, không gọi mạng
run:
  - uv run pytest tracks/data-analyst/modules/05-data-collection/exercises/advanced/01-daily-weather-pipeline -q
  - uv run python tracks/data-analyst/modules/05-data-collection/exercises/advanced/01-daily-weather-pipeline/starter/pipeline.py --last 14
---

## Mục tiêu

Biến một notebook "chạy tay mỗi sáng" thành một job nhỏ chạy hằng ngày mà người khác tin được: lưu response thô kèm
metadata, nạp idempotent (chạy lại không nhân đôi, nhận số được sửa), atomic theo ngày, có run log và log, tìm và
backfill ngày thiếu; rồi viết runbook đủ để đồng nghiệp vận hành khi bạn nghỉ phép.

## Đề bài

Team vận hành chuỗi cửa hàng muốn ghép doanh số ngày với thời tiết ở TP.HCM, Hà Nội, Đà Nẵng. Nguồn:
[Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (không cần key, CC BY 4.0),
mỗi request một thành phố một ngày, ba biến `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, múi giờ
`Asia/Bangkok`. Bạn sở hữu job này cho tới khi bàn giao cho Data Engineer.

`starter/pipeline.py` cho sẵn hằng số, schema (`weather_daily` khoá `(city, date)`; `run_log`), `build_params`,
`http_fetch`, `connect` và CLI. Viết:

1. `save_raw(raw_dir, day, city, body, url, params, fetched_at)`: nguyên bytes vào `<day>/<city>.json`, metadata
   (`url`, `params`, `fetched_at`, `sha256`, `n_bytes`) vào `<day>/<city>.meta.json`, ghi qua tệp tạm + `os.replace`.
2. `parse_day(body, city, day)`: một dòng `{city, date, tmax, tmin, precip_mm}`; response lỗi hoặc thiếu ngày thì
   `ValueError`.
3. `run_day(day, fetch, raw_dir, db_path, cities, now)`: đặc tả trong docstring: run log `running` → `success`/`failed`,
   upsert chỉ khi mọi thành phố thành công, không ném lỗi ra ngoài, log INFO/ERROR.
4. `missing_days(db_path, start, end, cities)`: ngày chưa đủ mọi thành phố.
5. Viết `starter/RUNBOOK.md` đủ 6 mục theo thứ tự có sẵn (250–1 200 từ). Quyết định lịch chạy, lookback, cảnh báo,
   điều kiện bàn giao là phần chính được chấm.
6. Chạy thật 14 ngày gần nhất bằng lệnh `--last 14` ở mục `run` (tới hôm qua; muốn khoảng cố định thì dùng
   `--backfill START END`, ví dụ `--backfill 2026-10-01 2026-10-21`; cell/lệnh này cần mạng) (ghi vào `data/raw_api/weather-daily/` và `data/clean/weather.sqlite`, cả hai nằm trong `.gitignore`).

## Tiêu chí đạt

- Test trên response thật đã lưu pass: metadata đúng và không còn tệp tạm; chạy lại cùng ngày giữ 3 dòng và nhận giá
  trị đã sửa; một thành phố lỗi thì không ghi dòng nào, run log `failed`, log ERROR, hàm không ném lỗi; `missing_days`
  coi ngày thiếu một thành phố là ngày thiếu; RUNBOOK đủ mục, không còn TODO.
- Nội dung code và runbook chấm theo rubric trong `SOLUTION.md` (đạt từ 70/100).

## Gợi ý

### Gợi ý 1

Upsert trong SQLite: `INSERT INTO weather_daily (...) VALUES (...) ON CONFLICT (city, date) DO UPDATE SET tmax =
excluded.tmax, ...`. Dùng `with conn:` để `sqlite3` tự commit hoặc rollback cả khối; ghi dòng `running` trong một khối
riêng trước, để run bị kill giữa chừng vẫn để lại dấu vết.

### Gợi ý 2

Thu thập hết ba thành phố vào một list trước, rồi mới mở transaction ghi. Lỗi ở thành phố thứ ba thì chưa có gì được
ghi; tệp raw của hai thành phố đầu vẫn nằm đó và không sao: lớp raw là nhật ký "nguồn trả gì, lúc nào", không phải bảng
báo cáo.
