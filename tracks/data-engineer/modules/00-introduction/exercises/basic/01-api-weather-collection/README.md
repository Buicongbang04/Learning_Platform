---
title: Thu thập từ API thật - thời tiết TP.HCM và Hà Nội 2023 (Open-Meteo)
level: basic
services: []
files:
  - path: starter/weather.ipynb
    note: 7 hàm TODO + 2 biểu đồ; cell explore gọi API thật
  - path: starter/report.md
    note: Báo cáo 4 mục, đang là TODO
  - path: tests/test_weather.py
    note: Không sửa; test không gọi mạng
run:
  - uv run pytest tracks/data-engineer/modules/00-introduction/exercises/basic/01-api-weather-collection -q
---

## Mục tiêu

Tự tay thu thập dữ liệu từ một **API công khai** theo cách một Data Engineer làm: ghim tham số để tái lập,
gọi có timeout và retry khi gặp 429/5xx, cache response thô trước khi parse, rồi biến JSON thành bảng
sạch và trả lời một câu hỏi thật: khí hậu hai đầu đất nước khác nhau tới mức nào?

## Đề bài

API [Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api) (miễn phí,
không cần key, CC BY 4.0). Mốc ghim: TP.HCM (10.82, 106.63) và Hà Nội (21.03, 105.85), từ 2023-01-01
tới 2023-12-31, biến theo ngày `temperature_2m_max/min/mean`, `precipitation_sum`, timezone
`Asia/Bangkok`, model `era5`.

Mở `starter/weather.ipynb`, làm lần lượt:

1. `build_params(lat, lon, start, end)`: dict tham số query, ghim timezone và model.
2. `fetch_json(get, url, params, max_retries=4, sleep=time.sleep)`: luôn có timeout; retry 429, 5xx và
   lỗi mạng với backoff 1, 2, 4... giây (hoặc đúng `Retry-After`); lỗi 4xx khác báo ngay; hết lượt thì
   `RuntimeError`.
3. `collect(get, raw_dir, ...)`: mỗi thành phố một tệp `data/raw/open-meteo/<city>_<start>_<end>.json`
   chứa **nguyên response**; có rồi thì không gọi lại; ghi qua tệp tạm.
4. `parse_daily(payload, city)` và `clean(df)`: bảng `city, date, tmax, tmin, tmean, precip_mm`; bỏ ngày
   toàn null, bỏ trùng `(city, date)`.
5. `insights(df)`: theo thành phố: tổng mưa, tỉ lệ mưa tháng 5–10, tháng nóng/lạnh nhất, biên độ nhiệt,
   ngày nóng nhất, số ngày ≥ 35 °C, số ngày mưa.
6. `write_clean(df, out_dir)`: ghi đè `data/clean/open-meteo/daily.parquet`.
7. Chạy cell `explore: thu thập` (2 request thật; không cần lệnh tải riêng, notebook chính là bộ thu thập),
   vẽ ít nhất 2 biểu đồ, viết `starter/report.md`.


## Tiêu chí đạt

- Test logic với `get` giả (không cần mạng) pass: tham số đúng, backoff `[1, 2, 4]`, tôn trọng `Retry-After`,
  không retry lỗi 400, lần chạy thứ hai không gọi API, không để lại tệp tạm.
- Trên dữ liệu đã thu thập: mỗi thành phố đủ 365 ngày; biên độ nhiệt TP.HCM ~3,3 °C, Hà Nội ~13,6 °C;
  tháng nóng nhất TP.HCM là tháng 4, Hà Nội tháng 7; hơn 80% lượng mưa rơi trong tháng 5–10.
- `write_clean` gọi hai lần vẫn đúng số dòng. Ít nhất 2 cell `explore` vẽ biểu đồ.
- `report.md` đủ 4 mục, không còn TODO, Insight có số.

## Gợi ý

### Gợi ý 1

Viết `fetch_json` thành một vòng `for attempt in range(max_retries + 1)`. Bắt `requests.RequestException`
cho lỗi mạng. Chỉ gọi `sleep` khi còn lượt thử. `int(resp.headers.get("Retry-After", 2 ** attempt))`.

### Gợi ý 2

Ghi cache: `tmp = raw_dir / f".{path.name}.tmp"`, `tmp.write_text(json.dumps(payload))`, `tmp.replace(path)`.
Biên độ nhiệt: `d.groupby(d["date"].dt.month)["tmean"].mean()`, lấy `max() - min()`.
