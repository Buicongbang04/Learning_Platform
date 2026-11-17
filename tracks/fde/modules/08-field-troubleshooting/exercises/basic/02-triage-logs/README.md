---
title: "Đọc 500 dòng log khách gửi trong 5 phút"
level: basic
services: []
files:
  - path: starter/triage_logs.py
    note: Bạn viết hàm triage
  - path: tests/logs
    note: Log thật của quillo 1.0.0 trong hai buổi có sự cố (output docker compose logs --no-color)
  - path: tests/expected
    note: Kết quả đúng cho hai log trên
  - path: tests/test_triage_logs.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/08-field-troubleshooting/exercises/basic/02-triage-logs -q
---

## Mục tiêu

Khách gửi lại một tệp log dài, lẫn lộn năm dịch vụ, có dòng JSON và dòng chữ thường, thứ tự không theo thời gian. Việc
đầu tiên của bạn không phải đọc từng dòng mà là trả lời ba câu: **lỗi gì, bao nhiêu lần, bắt đầu và kết thúc lúc nào**,
và đó là một đợt sự cố hay nhiều đợt khác nhau. Bài này viết công cụ nhỏ trả lời ba câu đó trên log thật của quillo.

## Đề bài

Viết `starter/triage_logs.py` (Python 3.12, chỉ thư viện chuẩn): `python triage_logs.py <tệp log>` in ra stdout một
JSON object, thoát `0`.

**Đầu vào** là output nguyên văn của `docker compose logs --no-color` trong thư mục cài quillo. Mỗi dòng dạng
`<dịch vụ>-<số> | <nội dung>` (số dấu cách trước `|` thay đổi; tên dịch vụ là phần trước `-<số>`). Dòng không có dạng đó
thì bỏ qua. Một dòng là **sự kiện** khi nội dung là JSON object có `ts` (dạng `2026-11-11T05:46:53+0000`), `level` và
`msg` là chuỗi; quillo ghi log như vậy, các trường khác (`path`, `status`, `error`…) tuỳ sự kiện. Mọi dòng có dạng trên mà
không phải sự kiện (log chữ của Postgres, llama.cpp, uvicorn, dòng JSON hỏng) là **dòng không đọc được** của dịch vụ đó.
Thứ tự dòng trong tệp **không** theo thời gian.

**Đầu ra** có đúng các khoá sau (thời điểm luôn ghi lại nguyên chuỗi `ts` của sự kiện tương ứng):

| Khoá | Nội dung |
| --- | --- |
| `services` | `{tên dịch vụ: {"events": số sự kiện, "unparsed": số dòng không đọc được}}` cho mọi dịch vụ xuất hiện |
| `window` | `{"first", "last"}`: `ts` sớm nhất và muộn nhất trong mọi sự kiện; không có sự kiện thì `null` |
| `groups` | Sự kiện có `level` là `WARNING`, `ERROR` hay `CRITICAL`, gom theo (dịch vụ, `level`, `msg`): mỗi nhóm `{"service", "level", "msg", "count", "first", "last"}` |
| `http_5xx` | Sự kiện `msg` là `"request"` có `status` (số nguyên) ≥ 500, gom theo (`path`, `status`): mỗi nhóm `{"path", "status", "count", "first", "last"}` |
| `incidents` | Các **đợt sự cố**: xếp mọi sự kiện thuộc `groups` hoặc `http_5xx` theo thời gian; một sự kiện cách sự kiện xấu liền trước **hơn 30 giây** thì mở đợt mới. Mỗi đợt `{"start", "end", "services", "events"}`: `ts` đầu, cuối, danh sách dịch vụ (xếp tăng dần, không lặp) và số sự kiện |

Thứ tự: `groups` xếp theo `first` (theo thời gian), cùng `first` thì theo (dịch vụ, `level`, `msg`) so chuỗi;
`http_5xx` theo `first` rồi (`path`, `status`); `services` theo tên. Hai log trong `tests/logs/` là log thật của quillo
1.0.0 trên VM `lab-open`, ghi ngày 2026-11-11 bằng `tests/capture_logs.py`: script dùng quillo như khách (thả tài liệu,
hỏi qua API) trong lúc dừng rồi bật lại từng dịch vụ hạ tầng; log còn giữ cả vài dòng của lần khởi động trước đó (lúc
dựng snapshot), như log thật của máy chạy lâu ngày.

## Tiêu chí đạt

- `test_recorded_logs` (2 log): output bằng đúng `tests/expected/<log>.json` ở cả năm khoá.
- `test_same_incident_other_day` (2 log): cùng log đó nhưng mọi `ts` bị dời một khoảng ngẫu nhiên (có thể qua ngày,
  qua năm), các dịch vụ bị trộn lại thứ tự như `docker compose logs` có thể in (giữ thứ tự trong từng dịch vụ), chèn thêm
  vài dòng JSON hỏng và dòng trống; output phải đúng như kết quả mong đợi dời cùng khoảng đó.
- Mỗi lần chạy ≤ 30 s.

## Gợi ý

### Gợi ý 1

Chạy `grep -c . tests/logs/*.log` rồi mở một tệp ra xem: dịch vụ nào ghi JSON, dịch vụ nào không, và các khối dòng của
từng dịch vụ nằm ở đâu trong tệp.

### Gợi ý 2

So thời điểm bằng giá trị thời gian đã phân tích, không bằng vị trí dòng trong tệp.

### Gợi ý 3

Đọc kết quả mong đợi của `lab-evening` cạnh log của nó: hai đợt trong `incidents` có cùng một nguyên nhân không? Khi
tóm tắt cho khách, bạn sẽ hỏi gì về khoảng lặng giữa chúng?
