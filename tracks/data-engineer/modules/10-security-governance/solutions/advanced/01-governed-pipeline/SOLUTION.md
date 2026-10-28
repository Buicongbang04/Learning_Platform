# Hướng dẫn: Governed pipeline

Bài này không có một đáp án duy nhất. Dưới đây là hướng làm, các quyết định thiết kế và rubric chấm.

## Hướng làm

1. **Một hàm `_event(kind, run_id, outputs=None, error=None)`** sinh dict theo OpenLineage RunEvent:
   `eventType`, `eventTime` (`datetime.now(timezone.utc).isoformat()`), `producer`, `run`, `job`, `inputs`,
   `outputs`. Ba loại event dùng chung hàm nên không lệch cấu trúc.
2. **Khung `run`**:

   ```python
   run_id = run_id or str(uuid.uuid4())
   emit(_event("START", run_id))
   try:
       good, quarantine = quality_check(orders)          # mask boolean hoặc pandera lazy
       if len(quarantine) / max(len(orders), 1) > max_invalid_ratio:
           raise QualityGateError(...)
       out = mask_and_join(good, customers, key)         # HMAC customer_unique_id, bỏ cột PII
       emit(_event("COMPLETE", run_id, outputs=[{... "facets": {"schema": ..., "dataQualityMetrics": ...}}]))
       return out, quarantine
   except Exception as exc:
       emit(_event("FAIL", run_id, error=f"{type(exc).__name__}: {exc}"))
       raise
   ```

3. **Quality check**: `order_id.isna() | order_id.duplicated(keep=False) | ~(price > 0) | ~status.isin(...)`.
   `keep=False` để quarantine **cả hai** dòng trùng: không biết dòng nào đúng thì không publish dòng nào.
4. **Mask**: `merge(..., validate="many_to_one")` để bắt lỗi khoá trùng ở `customers`; `customer_key` bằng
   HMAC-SHA256 có key (join được, không brute-force được); chọn đúng `OUTPUT_COLUMNS` (allow-list, không
   phải deny-list: cột mới thêm ở nguồn không tự lọt ra output).

## Quyết định thiết kế cần cân nhắc

| Quyết định | Lựa chọn | Đánh đổi |
| --- | --- | --- |
| Quarantine hay fail cả batch | Quarantine + ngưỡng | Ngưỡng thấp: nhiều false alarm; cao: số liệu thiếu lặng lẽ |
| Mask ở đâu | Trước khi ghi `mart` | Mask càng sớm càng thu hẹp vùng chứa PII; nhưng mất khả năng debug trên dữ liệu thô |
| Allow-list cột output | Có | An toàn hơn deny-list, phải cập nhật khi muốn thêm cột |
| Emit FAIL trong `except Exception` | Có | Không có FAIL, catalog thấy run "treo" ở START mãi; vẫn `raise` để orchestrator retry/alert |
| Error message trong event | Chỉ loại lỗi + mô tả | Không đưa giá trị dòng lỗi vào event vì có thể chứa PII |
| `emit` lỗi (backend lineage chết) | Nên bắt và log, không làm hỏng job | Lineage là phụ trợ; đừng để nó dừng pipeline chính |

Mở rộng nếu muốn: dùng thư viện `openlineage-python` và Marquez thật; thêm facet `columnLineage`; ghi
`quarantine` ra bảng riêng có retention ngắn và quyền hạn chế.

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Tests pass | 3 |
| Event đúng cấu trúc, một `runId` cho mọi event, `FAIL` phát cả khi exception lạ | 2 |
| Quality gate đúng (trùng khoá quarantine cả hai dòng, ngưỡng so sánh `>`) | 1.5 |
| Output dùng allow-list, PII không có trong output lẫn event, HMAC có key | 1.5 |
| Code rõ ràng: hàm nhỏ (`_event`, check, mask), có giải thích quyết định trong comment/docstring | 1 |
| Xử lý biên: DataFrame rỗng (chia cho 0), `emit` lỗi, khoá trùng ở `customers` | 1 |
