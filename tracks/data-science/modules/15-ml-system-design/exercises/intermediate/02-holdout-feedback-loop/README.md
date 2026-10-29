---
title: Holdout và feedback loop khi hệ thống đã can thiệp
level: intermediate
services: []
files:
  - path: starter/holdout.py
    note: 4 hàm TODO
  - path: tests/test_holdout.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/15-ml-system-design/exercises/intermediate/02-holdout-feedback-loop -q
---

## Mục tiêu

Sau khi hệ thống cảnh báo chạy, hai câu hỏi khó nhất là: nó có tác dụng thật không, và retrain model
thế nào khi chính hành động của hệ thống đã thay đổi nhãn. Bài này trả lời cả hai bằng log quyết định
có holdout.

## Đề bài

Mỗi dòng log là một đơn: `flagged` (vượt ngưỡng cảnh báo), `holdout` (được cảnh báo nhưng giữ lại ngẫu
nhiên, không nhắn tin), `treated` (= `flagged & ~holdout`), `bad` (0/1, review xấu). Trong
`starter/holdout.py`:

1. `naive_effect(log)`: tỉ lệ `bad` ở đơn được can thiệp trừ tỉ lệ ở **mọi** đơn không được can thiệp.
   Đây là phép so sánh mà dashboard ngây thơ hay làm.
2. `holdout_effect(log, alpha=0.05) -> (diff, lo, hi)`: trong các đơn `flagged`, tỉ lệ `bad` của nhóm
   treated trừ nhóm holdout; CI theo xấp xỉ normal với SE **không pooled**
   $$\sqrt{p_t(1-p_t)/n_t + p_h(1-p_h)/n_h}$$.
3. `realized_value(log, cost_action, loss_event, alpha=0.05) -> (value, lo, hi)`: giá trị mỗi đơn được
   can thiệp, $$-\text{diff} \cdot V - C$$, với CI suy ra từ CI của diff (chú ý đổi chiều).
4. `retraining_rows(log, holdout_share)`: dữ liệu để retrain model rủi ro: bỏ đơn đã được can thiệp,
   thêm cột `weight` (1 cho đơn không flagged, `1 / holdout_share` cho đơn holdout).

## Tiêu chí đạt

- Đúng trên log nhỏ tính tay.
- Trên dữ liệu giả lập (can thiệp giảm thật 10 điểm %), `naive_effect` dương (trông như có hại) còn
  `holdout_effect` gần −0.10 trên 10 seed, CI phủ giá trị thật ở ít nhất 85% của 40 seed.
- `retraining_rows` không còn đơn được can thiệp; nhóm flagged sau khi đặt trọng số có cỡ và tỉ lệ
  `bad` gần với khi không can thiệp.

## Gợi ý

### Gợi ý 1

So sánh ngây thơ lẫn hai thứ: tác động của can thiệp **và** việc đơn được can thiệp là đơn rủi ro cao.
Holdout ngẫu nhiên **trong** nhóm flagged loại được thứ hai, vì treated và holdout chỉ khác nhau ở việc
có được nhắn tin hay không.

### Gợi ý 2

Nếu retrain trên mọi đơn, các đơn rủi ro cao (đã được nhắn tin, nên ít review xấu hơn) dạy model rằng
chúng "ít rủi ro". Lần sau chúng không được cảnh báo nữa, review xấu tăng lại, model lại học ngược: một
vòng dao động. Holdout chỉ giữ một phần nhỏ nhóm flagged, nên cần trọng số để nhóm đó không bị đại diện
thiếu.
