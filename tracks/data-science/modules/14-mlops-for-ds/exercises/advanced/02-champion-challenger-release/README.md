---
title: Phát hành challenger an toàn - shadow, quy tắc promote, rollback
level: advanced
services: []
files:
  - path: starter/release.py
    note: 4 hàm TODO
  - path: starter/RELEASE.md
    note: Kế hoạch phát hành
  - path: tests/test_release.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/14-mlops-for-ds/exercises/advanced/02-champion-challenger-release -q
---

## Mục tiêu

Thay model đang chạy bằng một model mới mà không đánh cược: chạy challenger ở chế độ shadow, đánh
giá bằng quy tắc viết trước, promote bằng cách đổi alias trong registry, và luôn có đường rollback
một lệnh. Viết kế hoạch phát hành mà PM và kỹ sư vận hành đọc được.

## Đề bài

Model review xấu đang chạy (champion) là logistic regression của module. Bạn có một challenger
(tự chọn: thêm feature, LightGBM, train lại trên dữ liệu mới hơn…). Ở chế độ shadow, mỗi request được
cả hai model chấm; khách chỉ nhận quyết định của champion, điểm của challenger chỉ được ghi lại.
Nhãn (review) về sau đó vài ngày.

1. Trong `starter/release.py`, cài đúng docstring:
   - `shadow_report(log, threshold) -> dict`: AUC hai model trên dòng đã có nhãn, PSI giữa score
     hai model, tỉ lệ đổi quyết định (`flip_rate`), p95 độ trễ.
   - `promotion_decision(report, ...) -> str`: `need_more_data` / `keep` / `manual_review` /
     `promote` theo thứ tự quy tắc trong docstring.
   - `apply_decision(tracking_uri, model_name, challenger_version, decision) -> dict` và
     `rollback(tracking_uri, model_name) -> int`: đổi alias `champion`, `challenger`,
     `previous_champion` trong MLflow Model Registry.
2. Dựng challenger thật trên Olist, so offline với champion trên cùng tập test (chia theo thời gian
   của module).
3. Viết `starter/RELEASE.md` theo khung có sẵn.

## Tiêu chí đạt

- `shadow_report` đúng từng chỉ số, chỉ tính AUC trên dòng có nhãn, trả NaN khi chưa có nhãn.
- `promotion_decision` đúng cả bốn nhánh, kể cả khi challenger tốt hơn nhưng quá chậm.
- Promote chuyển `champion` sang challenger, giữ `previous_champion`, xoá `challenger`; quyết định
  khác không đổi gì; rollback đưa champion về version trước và từ chối rollback lần hai.
- `RELEASE.md` không còn TODO, ít nhất 450 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`MlflowClient(uri).get_registered_model(name).aliases` là dict `alias → version`. Ở MLflow 3, số
version có thể là `int` hoặc chuỗi tuỳ API: ép `int(...)` khi trả về, `str(...)` khi gọi
`set_registered_model_alias`.

### Gợi ý 2

`flip_rate` quan trọng không kém AUC: hai model có AUC bằng nhau vẫn có thể liên hệ những khách
**khác nhau**. Đội CSKH cảm nhận model qua danh sách khách được gọi, không qua AUC. Trong RELEASE.md,
tính thời lượng shadow từ số đơn có nhãn cần (`min_labeled`), số đơn giao mỗi tuần và độ trễ của
nhãn.
