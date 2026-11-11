---
title: SLO, SLA và error budget của Olist API từ số liệu tháng 10
level: basic
services: []
files:
  - path: starter/budget.py
    note: 7 TODO
  - path: data/olist-api-2026-10.csv
    note: Số request theo giờ, tháng 10/2026 (giờ UTC)
  - path: tests/test_budget.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/16-sre-operations/exercises/basic/01-sla-error-budget -q
---

## Mục tiêu

Tính SLO theo request và SLA theo thời gian trên cùng một tháng số liệu, thấy vì sao hai con số khác nhau, biết error budget cạn từ
giờ nào, burn rate ở từng cửa sổ, và hợp đồng phải trả credit bao nhiêu.

## Đề bài

`data/olist-api-2026-10.csv` có 744 dòng, mỗi dòng là một giờ của tháng 10/2026 (UTC) do Prometheus của Olist API tổng hợp:

| Cột | Ý nghĩa |
| --- | --- |
| `hour` | Đầu giờ, dạng `2026-10-01T00:00:00Z` |
| `requests` | Số request trong giờ |
| `errors` | Số request trả 5xx |
| `slow` | Số request không lỗi nhưng chậm hơn 500 ms |
| `maintenance` | `1` nếu giờ đó nằm trong cửa sổ bảo trì đã báo trước cho khách, `0` nếu không |

Hai cam kết:

- **SLO nội bộ** (request-based): 99,7% request trong tháng là request tốt, tức không 5xx và không chậm. Bảo trì vẫn tính, vì khách
  vẫn bị ảnh hưởng.
- **SLA với đối tác bán hàng** (time-based): một giờ bị tính là sập khi tỉ lệ 5xx trong giờ đó **lớn hơn** 5%. Giờ bảo trì đã báo
  trước bị bỏ khỏi cả tử số lẫn mẫu số. Credit theo bảng `[(99.9, 0), (99.0, 10), (95.0, 25), (0, 100)]`: availability (tính theo %)
  từ 99,9 trở lên thì 0% credit, từ 99,0 thì 10%, từ 95,0 thì 25%, thấp hơn nữa thì 100%.

Điền 7 hàm trong `starter/budget.py`:

1. `load(path)`: đọc CSV, trả list dict cùng khoá với cột; `requests`, `errors`, `slow` là `int`, `maintenance` là `bool`. Cột khác
   đúng `FIELDS` (cả thứ tự), hay `errors + slow` âm hoặc lớn hơn `requests`, thì `ValueError`.
2. `sli(rows)`: tỉ lệ request tốt. Không có request nào thì `ValueError`.
3. `budget_report(rows, slo)`: dict
   - `total`, `bad` (5xx cộng chậm),
   - `allowed_bad` bằng (1 - slo) nhân `total`,
   - `consumed` bằng `bad / allowed_bad`, `remaining` bằng `1 - consumed` (âm khi tiêu quá),
   - `exhausted_at`: `hour` của dòng đầu tiên mà tổng `bad` cộng dồn từ đầu tháng **vượt** `allowed_bad` của cả tháng; chưa vượt
     thì `None`.

   `slo` ngoài khoảng mở (0, 1), ví dụ gõ `99.7`, thì `ValueError`.
4. `burn_rates(rows, slo, end_hour, windows=(1, 6, 24, 72))`: với mỗi cửa sổ `w` giờ kết thúc ở `end_hour` (tính cả giờ đó), burn rate
   là tỉ lệ request xấu trong cửa sổ chia (1 - slo). Trả dict `{w: burn_rate}`. `end_hour` không có trong dữ liệu, hay cửa sổ dài hơn
   số giờ có tới `end_hour`, thì `ValueError`.
5. `sla_availability(rows, threshold=0.05)`: 1 trừ (số giờ sập chia số giờ không bảo trì).
6. `sla_credit(availability, tiers)`: phần trăm credit (`int`); `availability` là tỉ lệ (0,9996), mức trong `tiers` là phần trăm.
7. `policy(report)`: chính sách error budget rút gọn: `remaining` lớn hơn 0,5 là `"normal"`, từ trên 0 tới 0,5 là `"caution"`, từ 0 trở
   xuống là `"freeze"`.

## Tiêu chí đạt

- `uv run pytest ... -q` pass.
- Trả lời được: tháng 10 SLO đã cạn budget mà SLA chỉ mất 10% credit, vì sao hai cách đo cho kết quả ngược nhau? Sự cố latency đêm
  23/10 ảnh hưởng con số nào và không ảnh hưởng con số nào?

## Gợi ý

### Gợi ý 1

Làm trên ví dụ nhỏ trước: ba giờ, mỗi giờ 1000 request, lỗi 1, 2, 3 với SLO 99,8% thì `allowed_bad` là 6 và tiêu vừa đủ, chưa vượt.

### Gợi ý 2

`burn_rates` cắt danh sách theo vị trí của `end_hour`: cửa sổ `w` là `w` dòng kết thúc ở dòng đó. SLA chỉ nhìn 5xx, không nhìn `slow`.
