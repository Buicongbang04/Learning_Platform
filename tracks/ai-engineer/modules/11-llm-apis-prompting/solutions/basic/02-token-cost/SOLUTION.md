# Lời giải: máy tính chi phí token

## Cách làm

- `request_cost`: kiểm token không âm và giá cache có mặt khi cần, cộng bốn tích rồi chia $$10^6$$; batch nhân với
  `1 - batch_discount`.
- `workload_cost`: phần prompt ngoài prefix là input thường; dựng `Usage` cho request trúng cache (prefix là
  `cache_read_tokens`) và trượt cache (prefix là `cache_write_tokens`), lấy trung bình theo `cache_hit_rate`, chỉ tính
  nhánh có trọng số dương, nhân số request.
- `cache_breakeven`: từ $$p_{\text{cw}} + n\,p_{\text{cr}} \le (1 + n)\,p_{\text{in}}$$ suy ra
  $$n \ge \frac{p_{\text{cw}} - p_{\text{in}}}{p_{\text{in}} - p_{\text{cr}}}$$, lấy `math.ceil(x - 1e-12)`; tử số không dương thì 0, mẫu số
  không dương thì `ValueError`.
- `rank_models`: gọi `workload_cost` cho từng model, `sorted(key=(chi phí, tên))`.

Kiểm tay ví dụ của test có cache: phần riêng 300 token vào và 100 token ra tốn $$\frac{300 \cdot 3 + 100 \cdot 15}{10^6} = 0.0024$$
USD; prefix 1 200 token tốn 0.00036 khi đọc, 0.0045 khi ghi. Trung bình
$$0.0024 + 0.9 \cdot 0.00036 + 0.1 \cdot 0.0045 = 0.003174$$ USD mỗi request, 317.4 USD cho 100 000 request, so với 600 USD
không cache: prefix chiếm 80% prompt nên cache cắt gần một nửa hoá đơn.

## Vì sao các lựa chọn này

- **Giá là tham số, test dùng giá giả định**: giá thật đổi theo quý (bảng ở mục 3 lý thuyết ghi ngày kiểm). Code chi
  phí viết cứng giá sẽ âm thầm sai, còn test dựa trên giá thật sẽ đỏ mỗi lần nhà cung cấp đổi giá.
- **Tách `input_tokens` khỏi token cache**: đúng cách các API báo `usage` (Anthropic có `input_tokens`,
  `cache_creation_input_tokens`, `cache_read_input_tokens` riêng; OpenAI báo `cached_tokens` là một phần của
  `prompt_tokens`, nên phải trừ ra trước khi đưa vào hàm này).
- **Trừ epsilon trước khi lấy trần**: tỉ số đúng bằng số nguyên là trường hợp thường gặp (giá là bội của nhau);
  không có epsilon, sai số dấu phẩy động biến 4 thành 5.

## Đọc kết quả

Ba đòn bẩy chi phí theo thứ tự hiệu quả thường gặp: chọn model rẻ hơn mà vẫn đạt ngưỡng chất lượng (chênh 10 tới 100
lần), cache prefix chung (cắt phần lớn chi phí input khi prefix dài và được hỏi lại trong thời gian sống của cache),
batch cho việc không cần trả lời ngay (giảm 50%). Token ra đắt gấp khoảng 5 tới 8 lần token vào ở các bảng giá kiểm ở mục 3 lý thuyết,
nên prompt bắt model trả lời dài (CoT, JSON thừa trường) đắt hơn nhiều so với độ dài phần chữ của nó.

## Bẫy thường gặp

- Tính `cached_prefix_tokens` hai lần: vừa là input thường vừa là cache read.
- Cho rằng cache luôn trúng: cache có thời gian sống (5 phút hoặc 1 giờ ở Anthropic, tự động và ngắn ở OpenAI);
  lưu lượng thưa thì gần như mọi request là lần ghi, và với giá ghi 2 lần input, cache **làm đắt hơn**.
- Áp batch discount cho cả request cần trả lời ngay: Batch API trả kết quả trong tối đa 24 giờ.
