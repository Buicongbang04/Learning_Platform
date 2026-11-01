# Hướng làm: distillation so với GRPO và tự học

Bài không có code lời giải: thí nghiệm và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả
của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Model thầy | `Qwen2.5-3B-Instruct` bf16 qua Transformers (PC) | cùng họ, cùng chat template và khung `\boxed` với trò; batch được nên nhanh hơn nhiều so với Ollama |
| Biến duy nhất | nguồn lời giải: thầy (2 mẫu mỗi câu) thay cho trò (4 mẫu mỗi câu, Intermediate 03) | cùng 800 câu train, cùng `select_traces` (tối đa 2 mỗi câu), cùng `SFTConfig`, cùng tập đo 500 câu |
| Lọc | đúng đáp số **và** đúng khung chặt | trò học nguyên văn: lời giải có chữ thừa sau hộp dạy thói quen mà các bài khác phạt |
| Đo thầy | greedy trên cùng 500 câu | trần của distill với lượng dữ liệu này |
| So GRPO | dùng kết quả Advanced 01 (2 seed) | GRPO là phương pháp khác hẳn; ghi rõ khác ở chi phí và dữ liệu (GRPO không cần lời giải mẫu) |
| Giấy phép | ghi rõ: Qwen2.5-3B-Instruct dùng giấy phép `qwen-research` (model card, kiểm 2026-11-01), khác Apache-2.0 của bản 0.5B và 7B | model trò distill từ thầy 3B kế thừa ràng buộc của dữ liệu đó; muốn phát hành thương mại thì đổi thầy (7B Apache-2.0) |

Lỗi hay gặp, có thật ở bản tham chiếu: sinh bằng `trainer.model` ngay sau `trainer.train()` mà quên `model.eval()`. Model còn
ở chế độ train với gradient checkpointing (mặc định của `SFTConfig`), KV cache không được dùng đúng, và từ token thứ hai
model sinh chuỗi ký tự vô nghĩa: lần đo đầu cho accuracy 0.000 với 495 / 500 câu chạm 512 token, dù loss train bình thường
(0.19, độ chính xác token 93%). Luôn đọc vài câu trả lời trước khi tin một con số đo, nhất là con số quá tệ hoặc quá đẹp.

## Kết quả tham chiếu

PC của track (RTX 3060 12GB, dùng chung). Model thầy `Qwen2.5-3B-Instruct` bf16, 800 câu train (cùng Intermediate 03),
2 lời giải mỗi câu ở `temperature` 0.7, batch 32: 1 600 lời giải trong 29.8 phút, VRAM đỉnh 6.75 GiB; đo thầy greedy trên
500 câu thêm 9.7 phút. SFT model trò: 4.5 phút, VRAM đỉnh 1.48 GiB. Tổng khoảng 44 phút chưa kể lần đo model trò.

| Dữ liệu tổng hợp | Thầy 3B (2 mẫu mỗi câu) | Trò 0.5B tự sinh (4 mẫu, Intermediate 03) |
| --- | --- | --- |
| lời giải đúng đáp số | 90.4% | 45.1% |
| đúng đáp số và đúng khung chặt | 60.0% | 30.1% |
| câu có ít nhất một lời giải đúng | 93.8% | 73.6% |
| câu đóng góp mẫu SFT / số mẫu | 577 / 960 | 446 / 735 |
| độ dài TB mẫu giữ | 967 ký tự | 879 ký tự |

Greedy trên 500 câu test ghim, tối đa 512 token:

| Phương pháp | accuracy | boxed_correct | đúng khung | token TB | Hiệu accuracy [CI 95%] so với gốc cùng cách đo |
| --- | --- | --- | --- | --- | --- |
| Model gốc (batch 64) | 0.430 | 0.420 | 0.654 | 302 | |
| Tự học, SFT trên lời giải của chính nó (Intermediate 03) | 0.452 | 0.442 | 0.820 | 301 | +0.022 [−0.018, +0.066] |
| Distill từ thầy 3B | 0.470 | 0.464 | 0.910 | 311 | +0.040 [−0.000, +0.086] |
| GRPO 60 bước, seed 0 (Advanced 01, gốc đo batch 128: 0.436) | 0.482 | 0.480 | 0.970 | 160 | +0.046 [+0.004, +0.088] |
| GRPO 60 bước, seed 1 | 0.468 | 0.468 | 0.976 | 250 | +0.032 [−0.008, +0.074] |
| Thầy `Qwen2.5-3B-Instruct` (tham khảo) | 0.828 | 0.816 | 0.644 | 313 | |

So trực tiếp: distill − tự học +0.018 [−0.026, +0.062]; distill − GRPO seed 0 −0.012 [−0.058, +0.034], seed 1 +0.002
[−0.044, +0.046].

Một kiểm tra nhiễu đáng nhớ: **cùng model gốc**, chỉ đổi batch sinh từ 64 sang 128, accuracy đi từ 0.430 lên 0.436 và **51
trên 500 câu đổi kết quả** (nguyên nhân thường gặp: phép cộng bf16 theo thứ tự khác nhau khi batch khác, greedy rẽ nhánh ở token gần hoà; bản tham chiếu không tách nguyên nhân). Đó là lý do bảng ghi hiệu
của mỗi phương pháp so với model gốc **đo cùng cấu hình**, và lý do không xếp hạng các nhánh khi hiệu nhỏ hơn vài điểm.

## Đọc kết quả

- **Ba nhánh cùng tăng 2 tới 5 điểm, không nhánh nào thắng rõ nhánh nào.** Mọi hiệu đo trực tiếp giữa hai nhánh có
  khoảng tin cậy chứa 0. Kết luận trung thực: ở quy mô 800 câu train, cả ba đều chủ yếu dạy **khung**, và năng lực tăng ít.
- **Thầy giỏi hơn hẳn mà trò chỉ nhích.** Thầy đúng 82.8%, trò sau distill 47%. 960 lời giải không đủ để chuyển năng lực;
  DeepSeek-R1 distill bằng 800 nghìn mẫu. Distill hơn tự học ở **dữ liệu**: độ phủ câu 93.8% so với 73.6%, nên trò thấy lời
  giải đúng của cả những câu nó chưa giải được; với lượng dữ liệu này lợi thế đó chưa thành điểm đo được.
- **Chi phí khác nhau.** Distill tốn thời gian sinh (30 phút với thầy 3B) và cần GPU cho thầy (6.75 GiB); tự học rẻ nhất (13 phút
  sinh, 3 phút SFT); GRPO tốn nhất (39 phút mỗi seed) nhưng không cần lời giải mẫu hay thầy, và cho đúng khung cao nhất.
- **Khung khác nhau theo nguồn**: thầy 3B chỉ đúng khung chặt 64% (hay viết thêm chữ sau hộp), nên bộ lọc bỏ một phần ba lời
  giải đúng của thầy; trò distill đúng khung 91%, cao hơn cả thầy, vì chỉ học từ lời giải đã lọc.
- **Giấy phép là quyết định thật**: trò distill từ 3B mang dữ liệu sinh bởi model `qwen-research`; muốn phát hành thương mại thì
  chọn thầy Apache-2.0 (Qwen2.5-7B-Instruct) và đo lại.

Muốn thấy distill thắng thật: tăng lượng dữ liệu (toàn bộ 7 473 câu train, nhiều mẫu mỗi câu), thầy mạnh hơn (7B), hoặc ghép
distill rồi GRPO (công thức R1: SFT cold start rồi RL).
## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | Mọi test pass |
| So sánh công bằng | 25 | Cùng câu train, cùng bộ lọc, cùng công thức SFT, cùng tập đo và hàm đo cho mọi nhánh SFT; ghi rõ mọi chỗ khác (GRPO là phương pháp khác hẳn) |
| Số đo trung thực | 20 | Bảng `compare_table` có khoảng tin cậy; kết luận không vượt quá nhiễu; có chi phí (thời gian sinh, thời gian train, VRAM) |
| Dữ liệu tổng hợp | 20 | Tỉ lệ giữ, độ phủ câu, độ dài so với trò, ví dụ thật, kiểm nhiễm bẩn, giấy phép model thầy |
| Phân tích và khuyến nghị | 25 | Giải thích vì sao nhánh thắng thắng (dữ liệu mới từ thầy, độ phủ, định dạng), khuyến nghị có điều kiện (có/không có thầy, ngân sách), giới hạn |

Đạt từ 70 điểm. So các nhánh trên tập đo khác nhau, hoặc SFT khác công thức mà không nói, không quá 50 điểm.
