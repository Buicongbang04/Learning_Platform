---
title: Feedback loop, model tự làm lệch dữ liệu nó học
level: basic
services: []
files:
  - path: starter/feedback.py
    note: 4 TODO
  - path: tests/test_feedback.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/16-streaming-realtime-ml/exercises/basic/03-feedback-loop-bias -q
---

## Mục tiêu

Model chống gian lận chặn giao dịch rủi ro cao. Giao dịch bị chặn không bao giờ hoàn tất nên không bao giờ có nhãn (chargeback).
Dữ liệu huấn luyện vòng sau chỉ gồm giao dịch model đã cho qua: tỉ lệ gian lận "quan sát được" giảm dần, đội tưởng gian lận đã hết,
trong khi thật ra model đang tự che mắt mình. Bạn viết bộ phát hiện thiên lệch này bằng một nhóm giữ lại (exploration) và
inverse propensity weighting.

## Đề bài

Test mô phỏng 4 vòng, mỗi vòng 5 000 giao dịch; mỗi vòng model hạ ngưỡng chặn nên chặn nhiều hơn. Giao dịch bị chặn vẫn được cho
qua ngẫu nhiên với xác suất `epsilon` (nhóm exploration). Mỗi dòng log:

| Khoá | Ý nghĩa |
| --- | --- |
| `round` | số vòng (0, 1, ...) |
| `risk` | điểm rủi ro model tính |
| `approved` | giao dịch có được cho qua không |
| `p_approve` | xác suất được cho qua, ghi **lúc ra quyết định** (1.0 nếu dưới ngưỡng, `epsilon` nếu trên ngưỡng) |
| `label` | 1 gian lận, 0 không; `None` khi không được cho qua (không bao giờ biết nhãn) |

Điền `starter/feedback.py`:

1. `naive_rate(log)`: trung bình `label` trên các dòng có nhãn; không có dòng nào có nhãn thì `None`.
2. `ipw_rate(log)`: ước lượng Horvitz–Thompson cho tỉ lệ gian lận của **mọi** giao dịch:
   `sum(label / p_approve trên các dòng có nhãn) / số dòng`. Log rỗng, hoặc có dòng `p_approve <= 0` (không có exploration nên
   không ước lượng được) thì `None`.
3. `bias_report(log, tolerance=0.01)`: dict `{"naive", "ipw", "gap", "biased"}` với `gap = naive - ipw`,
   `biased = abs(gap) > tolerance`. Khi `naive` hoặc `ipw` là `None` thì `gap` và `biased` là `None` (không đo được khác với
   "không lệch").
4. `per_round(log, tolerance=0.01)`: list `bias_report` của từng vòng, tăng dần theo vòng, mỗi dict thêm khoá `"round"`.

Test so `ipw` với tỉ lệ gian lận thật của mô phỏng (sai số 0.015 trên toàn log, 0.03 từng vòng), kiểm `naive` thấp hơn thật ít nhất
0.03 và giảm dần qua các vòng, và một ca đối chứng không chặn gì thì `biased` là `False`.

## Tiêu chí đạt

- Test pass.
- Bạn giải thích được vì sao `p_approve` phải được ghi lúc quyết định chứ không tính lại sau, và vì sao không có exploration thì
  không thuật toán nào sửa được thiên lệch này.
- Bạn nêu được giá của exploration (cho qua một phần giao dịch rủi ro) và cách giữ nó nhỏ.

## Gợi ý

### Gợi ý 1

Một giao dịch có nhãn với `p_approve = 0.1` "đại diện" cho 10 giao dịch giống nó, 9 cái kia bị chặn và không có nhãn. Đó là toàn bộ
ý tưởng của trọng số `1 / p_approve`.

### Gợi ý 2

`per_round` chỉ là lọc log theo vòng rồi gọi lại `bias_report`; dùng `dict(report, round=r)` để thêm khoá.
