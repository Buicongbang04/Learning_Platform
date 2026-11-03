---
title: Quyết định retrain, rollback hay giữ nguyên qua ba tình huống có số liệu
level: intermediate
services: []
files:
  - path: starter/scenarios.json
    note: Dữ liệu ba tình huống, không sửa
  - path: starter/decisions.yaml
    note: Điền decision, reasons, evidence
  - path: tests/test_decisions.py
    note: Không sửa
  - path: tests/fixtures/scenarios.json
    note: Bản gốc của dữ liệu, không sửa
run:
  - uv run pytest tracks/mlops/modules/10-drift-incidents/exercises/intermediate/03-drift-decision-scenarios -q
---

## Mục tiêu

Luyện quyết định như một on-call ML: mỗi tình huống có số liệu drift, chất lượng và vận hành; bạn chọn `retrain`, `rollback` hoặc `keep` và dẫn đúng con số làm bằng chứng. Mục tiêu không phải thuộc đáp án mà
là quen với thứ tự detect, verify, impact, decide: drift không tự nó là lý do để làm gì.

## Đề bài

Đọc `starter/scenarios.json`: ba tình huống `holiday-week`, `bad-release`, `covid-lockdown`, mỗi tình huống có `context`, `metrics` (dict tên số đo sang số) và `quality_keys` (những số đo đến từ nhãn).
Số đo của `covid-lockdown` là số đo thật (PSI, MAE, tỉ lệ thiếu) từ bài notebook `01-tlc-seasonal-vs-covid` trên NYC TLC. `holiday-week` và `bad-release` là tình huống **dựng sẵn** (constructed): số liệu của chúng không phải số đo từ NYC TLC.

Điền `starter/decisions.yaml`. Mỗi tình huống có ba khoá:

```yaml
holiday-week:
  decision: keep        # retrain | rollback | keep
  reasons:
    - "Lý do 1, một câu đầy đủ"
    - "Lý do 2"
  evidence:
    psi_trip_distance: 0.31
    mae_current: 3.66
```

Luật mà test ép:

- Khoá cấp một của tệp đúng ba id tình huống. `decision` là một trong `retrain`, `rollback`, `keep` và phải là quyết định đúng của tình huống đó. Ba tình huống có ba quyết định khác nhau.
- `reasons`: danh sách ít nhất 2 chuỗi, mỗi chuỗi dài từ 30 ký tự. Nội dung lý do không do test chấm; tự chấm bằng rubric trong `SOLUTION.md`.
- `evidence`: mapping có ít nhất 2 mục. Khoá phải là tên có trong `metrics` của tình huống, giá trị phải là số khớp `metrics` (sai số tương đối 1%), và phải có **ít nhất một** khoá thuộc `quality_keys`
  (bằng chứng từ nhãn, không chỉ từ drift).
- Không sửa `scenarios.json` (test so với bản gốc).

## Tiêu chí đạt

- Cả ba `decision` đúng.
- Bằng chứng trích đúng số, mỗi tình huống có ít nhất một số đo chất lượng.
- Tự chấm lý do bằng rubric: mỗi lý do trả lời được "tín hiệu nào, vì sao tín hiệu đó đủ (hoặc chưa đủ) để hành động".

## Gợi ý

### Gợi ý 1

Với mỗi tình huống hỏi theo thứ tự: tín hiệu có thật không (loại lỗi dữ liệu trước), có làm chất lượng giảm không (nhãn hoặc proxy), có phiên bản nào tốt hơn đang sẵn sàng không. Chỉ sau đó mới chọn hành động.

### Gợi ý 2

Rollback hợp lý khi có một phiên bản trước đã biết là tốt hơn trên cùng lưu lượng và nguyên nhân gắn với một thay đổi gần đây. Retrain hợp lý khi chất lượng giảm thật mà không có bản trước nào tốt hơn và thế giới đã đổi bền vững.
