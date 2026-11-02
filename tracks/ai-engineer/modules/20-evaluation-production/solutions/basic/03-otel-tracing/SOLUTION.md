# Lời giải: trace một pipeline RAG bằng OpenTelemetry

## Cách làm

- `make_provider`: `TracerProvider(resource=Resource.create({"service.name": ...}),
  sampler=ParentBased(TraceIdRatioBased(ratio)))`, thêm `SimpleSpanProcessor(exporter)`. Không gọi
  `trace.set_tracer_provider`: provider toàn cục chỉ đặt được một lần mỗi tiến trình, nên code thư viện và test phải nhận
  provider (hoặc tracer) làm tham số.
- `JsonlSpanExporter.export`: mở tệp ở chế độ `"a"` (nối thêm, vì `SimpleSpanProcessor` gọi `export` một lần cho mỗi span),
  `ensure_ascii=False` để giữ chữ tiếng Việt, id in hex có số 0 đứng đầu, `parent` của span gốc là `None`.
- `traced_answer`: ba `with tracer.start_as_current_span(...)` lồng nhau đúng thứ tự; chi phí tính trong span `llm.chat`
  và gắn lên cả span gốc để dashboard cộng theo request mà không cần join.

## Vì sao như vậy

- **ParentBased(TraceIdRatioBased)** quyết định ở span gốc theo trace id, span con theo cha: trace luôn đủ hoặc không có gì.
  Lấy mẫu từng span độc lập sẽ cho trace cụt (có span LLM mà không có span gốc), không debug được.
- **Lỗi**: `start_as_current_span` mặc định ghi exception thành event và đặt status `ERROR` khi ngoại lệ đi qua nó; ngoại lệ
  đi qua cả span con lẫn span gốc nên cả hai được đánh lỗi, còn `rag.retrieve` đã đóng trước đó vẫn `UNSET`. Không nuốt lỗi:
  trace là để quan sát, không được đổi hành vi của dịch vụ.
- **PII**: che trước khi gắn vào thuộc tính. Exporter, backend và mọi người có quyền đọc trace đều thấy thuộc tính; che ở
  backend là quá muộn.
- **Tên thuộc tính GenAI** theo semantic conventions để backend (Langfuse, Phoenix, Grafana) tự hiểu token và model.
- **Chi phí**: đo bằng lời giải này, một request ba span tốn khoảng 0.13 ms khi ghi vào bộ nhớ và 0.31 ms khi ghi tệp đồng
  bộ, so với khoảng 0.03 ms khi trace bị lấy mẫu bỏ (mục 3 lý thuyết). Ở production dùng `BatchSpanProcessor` để ghi/gửi ở
  luồng nền.

## Lỗi hay gặp

- Gọi `tracer.start_span` (không "as current"): span không thành span hiện hành, span tạo sau không nhận nó làm cha.
- Ghi đè tệp (`"w"`) trong `export`: chỉ còn span cuối.
- Đặt `TraceIdRatioBased` không bọc `ParentBased`: span con được lấy mẫu lại độc lập theo cùng trace id nên thường vẫn
  khớp, nhưng mất đảm bảo khi cha đến từ tiến trình khác với quyết định khác.
- Gắn nguyên câu hỏi vào thuộc tính rồi định "lọc sau".
- `json.dumps` thuộc tính kiểu tuple ra list mà test vẫn so được; nhưng ghi `str(attributes)` thì không đọc lại được.
