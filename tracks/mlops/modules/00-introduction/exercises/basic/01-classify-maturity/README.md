---
title: Xếp hạng maturity của ba hệ thống ML đang chạy
level: basic
services: []
files:
  - path: starter/classification.yaml
    note: Điền 12 ô TODO
  - path: tests/fixtures/systems.yaml
    note: Mô tả ba hệ thống và facts, chỉ đọc
  - path: tests/test_maturity.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/00-introduction/exercises/basic/01-classify-maturity -q
---

## Mục tiêu

Đọc một hệ thống ML thật sự đang làm gì (không phải công cụ nó dùng) rồi xếp đúng mức maturity theo Google và Microsoft,
và chỉ ra thiếu gì để lên mức tiếp theo.

## Đề bài

Mở `tests/fixtures/systems.yaml`: ba hệ thống (`quote-pricing`, `recsys-ranking`, `fraud-scoring`), mỗi hệ thống có một đoạn
kể và bảng `facts` đúng/sai. Điền `starter/classification.yaml` cho từng hệ thống:

- `google_level`: 0, 1 hoặc 2. Luật dùng trong bài: mức 0 nếu training chưa tự kích hoạt; mức 1 nếu training tự kích hoạt
  nhưng pipeline chưa có CI/CD; mức 2 nếu pipeline cũng có CI/CD.
- `microsoft_level`: 0..4. Mức 4 cần deploy tự động và monitoring kích hoạt retrain; mức 3 cần deploy tự động có cổng
  kiểm tra model; mức 2 cần training tự kích hoạt và có tracking/registry; mức 1 nếu code có CI kiểm thử; còn lại mức 0.
- `blocker`: khoá trong `facts` mà việc thiếu nó giữ hệ thống ở mức Google hiện tại (`null` nếu đã mức 2).
- `rationale`: ít nhất 60 ký tự, nêu các facts quyết định.

Chú ý hai thang đo **không** trùng nhau: một hệ thống có CI cho code API vẫn có thể ở mức 0 của Google.

## Tiêu chí đạt

- Cả ba hệ thống đúng `google_level` và `microsoft_level`.
- `blocker` đúng khoá cho từng hệ thống.
- Mỗi `rationale` đủ 60 ký tự.

## Gợi ý

### Gợi ý 1

Google hỏi: training có tự chạy không, rồi pipeline có được CI/CD không. Có Git và CI cho code API chưa trả lời câu hỏi đầu.

### Gợi ý 2

`recsys-ranking` có Airflow, validation và registry nhưng người ta vẫn `ssh` lên server để cập nhật DAG: facts `pipeline_cicd` là
`false`, đó là blocker.
