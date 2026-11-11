---
title: SLO as code - sinh burn-rate alert nhiều cửa sổ cho Olist API
level: basic
services: []
files:
  - path: starter/slo.yaml
    note: 4 TODO
  - path: starter/slogen.py
    note: 5 TODO
  - path: tests/test_slogen.py
    note: Không sửa
  - path: tests/fixtures/slo.test.yml
    note: Kịch bản promtool test rules, không sửa
run:
  - uv run pytest tracks/devops/modules/16-sre-operations/exercises/basic/02-slo-burn-rate-rules -q
---

## Mục tiêu

Viết SLO thành tệp (SLO as code) rồi sinh recording rule và alert theo burn rate nhiều cửa sổ bằng script, thay vì chép tay hàng chục
biểu thức PromQL. Kiểm rule sinh ra bằng `promtool test rules` trên các kịch bản: sự cố thật phải page, một phút lỗi lẻ không được
đánh thức ai.

## Đề bài

Cần Docker: test chạy `promtool` trong image Prometheus ghim qua `testkit.promtool` (xem `## 0. Cài đặt` của module 13), không cần
dựng stack.

**1. `starter/slo.yaml`.** Hai SLO của route `/orders/{order_id}` trên `job="olist-api"` (metric của Olist Shop: counter
`http_requests_total{method, path, status}`, histogram `http_request_duration_seconds{method, path}` với bucket mặc định có `le="0.25"`):

| `name` | Ý nghĩa | `objective` (%) |
| --- | --- | --- |
| `orders-availability` | request không trả 5xx | 99.5 |
| `orders-latency` | request trả lời trong 250 ms | 95 |

`errors` và `total` là PromQL trả **một** số (tốc độ request xấu, tốc độ mọi request) có chỗ `{{window}}` cho cửa sổ, ví dụ
`sum(rate(...[{{window}}]))`. Với latency, request xấu là tổng request trừ request nằm trong bucket `le="0.25"`.

**2. `starter/slogen.py`.** Giữ nguyên `WINDOWS`, `ALERTS`, `RUNBOOK`, `main`. Viết:

1. `load_spec(path)`: đọc YAML, trả dict. `ValueError` khi: không có `slos` hay `slos` rỗng; `service` hay `name` không phải chuỗi chữ
   thường, số, `-` (tối đa 42 ký tự, không bắt đầu hay kết thúc bằng `-`); `name` trùng; `objective` không phải số trong khoảng mở
   (0, 100) (chuỗi `"99.9%"` hay `true` cũng sai); `window` khác `30d`; `errors` hay `total` không phải chuỗi có `{{window}}`.
2. `budget(slo)`: phần được phép xấu, `1 - objective / 100`.
3. `recording_rules(slo)`: với mỗi cửa sổ `w` trong `WINDOWS`, một rule `record: slo:sli_error:ratio_rate<w>`, `expr` là `(errors)` chia
   `(total)` đã thay `{{window}}` bằng `w`, `labels: {slo: <name>}`.
4. `alert_rules(slo)`: với mỗi dòng `(severity, factor, long, short)` của `ALERTS`, một rule:
   - `alert: ErrorBudgetBurn`;
   - `expr`: tỉ lệ xấu ở cửa sổ `long` **và** ở cửa sổ `short` (đọc từ recording rule, lọc `slo="<name>"`) đều lớn hơn `factor` nhân
     budget;
   - `labels`: đúng hai nhãn `severity` và `long_window` (nhãn `slo` đến từ recording rule);
   - `annotations`: `summary` và `runbook_url` (theo `RUNBOOK`);
   - không có `for`.
5. `generate(spec)`: `{"groups": [...]}`, mỗi SLO một group tên `slo-<name>` chứa recording rule rồi alert.

`python slogen.py slo.yaml > rules.yml` in tệp rule.

**Cách test chấm.** Gọi hàm của bạn, ghi `rules.yml` vào thư mục tạm, chạy `promtool check rules`, rồi chạy `promtool test rules` với
`tests/fixtures/slo.test.yml` (annotation được bỏ trước khi so). Các kịch bản trong đó: lỗi 10% thì cả bốn mức bắn; một phút lỗi 100%
sau một ngày khoẻ không bắn gì; lỗi 2% cả ngày chỉ ra ticket; lỗi 0,3% hay lỗi ở path khác không bắn; 40% request chậm trong 7 giờ
thì SLO latency page ở mức 6h; không có traffic không bắn. CLI chạy trong sandbox và phải in đúng rule như `generate`.

## Tiêu chí đạt

- `uv run pytest ... -q` pass.
- Giải thích được: vì sao cửa sổ ngắn bằng khoảng 1/12 cửa sổ dài; với SLO 99,5%, burn rate 14,4 trong 1 giờ tiêu bao nhiêu phần trăm
  budget 30 ngày; vì sao một phút lỗi 100% không page.

## Gợi ý

### Gợi ý 1

Thử từng kịch bản bằng tay: `python starter/slogen.py starter/slo.yaml > /tmp/rules.yml`, chép `tests/fixtures/slo.test.yml` vào
`/tmp`, rồi chạy lệnh `docker run ... promtool test rules` ở `setup/DEVOPS-TOOLS.md`.

### Gợi ý 2

Ngưỡng của alert là một số: `14.4 * 0.005` viết thẳng `0.072` hay để PromQL tính `(14.4 * 0.005)` đều được. Dùng `and` chứ không phải
`or`: hai cửa sổ phải cùng vượt.
