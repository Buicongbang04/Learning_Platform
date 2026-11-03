---
title: Trivy - sửa misconfiguration và viết cổng chặn lỗ hổng
level: intermediate
services: []
files:
  - path: starter/Dockerfile
    note: Sửa cho trivy config sạch
  - path: starter/triage.py
    note: Viết gate()
  - path: tests/test_trivy.py
    note: Không sửa
run:
  - trivy --version
  - uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/intermediate/03-trivy-gate -q -rs
---

## Mục tiêu

Dùng trivy như một cổng chất lượng trong CI: sửa lỗi cấu hình Dockerfile mà nó báo, và biến báo cáo lỗ hổng thành quyết định pass/fail có chính sách, thay vì chặn mọi thứ hay không chặn gì.

## Đề bài

Cài trivy theo mục `## 0. Cài đặt` của lý thuyết. Thiếu trivy thì test quét Dockerfile sẽ skip (kèm lệnh cài); các test còn lại vẫn chạy.

**Phần 1 - `starter/Dockerfile`.** Sửa để `trivy config` không còn finding nào ở trạng thái FAIL (mọi mức độ). Vẫn phải cài `flask` bằng `pip install`, nhưng ghim phiên bản (`flask==<phiên bản>`).

**Phần 2 - `starter/triage.py`.** Viết `gate(report, policy)` đọc báo cáo của `trivy image --format json` (`Results[].Vulnerabilities[]` với `VulnerabilityID`, `Severity`, `FixedVersion`):

- chỉ xét các mức trong `policy["fail_on"]`; mức khác bỏ qua hoàn toàn (không vào `blocking` lẫn `ignored`);
- lỗ hổng trong `policy["allow"]`, hoặc chưa có bản vá (`FixedVersion` rỗng hay thiếu) khi `policy["ignore_unfixed"]` bật, đi vào `ignored`;
- còn lại vào `blocking`; một ID vừa blocking vừa ignored (ở hai target khác nhau) chỉ nằm trong `blocking`;
- trả `{"decision": "fail" nếu có blocking, ngược lại "pass", "blocking": [...], "ignored": [...]}`, hai danh sách đã sắp xếp, không trùng;
- `Vulnerabilities` có thể là `null` hoặc thiếu, `Results` có thể thiếu: coi như không có lỗ hổng.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/intermediate/03-trivy-gate -q -rs` pass, không skip khi đã cài trivy.
- Giải thích được vì sao bỏ qua lỗ hổng chưa có bản vá là quyết định chính sách cần ghi lại, không phải chuyện kỹ thuật.

## Gợi ý

### Gợi ý 1

`trivy config --format json` liệt kê từng finding với `ID`, `Severity`, `Title` và `Status`; mô tả mỗi lỗi cho biết cách sửa.

### Gợi ý 2

Dùng tập hợp (`set`) cho `blocking` và `ignored`, rồi trừ `ignored` đi phần đã có trong `blocking`.
