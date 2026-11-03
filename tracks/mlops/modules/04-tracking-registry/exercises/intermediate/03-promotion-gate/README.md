---
title: Cổng promotion trên registry - quyết định được ghi lại trong version
level: intermediate
services: []
files:
  - path: starter/gate.py
    note: 3 hàm TODO
  - path: tests/test_gate.py
    note: Không sửa
run:
  - docker compose -f setup/mlops/compose.yaml up -d --build --wait
  - uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/intermediate/03-promotion-gate -q
---

## Mục tiêu

Nối hàm quyết định (bài Basic 02) với registry thật: lấy số đo của challenger và champion từ run, kiểm lineage, quyết định,
ghi quyết định cùng lý do lên version, và chỉ khi đạt mới dời alias. Một năm sau, ai mở version trong UI cũng thấy vì sao nó
được (hoặc không được) lên production.

## Đề bài

Cần stack `setup/mlops` đang chạy (test tự skip và nêu lệnh bật nếu chưa). Test dùng tên có hậu tố ngẫu nhiên và dọn khi xong;
bài này không phụ thuộc lời giải Basic 02: hàm quyết định `decide(challenger, champion, policy)` được truyền vào, trả đối
tượng có `.promote` và `.reasons`. Trong `starter/gate.py`, với `client = MlflowClient(<uri server>)`:

1. `collect_metrics(client, model_name, version) -> dict`: đọc từ run sinh ra version.
   Run có metric `mae`, `latency_p95_ms`, và mỗi slice có `mae_slice.<tên>` và `n_slice.<tên>`. Trả
   `{"mae", "latency_p95_ms", "slices": {tên: {"mae", "n"}}}` (`n` kiểu `int`).
2. `lineage_problems(client, model_name, version) -> list[str]`: lý do về lineage dựa trên tag của run. `git_dirty ==
   "true"` là một lý do (câu chữ chứa `git_dirty`); thiếu tag `data_version` hoặc `git_commit` là lý do (câu chữ chứa tên tag
   thiếu, mỗi tag một lý do). Đủ tag và sạch thì trả `[]`.
3. `gate_and_promote(client, model_name, challenger_version, decide, policy=None, alias="champion") -> dict`: trả
   `{"promoted": bool, "reasons": list[str], "version": int}`, làm theo thứ tự:
   - challenger đã giữ alias thì `ValueError`;
   - gọi `decide(challenger_metrics, champion_metrics_or_None, policy)` (truyền nguyên `policy`);
   - ghép lý do của `decide` với `lineage_problems`; có lý do lineage thì không promote dù `decide` nói có;
   - ghi lên version challenger các tag `promotion.decision` (`promoted`/`rejected`), `promotion.reasons` (JSON list, đúng
     bằng `reasons` trả về) và `promotion.compared_to` (số version champion dạng chuỗi, hoặc `none`);
   - chỉ khi promote: đặt alias, ghi `previous_<alias>` lên challenger và `superseded_by` lên champion cũ (chỉ khi có
     champion cũ). Từ chối thì alias và mọi tag khác của champion giữ nguyên.

## Tiêu chí đạt

- Model đầu tiên (chưa có champion) được promote và `decide` nhận `None` cho champion.
- Model tốt hơn được promote; tag quyết định, lý do, version so sánh và đường lui đều có trên registry.
- Model tốt hơn tổng nhưng xấu đi ở slice `airport` bị từ chối, lý do nêu `airport`, alias đứng yên.
- Model tốt hơn nhưng train từ cây thư mục bẩn bị từ chối, lý do nêu `git_dirty`, và vẫn có tag `rejected`.
- Không còn model hay experiment mang tiền tố `mlops-ex-` sau khi chạy.

## Gợi ý

### Gợi ý 1

`client.get_model_version(name, str(v)).run_id` dẫn tới `client.get_run(run_id).data.metrics` và `.data.tags`. Metric chỉ là
`float`; ép `n` về `int` khi dựng kết quả.

### Gợi ý 2

Tag của MLflow chỉ chứa chuỗi, nên danh sách lý do cần `json.dumps(..., ensure_ascii=False)`. Ghi tag quyết định **trước**
khi dời alias: nếu bước dời alias lỗi, bản ghi "đã quyết định promote" vẫn còn để điều tra.
