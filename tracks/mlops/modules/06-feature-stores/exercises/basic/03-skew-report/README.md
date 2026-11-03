---
title: Báo cáo skew giữa feature offline và online
level: basic
services: []
files:
  - path: starter/skew.py
    note: Hàm skew_report cần viết
  - path: tests/test_skew.py
    note: Không sửa
  - path: quiz.yaml
    note: Trắc nghiệm về nguồn skew và khi nào cần feature store
run:
  - uv run pytest tracks/mlops/modules/06-feature-stores/exercises/basic/03-skew-report -q
---

## Mục tiêu

Có công cụ đo skew thay vì đoán: so feature của **cùng thực thể** giữa bảng offline (lúc train) và bảng online (log lúc
serve), và chỉ ra cột nào lệch, lệch kiểu gì, bao nhiêu. Công cụ này dùng lại ở bài sự cố.

## Đề bài

Trong `starter/skew.py` viết `skew_report(offline, online, key, rtol=1e-6, atol=1e-9) -> list[dict]`.

Hai DataFrame có cột khoá `key`; các cột còn lại là feature. Nối hai bên theo `key` (khoá chỉ có ở một bên bị bỏ qua khi so giá
trị). Trả danh sách `dict`, mỗi mục là một vấn đề, có đúng 4 khoá `column`, `kind`, `mismatch_rate`, `max_abs_diff`:

| `kind` | Khi nào | `column` | `mismatch_rate` | `max_abs_diff` |
| --- | --- | --- | --- | --- |
| `missing_column` | cột (không phải khoá) chỉ có ở một bên | tên cột | 1.0 | `None` |
| `row_coverage` | tập khoá hai bên khác nhau | `"__rows__"` | số khoá chỉ có ở một bên chia số khoá của hợp hai bên | `None` |
| `null_mismatch` | cột chung, trên các dòng nối được có ít nhất một dòng một bên null một bên có giá trị | tên cột | tỉ lệ dòng nối được bị lệch (null lệch hoặc giá trị lệch) | lệch tuyệt đối lớn nhất trên các dòng cả hai có giá trị, hoặc `None` nếu không có / không phải số |
| `value_mismatch` | cột chung, không có null lệch nhưng có giá trị khác nhau | tên cột | như trên | như trên |

- Cột số so bằng `np.isclose(rtol, atol)`; cột không phải số so bằng `==` và `max_abs_diff` là `None`.
- Hai bên cùng `NaN` thì **không** phải lệch.
- Cột chung không lệch thì không xuất hiện trong kết quả.
- Sắp xếp kết quả theo `mismatch_rate` giảm dần, bằng nhau thì theo `column` tăng dần. Không sửa đầu vào.

Phần trắc nghiệm trong `quiz.yaml` làm trên giao diện học, không do `pytest` chấm.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/06-feature-stores/exercises/basic/03-skew-report -q` pass.
- Trả lời đúng trắc nghiệm trên giao diện.
- Giải thích được vì sao `null_mismatch` thường là dấu hiệu của default khác nhau chứ không phải sai số.

## Gợi ý

### Gợi ý 1

Tách việc làm theo từng loại: cột và khoá (so tập hợp), rồi mới nối và so giá trị. Với mỗi cột, tính hai mặt nạ: "null lệch"
(một bên null) và "giá trị khác trên các dòng cả hai có giá trị".

### Gợi ý 2

`np.isclose(..., equal_nan=True)` xử lý NaN ở cả hai bên; nhớ chỉ tính `max_abs_diff` trên dòng thực sự lệch. Sau nối với
`suffixes`, hai cột cùng tên có hậu tố khác nhau.
