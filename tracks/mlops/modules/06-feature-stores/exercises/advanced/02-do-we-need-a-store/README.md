---
title: Cần feature store không? Sáu tình huống
level: advanced
services: []
files:
  - path: starter/decisions.yaml
    note: Quyết định cho 6 tình huống
  - path: tests/fixtures/scenarios.yaml
    note: Câu chuyện của 6 tình huống, đọc trước
  - path: tests/test_decisions.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/06-feature-stores/exercises/advanced/02-do-we-need-a-store -q
---

## Mục tiêu

Tập quyết định có lý do về feature store thay vì phản xạ "có thì tốt". Một nửa số ca đúng là không cần, và bạn phải nói được
vì sao.

## Đề bài

`tests/fixtures/scenarios.yaml` có 6 tình huống S1..S6. Với mỗi tình huống điền vào `starter/decisions.yaml`:

- `decision`, một trong ba giá trị: `none` (không cần feature store; dùng bảng, thư viện chung, test), `feast` (tự host Feast
  hoặc tương đương mã nguồn mở), `managed` (dịch vụ quản lý như Tecton hoặc Hopsworks).
- `reasons`: danh sách lý do, mỗi lý do **ít nhất 20 ký tự**, không còn `TODO`.

Test kiểm `decision` khớp tình huống và kiểm lý do có nhắc các từ khoá mà ca đó đòi (không phân biệt hoa thường):

| Ca | Từ khoá bắt buộc trong lý do |
| --- | --- |
| S1 | `online` |
| S2 | `thân yêu cầu` |
| S3 | `point-in-time` và `online` |
| S4 | `streaming` và `SLA` |
| S5 | `parity` |
| S6 | `theo lô` |

Một test khác đưa vào bộ kiểm tra một bản trả lời phản xạ (mọi ca đều `feast`) và đòi nó bị bắt. Chất lượng lập luận chấm bằng
rubric trong `solutions/advanced/02-do-we-need-a-store/SOLUTION.md`; đọc **sau** khi làm xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/06-feature-stores/exercises/advanced/02-do-we-need-a-store -q` pass.
- Với ca S5, nói được cách sửa không cần mua gì và phép kiểm nào để biết đã sửa.
- Tự chấm đạt ít nhất 70/100 điểm rubric.

## Gợi ý

### Gợi ý 1

Hỏi ba câu: có ai tra feature theo thực thể trong vài chục mili giây không (online)? Có nhiều model hay đội dùng chung feature
không? Ai vận hành nó, và họ còn thời gian cho việc khác không?

### Gợi ý 2

Skew là triệu chứng, không phải lý do để mua công cụ: hỏi nguyên nhân gốc của skew trong ca đó và công cụ rẻ nhất chặn nó.
