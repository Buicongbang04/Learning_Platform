---
title: Phát lại một sự cố - dựng hồ sơ incident từ log, metric và kênh chat
level: intermediate
services: []
files:
  - path: starter/incident.yaml
    note: Hồ sơ sự cố, điền mọi TODO
  - path: tests/fixtures/metrics.csv
    note: Metric theo phút của eta-service, chỉ đọc
  - path: tests/fixtures/deploys.log
    note: Lịch sử deploy, chỉ đọc
  - path: tests/fixtures/alerts.log
    note: Thông báo của Alertmanager, chỉ đọc
  - path: tests/fixtures/chat.log
    note: Kênh sự cố, chỉ đọc
  - path: tests/test_incident_record.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/intermediate/02-incident-command-replay -q
---

## Mục tiêu

Sau sự cố, incident commander phải trả lời bằng số: bắt đầu lúc nào, biết lúc nào, hết lúc nào, mất bao nhiêu, ai giữ vai trò
gì, và quyết định nào thật sự chấm dứt tác động. Bạn dựng hồ sơ đó từ bằng chứng thô, có nhiễu và có đường cụt, như ngoài đời.

## Đề bài

Chiều 2026-10-14, `eta-service` trả lỗi 5xx trên `/predict`. Bằng chứng ở `tests/fixtures/`: `metrics.csv` (mỗi phút: `minute`,
`requests`, `errors_5xx`, `p95_ms`, `model_version`), `deploys.log`, `alerts.log` (giờ UTC, cùng múi giờ với chat), `chat.log` (kênh sự cố,
mỗi người là một handle `@tên`). Có thông tin không liên quan trong cả bốn tệp.

Điền `starter/incident.yaml` (không còn chữ `TODO`) theo đúng định nghĩa sau. Test tính lại mọi giá trị đo được từ bốn tệp:

| Trường | Định nghĩa |
| --- | --- |
| `started_at` | Phút đầu tiên trong `metrics.csv` có tỉ lệ `errors_5xx / requests` **lớn hơn 2%** |
| `detected_at` | Thời điểm alert đầu tiên của `eta-service` chuyển sang `firing` trong `alerts.log` |
| `mitigated_at` | Phút đầu tiên mà từ đó **đến hết dữ liệu** tỉ lệ lỗi luôn **không quá 1%** |
| `time_to_detect_min`, `time_to_mitigate_min` | Số phút từ `started_at` tới `detected_at` và tới `mitigated_at` (số nguyên) |
| `impact.failed_requests` | Tổng `errors_5xx` từ `started_at` (gồm) tới `mitigated_at` (không gồm), số nguyên chính xác |
| `impact.budget_consumed_pct` | `failed_requests` chia budget 30 ngày, nhân 100. SLO khả dụng 99.5%, lưu lượng 30 ngày là 43 200 000 yêu cầu (sai số 0.05) |
| `severity` | `SEV1` nếu tiêu từ 10% budget trở lên hoặc có phút tỉ lệ lỗi từ 50% trở lên; `SEV2` nếu tiêu từ 2%; còn lại `SEV3` |
| `trigger` | `deploy_id` của thay đổi gây ra sự cố |
| `decision` | Hành động đã chấm dứt tác động, một trong `rollback`, `restart`, `scale-out`, `wait`, `disable-feature` |
| `roles` | Handle (không cần `@`) của người giữ `incident_commander`, `comms`, `ops` theo kênh chat; ba người khác nhau |
| `next_steps` | Ít nhất 3 việc tiếp theo, mỗi việc một chuỗi không rỗng (nội dung tự chấm theo `SOLUTION.md`) |

Thời điểm viết dạng `"HH:MM"` **trong ngoặc kép**: YAML 1.1 đọc `13:05` không có ngoặc thành số nguyên 785.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/intermediate/02-incident-command-replay -q` pass.
- Bạn chỉ ra được trong chat một giả thuyết sai và một hành động không có tác dụng, và vì sao đội vẫn đúng khi thử chúng theo thứ tự đó.
- Bạn giải thích được vì sao người đang debug không nên đồng thời làm incident commander.

## Gợi ý

### Gợi ý 1

Đọc `metrics.csv` bằng pandas hay `csv`, thêm cột tỉ lệ, rồi in các phút quanh lúc tỉ lệ đổi. Một phút lỗi cao đơn lẻ không phải sự cố
nếu nó không vượt ngưỡng định nghĩa.

### Gợi ý 2

Đặt bốn tệp cạnh nhau theo thời gian. Thay đổi nào xảy ra ngay trước khi lỗi bắt đầu, và hành động nào ngay trước khi lỗi hết? Một
sự kiện cùng giờ (bảo trì) không phải nguyên nhân nếu bằng chứng nói ngược lại.
