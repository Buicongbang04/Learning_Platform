---
title: Client World Bank API cho slide chọn thị trường ASEAN - phân trang, retry, lỗi trong HTTP 200
level: intermediate
services: []
files:
  - path: starter/wb_client.ipynb
    note: 6 hàm TODO; cell explore gọi API thật (không cần key)
  - path: tests/test_wb_client.py
    note: Không sửa; dùng server giả httpx.MockTransport, không gọi mạng
run:
  - uv run jupyter lab tracks/data-analyst/modules/05-data-collection/exercises/intermediate/01-world-bank-api-client/starter/wb_client.ipynb
  - uv run pytest tracks/data-analyst/modules/05-data-collection/exercises/intermediate/01-world-bank-api-client -q
---

## Mục tiêu

Viết một client API nhỏ mà số trên slide có thể tin và lấy lại được: đi hết các trang và đối chiếu `total`, thử lại
đúng loại lỗi, nhận ra lỗi nằm trong HTTP 200, không để lộ key trong log; rồi biến JSON thành một bảng trả lời câu hỏi
"thị trường online nào lớn nhất ASEAN".

## Đề bài

[World Bank Indicators API v2](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392): miễn phí, không cần
key, dữ liệu CC BY 4.0. Ba chỉ số `SP.POP.TOTL`, `NY.GDP.PCAP.CD`, `IT.NET.USER.ZS` cho 10 nước ASEAN, 2015–2023.

Head of Expansion của một công ty TMĐT Việt Nam cần bảng cho slide chọn thị trường thứ hai. Mở
`starter/wb_client.ipynb`:

1. `get_json(client, path, params, max_retries, sleep)`: retry lỗi mạng, 429, 5xx với backoff `1, 2, 4…` giây hoặc
   đúng `Retry-After`; 4xx khác báo ngay; HTTP 200 có `message` trong body là lỗi.
2. `fetch_indicator(client, indicator, countries, start, end, per_page, sleep)`: đi hết `pages`, so với `total`.
3. `to_tidy(records)`: bảng `iso3, country, indicator, year, value`, bỏ nhóm nước, giữ `NaN`.
4. `online_population(tidy, year)`: mỗi nước một dòng, `online_population = population * internet_pct / 100`.
5. `redact(url)`: che giá trị `api_key`, `key`, `token` trong URL trước khi log.
6. Chạy các cell `explore` (cell explore cần mạng; test thì không): gọi API thật (11 request), lưu JSON thô kèm `fetched_at` và `lastupdated` vào
   `data/raw_api/world-bank-asean/` (thư mục nằm trong `.gitignore`), dựng bảng và biểu đồ. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy
   notebook.

## Tiêu chí đạt

- Test với server giả pass: backoff `[1, 7]` khi gặp 503 rồi 429 có `Retry-After: 7`; lỗi mạng được thử lại; 400 và
  lỗi trong body không thử lại; hết lượt thì `ApiError`; 7 bản ghi với `per_page=3` cần đúng 3 request; `total` lệch thì
  báo lỗi; nước thiếu tỉ lệ internet có `online_population` là `NaN` và đứng cuối.
- Trên API thật (lastupdated 2026-10-08): mỗi chỉ số 90 bản ghi; năm 2023 Indonesia có dân số online lớn nhất (khoảng
  195 triệu), tiếp theo Philippines (khoảng 90 triệu) và Việt Nam (khoảng 78 triệu).
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`get_json`: một vòng `for attempt in range(max_retries + 1)`. Bắt `httpx.TransportError` quanh `client.get`. Với
status trong `RETRY_STATUS`, nếu còn lượt thì `sleep(int(resp.headers.get("Retry-After", 2 ** attempt)))` rồi
`continue`. Kiểm body sau khi chắc status là 2xx.

### Gợi ý 2

`online_population`: lọc năm và ba chỉ số, `pivot_table(index="iso3", columns="indicator", values="value",
aggfunc="first", dropna=False)`, đổi tên cột theo `INDICATORS`, thêm cột `country`, tính cột mới, rồi
`sort_values(..., na_position="last")`.
