# Hướng làm: pipeline thu thập hằng ngày

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết bốn hàm, một runbook mẫu rút gọn, các quyết định cần
cân nhắc và rubric.

## Bốn hàm

- `save_raw`: tạo `raw_dir/<day>/`; với từng tệp (body, metadata) dùng `tempfile.mkstemp(dir=folder)` rồi
  `os.replace(tmp, đích)`. `os.replace` là thao tác đổi tên nguyên tử trên cùng ổ đĩa: người đọc chỉ thấy tệp cũ hoặc
  tệp mới, không bao giờ thấy tệp ghi dở. `sha256` của body cho biết hai lần tải có khác nhau không mà không cần mở tệp.
- `parse_day`: `json.loads`, kiểm `payload.get("error")` (Open-Meteo trả HTTP 400 kèm `{"error": true, "reason":
  ...}`; khi body được lưu lại và parse sau, chính body phải báo được lỗi), tìm `day` trong `daily.time` thay vì lấy
  phần tử đầu (một response nhiều ngày vẫn đúng).
- `run_day`: ba khối. (1) `with conn:` ghi `run_log` trạng thái `running`, lấy `run_id`. (2) Vòng qua thành phố: fetch →
  `save_raw` → `parse_day`, gom vào list; chưa ghi gì vào bảng. (3) `with conn:` upsert mọi dòng + cập nhật run log
  `success`. Mọi exception ở (2) hoặc (3) bắt bằng `except Exception`, cập nhật run log `failed` kèm `str(exc)[:500]`,
  `logger.error(...)`, trả dict. Không ném lỗi để vòng backfill nhiều ngày chạy tiếp; mã thoát của CLI (1 khi có ngày
  lỗi) báo cho scheduler.
- `missing_days`: một câu `GROUP BY date` đếm `COUNT(DISTINCT city)`, so với danh sách mọi ngày trong khoảng sinh bằng
  `date.fromisoformat` + `timedelta`. Ngày không có dòng nào không xuất hiện trong kết quả SQL, nên phải sinh lịch ở
  Python.

Bản tham chiếu (không commit) chạy được với API thật: `--backfill 2026-10-18 2026-10-21` ghi 12 dòng, 4 dòng `run_log`
`success`; chạy lại `--day 2026-10-21` giữ 12 dòng, thêm 1 dòng run log.

## Runbook mẫu (rút gọn)

- **Mục đích**: `weather_daily` cho dashboard doanh số theo thời tiết của team vận hành; cần số của hôm qua (D-1) trước 8h sáng ngày D.
- **Lịch**: 6h sáng hằng ngày, lấy lại 7 ngày gần nhất (dữ liệu gần đây được nguồn sửa); upsert nên lấy lại không nhân đôi.
- **Chạy lại / backfill**: `--day`, `--last 14` (14 ngày gần nhất), `--backfill START END`; an toàn vì transaction theo ngày và upsert theo khoá.
- **Giám sát**: run `failed` chưa chạy lại thành công, `missing_days` 14 ngày gần nhất khác rỗng, run `running` quá 30
  phút, giá trị ngoài khoảng hợp lý; ai nhận, ai dự phòng.
- **Raw và metadata**: lưu ở đâu, giữ bao lâu, dùng sha256 + `fetched_at` để trả lời "vì sao số đổi", parse lại từ raw.
- **Giới hạn và bàn giao**: giá trị ô lưới (toạ độ trả về lệch toạ độ yêu cầu vài km), không phải trạm đo; gói miễn
  phí cho mục đích phi thương mại; SQLite một người ghi; bàn giao DE khi thêm nguồn, nhiều dashboard phụ thuộc, hoặc cần
  scheduler chung.

## Các quyết định cần cân nhắc

- **Ranh giới idempotent**: theo ngày (xoá-ghi hoặc upsert theo `(city, date)`). Upsert giữ được dòng của ngày khi lần
  chạy sau lấy ít thành phố hơn; xoá-ghi đơn giản hơn khi một ngày luôn lấy đủ.
- **All-or-nothing theo ngày** hay từng thành phố: bài chọn theo ngày để dashboard không bao giờ thấy ngày "một nửa";
  đổi lại một thành phố lỗi làm cả ngày chờ. Ghi rõ lựa chọn trong runbook.
- **Lookback**: nguồn sửa số gần đây, nên chỉ chạy ngày D-1 sẽ giữ mãi bản sơ bộ. Lookback 7 ngày nhân 7 số request; với
  3 thành phố vẫn nhỏ, với 300 thành phố thì phải dùng một request nhiều ngày.
- **Lỗi không ném ra ngoài, nhưng không im lặng**: run log + log ERROR + mã thoát khác 0.
- **Raw bất biến, bảng có thể dựng lại**: bảng `weather_daily` dựng lại được từ `data/raw_api/weather-daily/` mà không gọi API.
- **Khi nào không còn là việc của DA**: lịch chung, retry tập trung, nhiều nguồn, SLA cho nhiều team.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Dữ liệu thô và metadata | 15 | Raw nguyên bytes, metadata đủ khoá, ghi atomic, không tệp tạm còn sót |
| Idempotent và nhận số sửa | 20 | Chạy lại cùng ngày không nhân đôi, giá trị và `loaded_at` được cập nhật |
| Atomic và xử lý lỗi | 20 | Lỗi một thành phố không ghi dòng nào, run log `failed` có lỗi, hàm không ném, CLI trả mã khác 0 |
| Log và backfill | 10 | Log INFO/ERROR có ngày và trạng thái; `missing_days` đúng với ngày thiếu một phần |
| Runbook: lịch, lookback, chạy lại | 15 | Nêu giờ chạy, ngày dữ liệu, lookback có lý do, lệnh chạy lại và vì sao an toàn |
| Runbook: giám sát, giới hạn, bàn giao | 15 | Có tín hiệu cảnh báo cụ thể và người nhận; nêu giới hạn nguồn (ô lưới, sửa số, điều khoản) và điều kiện bàn giao DE |
| Văn phong | 5 | Đồng nghiệp đọc 5 phút là vận hành được, không mô tả lại code |

Từ 70 điểm trở lên là job đủ để bàn giao cho đồng nghiệp vận hành.
