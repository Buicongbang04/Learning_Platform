# Hướng làm: bản đánh giá khả thi tính năng hỏi đáp pháp luật

Bài không có một đáp án duy nhất: hai memo khác khuyến nghị đều có thể đạt điểm cao nếu số liệu đúng và lập luận có điều
kiện. Dưới đây là hai hàm, các con số của bản tham chiếu (chạy ngày 2026-10-30, tokenizer Qwen2.5, giá kiểm cùng ngày),
những điều một memo tốt phải phát hiện, và rubric.

## Hai hàm

- `request_tokens`: `system_tokens + len(encode(question)) + sum(min(len(encode(a)), cap) for a in articles[:k])`, với
  `cap` vô hạn khi `max_article_tokens is None`; ép về `int`.
- `overflow_rate`: tỉ lệ `t + max_new_tokens > context_window`; dấu `>` vì vừa khít vẫn chạy được. Danh sách rỗng ném
  `ValueError` thay vì chia cho 0.

## Số liệu của bản tham chiếu

300 câu hỏi ghim (300 `query-id` đầu của `qrels/test.jsonl`), mỗi request: system prompt 150 token, câu hỏi, 5 điều
(điều đáp án trước, rồi các điều khác cùng văn bản theo thứ tự corpus), câu trả lời 300 token:

- Câu hỏi: trung vị 22 token, dài nhất 45. Điều đáp án (301 điều): trung vị 570 token, trung bình 1 369, 29.2% dài hơn
  1 500 token, 37.9% dài hơn 800 token. Điều đáp án dài hơn hẳn điều luật ngẫu nhiên (trung vị 248 trên 3 000 điều lấy
  ngẫu nhiên): điều được hỏi nhiều là điều dài, nhiều khoản.

| Cắt mỗi điều | Trung vị | p95 | Trung bình | Lớn nhất | Tràn 4 096 |
| --- | --- | --- | --- | --- | --- |
| không | 2 638.5 | 8 700 | 3 689.1 | 8 714 | 31.7% |
| 1 500 | 2 575 | 4 618 | 2 746.1 | 4 629 | 28.0% |
| 800 | 2 185.5 | 3 173 | 2 182.9 | 3 341 | 0.0% |

Chi phí tháng, 10 000 request/ngày, trung bình 2 182.9 token vào (cắt 800), 300 token ra:

| Phương án | USD/tháng | Có cache 150 token system |
| --- | --- | --- |
| Claude Haiku 5.5 | 110.5 | 106.4 |
| Gemini 3.8 Flash (giá tới 2026-12-31) | 828.7 | 798.3 |
| Gemini 3.8 Flash (từ 2027-01-01) | 1 657.3 | 1 596.6 |
| Claude Sonnet 5.5 | 2 209.8 | 2 124.3 |
| Tự host, GPU giả định 0.5 USD/giờ, 24/7 | 360 | 360 |

24.8 triệu token mỗi ngày; ở 400 token/giây (giả định), GPU phải bận 72% thời gian. Độ trễ dự đoán với hệ số GPU rảnh
của lý thuyết: request trung vị khoảng 4.9 giây (TTFT 0.86 giây), p95 khoảng 5.2 giây; decode 300 token chiếm khoảng 4 giây.

## Những điều memo tốt phải thấy

1. **Tràn context im lặng.** Không cắt, gần một phần ba request vượt context 4 096 mặc định của Ollama, và Ollama cắt
   đầu prompt mà không báo lỗi (mất system prompt, chỉ thị trích dẫn). Đây là bug sản phẩm chứ không chỉ chuyện chi phí.
   Cách xử lý: cắt hoặc chia điều theo khoản (module 13), hoặc tăng `num_ctx` (tốn thêm KV cache: bài Basic 02).
2. **Cắt có giá.** Cắt ở 800 token làm 37.9% điều đáp án bị cụt: có thể cắt mất đúng khoản chứa câu trả lời. Memo nên
   nói rõ đánh đổi và đề xuất đo ảnh hưởng (tỉ lệ trả lời đúng trước và sau khi cắt).
3. **Giấy phép.** `qwen2.5:3b` (model của track) dùng `qwen-research`, chỉ phi thương mại. Dùng cho prototype nội bộ thì
   được, cho sản phẩm thì không.
4. **Output chi phối.** 300 token output × giá output gấp 5 lần input tương đương khoảng 1 500 token input: gần ngang cả
   prompt 2 183 token. Rút ngắn câu trả lời vừa giảm tiền vừa giảm độ trễ (decode chiếm khoảng 80% thời gian).
5. **Cache gần như vô dụng ở đây** (giảm khoảng 4%): phần lặp lại chỉ 150 token. Người viết "bật prompt caching để giảm
   chi phí" mà không tính là chưa đọc số.
6. **Tự host không chỉ là giá.** 360 USD/tháng cho GPU 24/7 đắt gấp 3 lần Haiku 5.5, lại cần người vận hành, và với
   72% thời gian bận thì giờ cao điểm sẽ xếp hàng. Tính theo MTok: Haiku 5.5 ở workload này là khoảng 0.148 USD/MTok
   (110.5 USD cho 744.9 triệu token mỗi tháng), còn GPU 0.5 USD/giờ ở 400 token/giây, bận 100%, là 0.347 USD/MTok. **Tăng
   tải không làm tự host thắng**: tải gấp 10 lần thì cần thêm GPU, chi phí tăng theo cùng tỉ lệ. Tự host chỉ rẻ hơn về giá
   khi một GPU 0.5 USD/giờ đạt bền vững trên khoảng 940 token/giây và bận gần hết thời gian (batching nhiều request đồng
   thời, model nhỏ hơn hoặc quantization), hoặc khi giá API tăng. Ở quy mô này, lý do hợp lệ để tự host là dữ liệu không
   được rời hạ tầng, không phải giá.
7. **Số token theo tokenizer khác nhau.** Notebook đếm bằng Qwen2.5; tokenizer của Claude 4.7 trở đi tạo khoảng 30% nhiều
   token hơn (trang giá Anthropic). Memo tốt cộng biên an toàn hoặc đo lại bằng API đếm token của nhà cung cấp.
8. **Chưa đo chất lượng.** Mọi so sánh giá chỉ có nghĩa khi model đạt bộ eval. Khuyến nghị đúng là "làm bộ eval trước,
   rồi chọn model rẻ nhất đạt ngưỡng", không phải "chọn model rẻ nhất".

## Khuyến nghị hợp lý (một trong nhiều)

Làm, theo hai bước: (1) hai tuần prototype với `qwen2.5:3b` local (miễn phí, phi thương mại) để dựng retrieval, prompt
có trích dẫn và bộ eval 300 câu + 50 câu chuyên gia duyệt; (2) nếu đạt ngưỡng, production với model API nhỏ (khoảng
110 USD/tháng, khoảng 145 USD với biên tokenizer 30%), đối chứng một model lớn trên cùng bộ eval. Khuyến nghị sai nếu: model
nhỏ trượt eval; dữ liệu khách hàng không được gửi ra ngoài (khi đó tự host dù đắt hơn); một GPU tự host đạt bền vững trên khoảng 940
token/giây ở 0.5 USD/giờ, hoặc giá API tăng (khi đó tự host rẻ hơn về giá); hoặc
giá khuyến mãi hết hạn đổi thứ tự phương án (Gemini 3.8 Flash tăng gấp đôi từ 2027-01-01).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | `request_tokens`, `overflow_rate` qua test; `MEMO.md` đủ 8 mục, không còn TODO |
| Khối lượng và token | 20 | Số request/ngày, token trung vị và p95 khớp notebook; phát hiện tràn context và nói cái giá của việc cắt |
| Chi phí | 20 | Ít nhất 3 phương án, ngày kiểm giá, giả định tokenizer và GPU ghi rõ; nhận ra output chi phối và cache gần như không giúp; so tự host bằng USD/MTok với điều kiện hoà vốn đúng (thông lượng mỗi GPU, không phải tổng tải) |
| Độ trễ | 10 | TTFT và độ trễ toàn phần có số, từ hệ số tự đo; đề xuất streaming hoặc giới hạn độ dài trả lời |
| Model và giấy phép | 15 | Phát hiện `qwen-research`; khớp model với phần cứng (VRAM) có số |
| Vai trò, rủi ro, đo lường | 10 | Phân việc AI Engineer / ML Engineer / chuyên gia rõ; ít nhất 4 rủi ro có cách đo; bộ eval và ngưỡng trước khi ra mắt |
| Khuyến nghị | 15 | Rõ ràng, có bước tiếp theo, và nêu điều kiện làm khuyến nghị sai |

Đạt từ 70 điểm. Memo chỉ có nhận xét chung mà thiếu số đo của chính notebook không quá 40 điểm.
