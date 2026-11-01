---
title: Judge khớp với người tới đâu - Cohen's kappa và đổi chỗ khi so cặp
level: basic
services: []
files:
  - path: starter/agreement.py
    note: 4 hàm TODO
  - path: tests/test_agreement.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/20-evaluation-production/exercises/basic/02-judge-agreement -q
---

## Mục tiêu

Viết các thước đo để quyết định có tin một LLM judge hay không: độ khớp với nhãn người đã trừ phần khớp do may rủi
(Cohen's kappa), judge sai theo hướng nào (dễ dãi hay khắt khe), và khi so hai câu trả lời thì judge có chọn theo vị trí
thay vì theo nội dung không. Bài Intermediate 01 dùng đúng các hàm này trên judge `qwen2.5:3b` và `qwen2.5:7b` thật.

## Đề bài

**Phần cứng:** CPU · ~45 phút

Trong `starter/agreement.py`, chỉ dùng thư viện chuẩn:

1. `cohen_kappa(a, b) -> float`: hai dãy nhãn (kiểu bất kỳ so sánh được bằng `==`) cùng độ dài, không rỗng, theo công
   thức ở mục 2 lý thuyết. $$p_e$$ tính từ tần suất biên của từng người chấm. Khi $$p_e = 1$$ (cả hai chỉ dùng đúng một nhãn và
   trùng nhau) trả `nan`. `ValueError` khi độ dài lệch hoặc rỗng.
2. `calibration_report(judge, human) -> dict`: `judge[i]` là `True` (judge cho qua), `False` hoặc `None` (không đọc được
   verdict); `human[i]` là nhãn người, `True`/`False`. Bỏ mọi vị trí `judge` là `None` rồi trả:
   - `n` (số vị trí còn lại), `unparsed` (số vị trí bị bỏ);
   - `accuracy`, `kappa` (trên các vị trí còn lại);
   - `false_pass`: trong các câu người chấm `False`, tỉ lệ judge cho `True` (`nan` nếu không có câu nào như vậy);
   - `false_fail`: trong các câu người chấm `True`, tỉ lệ judge cho `False` (`nan` nếu không có);
   - `judge_pass_rate`, `human_pass_rate`.

   `ValueError` khi độ dài lệch hoặc không còn vị trí nào.
3. `resolve_swap(v_ab, v_ba) -> str`: judge so A với B hai lần. Lần một A đứng trước, verdict `v_ab`; lần hai B đứng
   trước, verdict `v_ba`. Verdict là `"first"`, `"second"` hoặc `"tie"` theo **vị trí** trong prompt. Đổi mỗi verdict
   ra người thắng (`"A"`, `"B"` hoặc `"tie"`); hai lần cho cùng kết quả thì trả kết quả đó, khác nhau thì
   `"inconsistent"`. Verdict lạ: `ValueError`.
4. `pairwise_summary(pairs) -> dict`, `pairs` là list `(v_ab, v_ba)`: `n`, số cặp mỗi loại `A`, `B`, `tie`,
   `inconsistent`; `consistency` = tỉ lệ cặp không `inconsistent`; `win_rate_A` = (số `A` + 0.5 × (số `tie` + số
   `inconsistent`)) / `n`; `first_rate` = trong mọi verdict không phải `"tie"` của cả hai lượt, tỉ lệ là `"first"`
   (`nan` nếu không có verdict nào như vậy). `ValueError` khi rỗng.

## Tiêu chí đạt

- `cohen_kappa` khớp ví dụ tính tay (0.4) và `sklearn.metrics.cohen_kappa_score` trên 20 cặp dãy ba nhãn ngẫu nhiên;
  90% khớp vẫn có thể là kappa 0.
- `calibration_report` đúng mọi trường trên ví dụ của test, loại `None`, trả `nan` khi thiếu một lớp.
- `resolve_swap` đúng ở 7 tổ hợp verdict; `pairwise_summary` đúng đếm, tỉ lệ thắng, tỉ lệ chọn vị trí đầu, và nhận ra
  judge luôn chọn đoạn đứng trước.

## Gợi ý

### Gợi ý 1

`collections.Counter` cho tần suất biên của từng người chấm; $$p_e$$ là tổng theo nhãn của tích hai tần suất. Kiểm tay
ca "người chấm A luôn nói có": kappa phải bằng 0 dù accuracy cao.

### Gợi ý 2

Trong `resolve_swap`, viết hai bảng tra: một cho lượt A đứng trước, một cho lượt B đứng trước. Một judge chỉ thích vị
trí đầu sẽ trả `"first"` ở cả hai lượt: hai lượt đó chọn hai người thắng khác nhau.
