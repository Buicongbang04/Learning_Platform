---
title: Design doc - trợ lý mua sắm và CSKH cho sàn thương mại điện tử
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung 10 mục, viết design doc ở đây
  - path: starter/assumptions.yaml
    note: Giả định số liệu của bạn
  - path: starter/estimates.py
    note: 2 hàm TODO, sinh bảng ước lượng cho mục 3
  - path: tests/test_design_doc.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/21-ai-system-design/exercises/advanced/01-design-doc-shopping-assistant -q
---

## Mục tiêu

Viết một design doc hoàn chỉnh như ở vòng system design của vị trí AI Engineer, nhưng có thời gian làm kỹ: đóng khung
bài toán, chọn kiến trúc có lý do, ước lượng bằng số sinh từ code (không tính nhẩm rồi chép tay), thiết kế đánh giá
và vận hành, nói rõ đánh đổi. Sản phẩm là một tài liệu bạn đưa được vào portfolio.

## Đề bài

**Phần cứng:** CPU · ~5 giờ

**Bối cảnh (hư cấu, số liệu giả định).** ChợViệt là sàn thương mại điện tử kiểu Olist (bộ dữ liệu Olist bạn đã gặp ở
track Data Engineer): 3 000 người bán, 400 000 sản phẩm, 2 triệu đánh giá; 1.2 triệu người dùng hoạt động mỗi tháng,
khoảng 200 000 mỗi ngày. Tổng đài nhận 9 000 ticket mỗi ngày, 62% thuộc ba loại: "đơn của tôi đang ở đâu", "đổi trả
thế nào", "sản phẩm này có hợp với tôi không". Ban giám đốc muốn một trợ lý AI trong app làm ba việc: tư vấn sản phẩm
dựa trên catalog và đánh giá, tra trạng thái đơn của chính người dùng, trả lời chính sách đổi trả và vận chuyển (60
trang, sửa khoảng mỗi tháng). Ràng buộc: TTFT p95 ≤ 1.5 giây; ngân sách hạ tầng AI ≤ 15 000 USD/tháng; tên, số điện
thoại, địa chỉ khách không được gửi cho nhà cung cấp bên ngoài khi chưa ẩn; ngày flash sale lưu lượng gấp 10 lần
ngày thường; đội có 4 kỹ sư, chưa ai vận hành GPU.

Làm bốn việc:

1. **`starter/assumptions.yaml`**: điền mọi giả định số, mỗi số một chú thích nguồn hoặc lý do. Giá API phải là giá
   bạn đã kiểm trên trang giá chính thức (ghi ngày) hoặc ghi rõ GIẢ ĐỊNH; tương tự giá thuê GPU và thông lượng mỗi GPU.
   Thông số model (`n_layers`, `n_kv_heads`, `head_dim`) lấy từ `config.json` thật của model bạn chọn.
2. **`starter/estimates.py`**: viết `estimate(assumptions) -> dict` trả đúng các khoá trong `ORDER`, định nghĩa:
   - `requests_per_day` $$= \text{dau} \cdot \text{requests\_per\_user\_per\_day}$$ (làm tròn về `int`);
     `peak_rps` $$= \frac{\text{requests\_per\_day}}{86\,400} \cdot \text{peak\_to\_avg}$$;
     `peak_concurrency` $$= \text{peak\_rps} \cdot \text{e2e\_latency\_s}$$ (định luật Little).
   - `api_cost_per_request`: như bài Basic 01, `cached_input_tokens` (tuỳ chọn, mặc định 0) là một phần của
     `input_tokens`, tính giá `cached_input`; `api_cost_per_1k` nhân 1 000; `api_monthly_usd` nhân
     `requests_per_day` và 30.
   - `weights_gib` $$= \frac{N \cdot \text{weight\_bits}/8}{2^{30}}$$; `kv_kib_per_token` $$= \frac{2 L\, n_{kv}\, d_{head}\, \text{kv\_bits}/8}{1024}$$.
   - `seqs_per_gpu`: như bài Basic 02, $$\left\lfloor \frac{(\text{vram\_gib} - \text{reserve\_gib}) \cdot 2^{30} - \text{weights}}{\text{KV}_{\text{token}} \cdot \text{context\_tokens}} \right\rfloor$$.
   - `gpus_for_memory` $$= \lceil \text{peak\_concurrency} / \text{seqs\_per\_gpu} \rceil$$;
     `gpus_for_throughput` $$= \lceil \text{peak\_rps} (1 + \text{headroom}) / \text{rps\_per\_gpu} \rceil$$;
     `gpus` là số lớn hơn (khác bài Intermediate 01, ở đây **không** cộng GPU dự phòng N+1: bàn chuyện dự phòng trong
     mục 6 và 9 của doc); `self_host_monthly_usd` $$= \text{gpus} \cdot \text{usd\_per\_gpu\_hour} \cdot 730$$.
   - Số nguyên (`requests_per_day`, `seqs_per_gpu`, ba số GPU) trả `int`. Ném `ValueError` khi
     `cached_input_tokens > input_tokens` hoặc `seqs_per_gpu` bằng 0 (model không vừa GPU).

   Và `render_table(est) -> str`: dòng đầu `| Chỉ số | Giá trị |`, dòng hai `| --- | --- |`, rồi mỗi khoá theo thứ tự
   `ORDER` một dòng `| <khoá> | <giá trị> |`; số nguyên viết `f"{v:,}"`, `api_cost_per_request` viết `f"{v:.6f}"`, số
   thực khác viết `f"{v:,.2f}"`; mỗi dòng kết thúc bằng `\n`.
3. **`starter/DESIGN.md`**: viết design doc theo khung 10 mục có sẵn (giữ nguyên tiêu đề `## 1.` tới `## 10.`). Mục 3
   chứa nguyên văn bảng `render_table(estimate(assumptions.yaml))` rồi **đọc** bảng: API hay self-host và vì sao, nút
   thắt nằm ở đâu, ngày flash sale thay đổi gì. Ít nhất 2 sơ đồ mermaid, ít nhất 1 500 từ.
4. Làm phần trắc nghiệm của bài trong app.

Không có đáp án duy nhất. Chọn self-host, API, hay lai đều được nếu số liệu và lý do đứng vững. Rubric chấm ở
`SOLUTION.md` trong thư mục lời giải: đọc sau khi viết xong bản đầu.

## Tiêu chí đạt

- `estimate` và `render_table` đúng trên giả định của case ngân hàng ở `tests/fixtures/assumptions_bank.yaml` (bảng
  13 dòng khớp từng ký tự), kể cả khi không có prompt caching; đầu vào sai ném `ValueError`.
- `DESIGN.md` không còn TODO, đủ 10 mục, ≥ 1 500 từ, ≥ 2 sơ đồ mermaid, và chứa đúng bảng sinh từ `assumptions.yaml`
  của bạn (sửa giả định thì phải sinh lại bảng).
- Nội dung đạt từ 70/100 theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Bắt đầu từ mục 1 và 2, không phải từ sơ đồ. Viết ra người dùng là ai, ba loại yêu cầu khác nhau ra sao (loại nào cần
dữ liệu cá nhân, loại nào cần đúng tuyệt đối, loại nào cần sáng tạo), chỉ số kinh doanh nào sẽ thay đổi nếu trợ lý
tốt. Mỗi loại yêu cầu có thể cần một kiến trúc khác nhau (mục 2 lý thuyết): không phải mọi thứ đều là agent.

### Gợi ý 2

Sinh bảng bằng một dòng `uv run python -c "import yaml, estimates; print(estimates.render_table(estimates.estimate(yaml.safe_load(open('assumptions.yaml')))))"`
chạy trong `starter/`. PyYAML đọc `7.6e9` thành chuỗi: viết `7.6e+9` hoặc `7600000000`. Đọc bảng với con mắt nghi
ngờ: `gpus_for_memory` nhỏ mà `gpus_for_throughput` lớn nghĩa là gì? Chi phí model chiếm bao nhiêu phần ngân sách,
phần còn lại đi đâu (embedding catalog, vector DB, người chấm eval, observability)?
