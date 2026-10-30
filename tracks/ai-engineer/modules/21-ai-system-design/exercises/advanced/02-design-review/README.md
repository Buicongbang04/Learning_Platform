---
title: Review một design doc AI có lỗi
level: advanced
services: []
files:
  - path: starter/design_under_review.md
    note: Design doc cần review (không sửa)
  - path: starter/claims.yaml
    note: Trích các con số của doc (2 claim mẫu, thêm phần còn lại)
  - path: starter/review.py
    note: 2 hàm TODO, kiểm lại từng con số
  - path: starter/REVIEW.md
    note: Viết nhận xét review ở đây
  - path: tests/test_review.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/21-ai-system-design/exercises/advanced/02-design-review -q
---

## Mục tiêu

AI Engineer lâu năm dành nhiều thời gian **review** thiết kế của người khác hơn là tự viết. Bài này luyện việc đó:
đọc một design doc nghe rất hợp lý, tìm lỗi về an toàn, kiến trúc, đánh giá, vận hành, và kiểm lại mọi con số bằng
code thay vì tin. Làm xong bạn có một checklist review dùng lại được và một bộ kiểm số liệu tự động.

## Đề bài

**Phần cứng:** CPU · ~3 giờ

`starter/design_under_review.md` là design doc (hư cấu) của trợ lý AI trả lời email và chat cho hãng bay VietSky,
600 000 lượt liên hệ mỗi ngày. Nhóm tác giả xin duyệt để triển khai. Doc có nhiều lỗi, từ số học tới những quyết định
có thể làm mất tiền hoặc lộ dữ liệu khách; đề không nói lỗi ở đâu.

1. **`starter/review.py`**: viết hai hàm.
   - `recompute(claim) -> float`: tính lại giá trị đúng của một claim từ `claim["kind"]` và `claim["inputs"]`. Sáu
     kind, input bắt buộc và công thức:

     | kind | inputs bắt buộc | giá trị |
     | --- | --- | --- |
     | `cost_per_1k` | `input_tokens`, `output_tokens`, `input_price`, `output_price` (tuỳ chọn `cached_input_tokens`, `cached_price`) | USD cho 1 000 request; giá USD mỗi triệu token; token cache là một phần của input (như Basic 01) |
     | `monthly_cost` | `cost_per_request`, `requests_per_day`, `days` | tích ba số |
     | `kv_bytes_per_token` | `n_layers`, `n_kv_heads`, `head_dim`, `kv_bits` | $$2 L\, n_{kv}\, d_{head}\, \text{kv\_bits}/8$$ |
     | `weights_bytes` | `n_params`, `bits` | $$N b / 8$$ |
     | `concurrency` | `rps`, `latency_s` | định luật Little $$\lambda W$$ |
     | `gpus` | `peak_rps`, `rps_per_gpu`, `headroom` | $$\lceil \text{peak} (1 + \text{headroom}) / \text{rps\_per\_gpu} \rceil$$ (không cộng dự phòng) |

     Trả `float`. `ValueError` khi kind không có trong bảng hoặc thiếu input bắt buộc.
   - `check_claims(claims, rel_tol=0.1) -> list[dict]`: mỗi claim một dict `{"id", "claimed", "recomputed",
     "rel_error", "ok"}` cùng thứ tự đầu vào, với `rel_error` $$= |\text{claimed} - \text{recomputed}| / |\text{recomputed}|$$
     (nếu giá trị đúng bằng 0 thì là $$|\text{claimed}|$$) và `ok` khi `rel_error <= rel_tol`.
2. **`starter/claims.yaml`**: trích **mọi** con số định lượng ở mục 4 của doc thành claim (đã có 2 claim mẫu). `inputs`
   lấy đúng như doc ghi, `claimed` là kết quả doc đưa ra. Ít nhất 6 claim, phủ ít nhất 5 kind.
3. **`starter/REVIEW.md`**: viết review theo khung có sẵn. Mỗi vấn đề một mục `## Vấn đề N: <tên ngắn>` với mức độ
   (chặn ship / nghiêm trọng / nên sửa), doc nói gì, vì sao sai kèm bằng chứng, và đề xuất cụ thể. Ít nhất 6 vấn đề,
   ít nhất 700 từ, nhắc tên (id) của **mọi** claim mà `check_claims` đánh dấu sai, và một mục kiểm số liệu. Đừng dừng
   ở số học: lỗi đắt nhất của doc này không phải là phép nhân.
4. Làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `recompute` và `check_claims` đúng trên bộ claim của một doc khác ở `tests/fixtures/claims_example.yaml` (bắt đúng 4
  claim sai, cả lỗi quên token cache, dùng attention head thay KV head, chia thay vì nhân, quên headroom), kể cả với
  dung sai chặt hơn; kind lạ hoặc thiếu input ném `ValueError`.
- `claims.yaml` không còn TODO, ≥ 6 claim, ≥ 5 kind; `REVIEW.md` không còn TODO, ≥ 6 mục `## Vấn đề N`, ≥ 700 từ, nhắc
  mọi claim sai.
- Nội dung đạt từ 70/100 theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đọc doc ba lượt, mỗi lượt một câu hỏi. (1) Cái gì có thể làm mất tiền hoặc lộ dữ liệu nếu một người dùng cố tình phá?
Nhìn vào mọi chỗ dữ liệu từ người ngoài đi vào prompt và mọi tool có tác dụng phụ. (2) Kiến thức thay đổi nhanh được
xử lý thế nào, và "đúng" được đo thế nào? (3) Hệ thống hỏng thì sao: nhà cung cấp lỗi, lưu lượng tăng, model trả lời
sai mà không ai biết?

### Gợi ý 2

Một con số đúng phép tính vẫn có thể sai vì nó dùng một con số sai ở trên (lỗi lan truyền): `check_claims` không bắt
được vì inputs lấy từ doc, bạn phải tự lần. So mỗi con số với yêu cầu ở mục 2 của doc: tính lại xong, yêu cầu nào không
còn đạt? Mục độ trễ không có claim trong bảng kind nhưng vẫn có lỗi (xem bài Basic 03).
