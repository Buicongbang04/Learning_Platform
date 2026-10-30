# Lời giải: máy tính chi phí inference

## Cách làm

Mọi hàm quy về một hàm phụ `_cost(n_in, n_out, price, n_cached)`:

1. Chọn bảng giá: có `long_context` và `n_in > threshold` thì dùng bảng giá con, ngược lại dùng bảng chính.
2. Giá cache: `tier.get("cached_input", tier["input"])` trên **bảng đã chọn**.
3. Cộng: $$\frac{(n_{in} - n_{cached})\,p_{in} + n_{cached}\,p_{cached} + n_{out}\,p_{out}}{10^6}$$.

`request_cost` kiểm đầu vào (không âm, `n_cached <= n_in`) rồi gọi `_cost`. `monthly_cost` gọi `_cost` với
`n_cached = n_in * cache_hit` để **không làm tròn**: `cache_hit` là tỉ lệ trung bình trên nhiều request, 1 001 token
với 50% cache là 500.5 token cache theo kỳ vọng. Làm tròn từng request rồi nhân 300 000 request khuếch đại sai số.

`self_hosted_cost_per_mtok` là $$\frac{g}{r \cdot 3600 \cdot u} \cdot 10^6$$: số token sinh được mỗi giờ là
$$r \cdot 3600 \cdot u$$ vì GPU chỉ "làm ra token" trong phần thời gian bận, nhưng bạn trả tiền cả giờ.

`choose_model` lọc theo hai ràng buộc rồi giữ ứng viên có chi phí nhỏ **hẳn** (`<`), nên bằng chi phí thì ứng viên đứng
trước thắng. Độ trễ $$\text{TTFT} + n_{out}/r$$ là mô hình ở mục 5 lý thuyết; bài Intermediate 02 đo nó thật.

## Câu hỏi cuối đề

Giá kiểm 2026-10-30 (mục 5 lý thuyết), 10 000 request/ngày, 2 000 token input, 500 token output, 30 ngày:

| Model | Không cache | 1 500 token đầu từ cache (`cache_hit=0.75`) | Giảm |
| --- | --- | --- | --- |
| Claude Sonnet 5.5 (2 / 10, cache 0.10) | 2 700 USD | 1 845 USD | 31.7% |
| gpt-6-luna (0.10 / 0.50, cache 0.01) | 135 USD | 94.5 USD | 30.0% |

Hai điều đáng để ý:

- Cache giảm 75% số token input tính giá đầy đủ nhưng hoá đơn chỉ giảm khoảng 30%: **output chiếm phần lớn chi phí**
  (500 token output × 5 lần giá = 2 500 "đơn vị input", lớn hơn 2 000 token input). Muốn giảm tiếp phải rút ngắn
  output hoặc chuyển việc dễ sang model nhỏ.
- Chênh lệch 20 lần giữa hai model lớn hơn mọi tối ưu cache. Nhưng con số này chỉ có nghĩa khi model nhỏ **đạt chất
  lượng** trên bộ eval của bạn: đó là lý do `choose_model` lọc chất lượng trước rồi mới so giá.

Mô hình này bỏ qua phí ghi cache (Anthropic tính 1.25 lần giá input cho lần ghi cache 5 phút). Với 10 000 request
mỗi ngày, cache gần như luôn "nóng" nên phí ghi không đáng kể; với vài request mỗi giờ, cache hết hạn giữa hai request
và có thể làm hoá đơn **tăng**.

## Bẫy thường gặp

- Coi `n_cached` là token **thêm vào** `n_in` thay vì một phần của nó: tính hai lần phần cache.
- Chỉ tính giá dài cho phần vượt ngưỡng. Trang giá nói rõ request có prompt vượt ngưỡng trả giá cao hơn cho cả request.
- So `>=` với ngưỡng: prompt đúng bằng 100 000 token vẫn là giá thường.
- `int(n_in * cache_hit)` trong `monthly_cost`.
- Quên `utilization`: tự host luôn trông rẻ trên giấy vì giả định GPU bận 100%, điều gần như không bao giờ xảy ra với
  tải thật dao động theo giờ trong ngày.
- So giá mỗi MTok giữa hai model khác tokenizer: cùng văn bản tiếng Việt có thể chênh 1.7 lần số token (mục 5).
