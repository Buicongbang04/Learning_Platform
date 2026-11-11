---
title: "Acceptance test chạy cùng khách: health, p95, trích dẫn, ACL"
level: intermediate
services: []
files:
  - path: starter/acceptance.py
    note: Bạn viết
  - path: tests/test_acceptance.py
    note: Không sửa; chạy thẳng tệp này để dựng quillo có SSO + ACL và một cấu hình mẫu
run:
  - nice -n 15 uv run python tracks/fde/product/release.py build --version 1.0.0 --out tracks/fde/product/dist
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - nice -n 15 uv run python -m fdekit derive 07-customer-integration-quillo
  - docker pull quay.io/keycloak/keycloak:26.8.1-1@sha256:a78d6b79572168cb25886b80a8b5b8d4ed4390743e3eecb810538683e209dd6b
  - uv run pytest tracks/fde/modules/09-production-trust/exercises/intermediate/02-acceptance -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Hợp đồng với công ty luật ghi: "hệ thống được nghiệm thu khi vượt qua bộ acceptance test thống nhất giữa hai bên". Bộ đó
chạy ở buổi nghiệm thu, chạy lại sau mỗi lần nâng cấp, và là thứ IT của khách tự chạy khi nghi ngờ hệ thống. Nó phải nói
**đúng mục nào hỏng**: một bộ test chỉ in "FAIL" khiến mọi cuộc gọi hỗ trợ bắt đầu lại từ đầu, một bộ test báo PASS khi
ACL sai là một bộ test nguy hiểm.

## Đề bài

Viết `starter/acceptance.py` (Python 3.12; được dùng `requests`):
`python acceptance.py --config <cfg.json> --out <report.json>`. Script ghi `report.json`, in mỗi mục một dòng ra stdout,
thoát `0` khi mọi mục PASS, `1` khi có mục FAIL.

**Cấu hình** (do test viết; khách và bạn thống nhất trước buổi nghiệm thu):

```json
{
  "url": "http://127.0.0.1:18080",
  "admin_token": "…",
  "top_k": 2,
  "latency_samples": 4,
  "latency_question": "…",
  "p95_max_seconds": 3.2,
  "questions": [{"question": "…", "expect_folder": "legal/"}],
  "users": [{"name": "an", "token": "<access token SSO>", "folders": ["legal/"], "probe": "<câu hỏi về tài liệu ngoài quyền>"}]
}
```

Mọi `/api/ask` gửi `{"question", "top_k"}` với `top_k` của cấu hình. **Bốn mục**, quy tắc PASS:

| `id` | PASS khi |
| --- | --- |
| `health` | `GET /healthz` trả 200, `status` là `ok` và mọi giá trị trong `checks` là `true`. Khi FAIL, `detail` phải nêu tên các check bị `false` |
| `latency` | gửi đúng `latency_samples` lần `latency_question` bằng `admin_token`, lần nào cũng 200, và p95 thời gian trả lời (xếp tăng dần, lấy phần tử thứ `ceil(0.95 × n)`, đếm từ 1) ≤ `p95_max_seconds` |
| `citations` | với mỗi phần tử của `questions` (hỏi bằng `admin_token`): trả 200 và có ít nhất một trích dẫn thuộc tài liệu có đường dẫn (`filename` trong `GET /api/documents`) bắt đầu bằng `expect_folder` |
| `acl` | với mỗi người trong `users`: `GET /api/documents` bằng token của họ trả 200, không rỗng, mọi tài liệu có đường dẫn bắt đầu bằng một trong `folders`; và hỏi `probe` bằng token đó trả 200 với mọi trích dẫn thuộc danh sách tài liệu họ vừa thấy |

Lỗi kết nối hay timeout trong một mục làm mục đó FAIL, không làm script dừng. `report.json`:
`{"items": [{"id", "status": "PASS"|"FAIL", "detail": "<chuỗi>"}…] (đủ 4 mục), "p95_seconds": <số giây đo được, hoặc null>,
"passed": <true khi mọi mục PASS>}`.

**Test** dựng quillo 1.0.0 thật trên `lab-open` (snapshot `07-customer-integration-quillo`) với Keycloak của khách, nạp
hai tài liệu `legal/`, hai tài liệu `finance/`, bật SSO với `QUILLO_ACL=legal:legal/,finance:finance/` (user `an` nhóm
legal, `binh` nhóm finance), đo mốc p95 của chính nó, rồi chạy script của bạn ba lần với ba trạng thái của hệ thống mà
test không báo trước cho script. Chạy thẳng tệp test để có quillo và một cấu hình mẫu mà thử tay. Cả bài ~75 s.

## Tiêu chí đạt

`test_acceptance_against_real_quillo`, mỗi lần chạy ≤ 150 s và luôn ghi `report.json` đủ 4 mục:

- Hệ thống khoẻ, ngưỡng p95 = max(2 × mốc test đo, 1 s): cả 4 mục PASS, thoát `0`, `p95_seconds` là số giây thật
  (từ 0,05 s tới ngưỡng).
- Một trạng thái hỏng khác, ngưỡng p95 0,001 s: đúng `latency` và `acl` FAIL, `health` và `citations` PASS, thoát `1`.
- Dịch vụ `embed` của quillo bị dừng: cả 4 mục FAIL theo đúng quy tắc trên, `detail` của `health` nêu `embed`, thoát `1`.

## Gợi ý

### Gợi ý 1

Viết mỗi mục thành một hàm trả `{"id", "status", "detail"}` và tự bắt lỗi của riêng nó. Mục sau không được phụ thuộc mục
trước đã PASS.

### Gợi ý 2

"Người A không thấy tài liệu của người B" và "người A chỉ thấy tài liệu của A" là hai phát biểu khác nhau. Mục `acl` phải
bắt được cả trường hợp quyền bị cấp **thừa**.

### Gợi ý 3

Gửi cùng một câu hỏi nhiều lần và để ý thời gian trả lời lần đầu so với các lần sau. Con số p95 bạn báo cho khách đo
cái gì?
