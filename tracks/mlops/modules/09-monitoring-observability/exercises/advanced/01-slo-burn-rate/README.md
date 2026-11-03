---
title: SLO, error budget và alert burn-rate hai cửa sổ cho service ETA
level: advanced
services: []
files:
  - path: starter/SLO.md
    note: Tài liệu SLO, điền mọi TODO
  - path: starter/slo.rules.yml
    note: Recording rule và alert burn-rate (đang rỗng)
  - path: tests/fixtures/SLO.bad.md
    note: Ví dụ tài liệu yếu, test dùng để kiểm bộ kiểm tra
  - path: tests/test_slo.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/advanced/01-slo-burn-rate -q
---

## Mục tiêu

Chuyển từ "alert khi lỗi vượt 5%" sang cách làm của đội SRE: đặt SLO, tính error budget, và cảnh báo theo **tốc độ đốt budget**
bằng hai cửa sổ. Phần tài liệu và phần rule đều được kiểm bằng máy; lập luận chấm bằng rubric.

## Đề bài

Service ETA (`/predict`) cần SLO khả dụng **99.5% trong 30 ngày**. Viết hai tệp.

**`starter/SLO.md`**, giữ các heading `## 1.` tới `## 5.`, không còn chữ `TODO`:

| Phần | Yêu cầu kiểm tự động |
| --- | --- |
| 1. SLI và SLO | Lời dẫn ít nhất 200 ký tự (không tính bảng); bảng ít nhất 3 SLI đủ 4 cột (`SLI`, `Định nghĩa (PromQL)`, `SLO`, `Cửa sổ`); một SLI có SLO `99.5%` và cửa sổ `30d`; cột định nghĩa không nhắc CPU, RAM, đĩa hay `node_` (đo thứ người dùng thấy, không đo nguyên nhân) |
| 2. Error budget | Bảng `Cửa sổ`, `SLO khả dụng`, `Budget (phút)`; dòng `30d` có budget 216 (sai số 1) |
| 3. Burn-rate alert | Bảng ít nhất 3 mức đủ 6 cột (`Mức`, `Burn rate`, `Cửa sổ dài`, `Cửa sổ ngắn`, `% budget tiêu`, `Hành động`); cửa sổ viết dạng `5m`, `1h`, `3d`; cửa sổ ngắn bằng **đúng 1/12** cửa sổ dài; `% budget tiêu` = burn rate x cửa sổ dài (giờ) / 720 x 100 (sai số 0.3); có ít nhất một hành động chứa `page` và một chứa `ticket` |
| 4. Quy trình khi budget cạn | Một khối ` ```mermaid ` có ít nhất 4 cạnh; ít nhất 3 gạch đầu dòng, có nhắc `freeze` hoặc `đóng băng` |
| 5. Giới hạn và rủi ro | Ít nhất 3 gạch đầu dòng |

**`starter/slo.rules.yml`** (kiểm bằng `promtool check rules` và `promtool test rules` qua `mlopskit.promtool`, không cần stack):

- Bốn recording rule `eta:http_error_ratio:rate5m`, `rate30m`, `rate1h`, `rate6h`: tỉ lệ 5xx trên `route="/predict"` của
  `job="eta-service"` ở từng cửa sổ (dữ liệu có nhãn `job`, `method`, `route`, `status`; `status` là mã HTTP như `"500"`).
- Alert `ETAErrorBudgetFastBurn` (`severity: critical`): burn rate 14.4 trên cửa sổ 1h **và** 5m, tức biểu thức dùng `rate1h` và
  `rate5m` nối bằng `and`.
- Alert `ETAErrorBudgetSlowBurn` (`severity: warning`): burn rate 6 trên 6h **và** 30m, dùng `rate6h` và `rate30m`.
- Mỗi alert có `annotations.runbook_url` bắt đầu bằng `https://`.
- Kịch bản kiểm lúc 8 giờ: lỗi 10% thì cả hai alert bắn; lỗi 5% chỉ SlowBurn bắn; lỗi 0.5% không bắn; không traffic không bắn.

Test còn đưa một tài liệu yếu (`tests/fixtures/SLO.bad.md`) vào cùng bộ kiểm tra và đòi nó bị bắt. Nội dung chấm bằng rubric trong
`solutions/advanced/01-slo-burn-rate/SOLUTION.md`; đọc rubric **sau** khi viết xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/advanced/01-slo-burn-rate -q` pass.
- Tự chấm đạt ít nhất 70/100 điểm rubric.
- Bạn tự tính lại được vì sao burn rate 14.4 trong 1 giờ tiêu 2% budget 30 ngày, không chép số.

## Gợi ý

### Gợi ý 1

Budget 30 ngày là `0.5% x 43 200 phút`. Tỉ lệ lỗi đúng bằng ngưỡng của burn rate B là `B x (1 - SLO)`; với SLO 99.5% và B = 14.4
đó là 7.2%. Ghi hằng số vào rule dạng `(14.4 * 0.005)` để người đọc thấy nguồn gốc con số.

### Gợi ý 2

Tự hỏi: nếu chỉ có cửa sổ dài thì sau khi sửa lỗi alert còn bắn bao lâu? Nếu chỉ có cửa sổ ngắn thì một đợt spike 2 phút làm gì?
Đó là lý do cho `and`.
