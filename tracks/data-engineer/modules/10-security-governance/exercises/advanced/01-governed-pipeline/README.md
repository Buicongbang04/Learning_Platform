---
title: Governed pipeline - quality gate, masking PII và OpenLineage events
level: advanced
services: []
files:
  - path: starter/pipeline.py
    note: Tự thiết kế phần thân, giữ nguyên chữ ký hàm run
  - path: tests/test_pipeline.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/advanced/01-governed-pipeline -q
---

## Mục tiêu

Ghép ba lớp governance vào **một** job thật: kiểm tra chất lượng có quality gate, che PII trước khi publish,
và phát lineage event theo mô hình OpenLineage để catalog (Marquez, DataHub) dựng được graph và lịch sử chạy.

## Đề bài

Viết `run(orders, customers, key, emit, run_id=None, max_invalid_ratio=0.1)` trong `starter/pipeline.py`.

**Đầu vào**: `orders` (`order_id`, `customer_id`, `order_status`, `price`) và `customers` (`customer_id`,
`customer_unique_id`, `email`, `cpf`, `customer_state`) dạng pandas DataFrame. `emit` là callable nhận một
dict (event). `key` là secret cho HMAC.

**Xử lý**:

1. Phát event `START` trước khi làm gì khác.
2. Quality check trên `orders`: `order_id` không null và unique, `price > 0`, `order_status` thuộc
   `ORDER_STATUSES`. Dòng vi phạm vào `quarantine`. Nếu tỉ lệ dòng lỗi **lớn hơn** `max_invalid_ratio`:
   phát event `FAIL` rồi raise `QualityGateError`.
3. Join với `customers`, tạo `customer_key = HMAC-SHA256(key, customer_unique_id)` (hex), bỏ mọi cột PII
   (`email`, `cpf`, `customer_unique_id`, `customer_id`). Output có đúng các cột `OUTPUT_COLUMNS`.
4. Phát event `COMPLETE`, trả `(output_df, quarantine_df)`.
5. Lỗi bất ngờ (exception khác) cũng phải phát `FAIL` rồi raise lại.

**Event** (dict, JSON-serializable) theo OpenLineage RunEvent rút gọn:

```json
{
  "eventType": "START | COMPLETE | FAIL",
  "eventTime": "2024-05-01T02:10:00+00:00",
  "producer": "...",
  "run": {"runId": "<uuid, giống nhau cho mọi event của một lần chạy>", "facets": {}},
  "job": {"namespace": "olist", "name": "build_orders_enriched"},
  "inputs": [{"namespace": "olist", "name": "raw.orders"}, {"namespace": "olist", "name": "raw.customers"}],
  "outputs": [{"namespace": "olist", "name": "mart.orders_enriched", "facets": {...}}]
}
```

- `COMPLETE`: output có facet `schema` (`{"fields": [{"name", "type"}]}` đúng các cột output) và facet
  `dataQualityMetrics` (`{"rowCount": số dòng output, "invalidRowCount": số dòng quarantine}`).
- `FAIL`: `run.facets.errorMessage = {"message": "...", "programmingLanguage": "python"}`.
- Không event nào được chứa giá trị PII (email, cpf, `customer_unique_id`).

## Tiêu chí đạt

- Tests trong `tests/` pass.
- Thiết kế được giải thích trong docstring hoặc comment: vì sao mask trước khi publish, vì sao FAIL phải
  được phát cả khi exception lạ, chọn ngưỡng gate thế nào.
- Event JSON-serializable, `eventTime` là ISO 8601 có timezone.

## Gợi ý

### Gợi ý 1

Bọc phần thân bằng `try/except` ở mức `run`: `emit(START)` → `try: ... emit(COMPLETE)` →
`except Exception as e: emit(FAIL); raise`. Viết một hàm `_event(type, ...)` dùng chung để ba loại event
không lệch cấu trúc.

### Gợi ý 2

Có thể tái dùng pandera (bài basic/03) cho quality check, hoặc mask boolean bằng pandas. Kiểu cột cho facet
schema: `str(df[col].dtype)`. `datetime.now(timezone.utc).isoformat()` cho `eventTime`.
