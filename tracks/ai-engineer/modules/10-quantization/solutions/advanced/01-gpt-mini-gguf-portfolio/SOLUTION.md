# Hướng làm: GPT mini tiếng Việt từ PyTorch tới GGUF và llama.cpp

Bài không có một đáp án duy nhất; dưới đây là hướng làm, các quyết định cần cân nhắc, kết quả của bản tham chiếu (giữ ngoài
repo) và rubric.

## Ba hàm được chấm

- `gguf_tensor_name`: bảng ánh xạ cố định; `lm_head.weight` trả `None` vì GPT mini dùng chung trọng số với `tok_emb`, và
  llama.cpp kiến trúc `gpt2` tự dùng lại `token_embd` khi tệp không có tensor `output`. Ghi cả hai tensor là lãng phí đúng một
  ma trận lớn nhất của model (3.07 triệu trên 13.8 triệu tham số ở cấu hình PC).
- `export_gguf`: `gguf.GGUFWriter(path, "gpt2")`, các `add_*` theo đặc tả, token sắp theo id lấy từ `tokenizer.to_str()`, merge
  dạng `"a b"`, `add_add_bos_token(False)` (tokenizer không có token đặc biệt), rồi `add_tensor` với mảng numpy cùng shape
  PyTorch: gguf-py ghi shape đảo ngược (`ne0` là chiều trong cùng), đúng thứ llama.cpp mong đợi cho ma trận `(out, in)`. Bản f16 chỉ
  đổi ma trận 2 chiều; norm và bias giữ f32 (llama.cpp yêu cầu).
- `sequence_nll`: log-softmax ổn định số trong float64 (trừ max theo hàng), tổng NLL của target. Cộng NLL của `n_new` target cuối
  mỗi cửa sổ trượt (giống `evaluate_nll` module 05), chia số ký tự nhân $$\ln 2$$.

## Kết quả bản tham chiếu

Hai checkpoint của module 05 (cấu hình PC: 6 tầng, `n_embd` 384, 13.8 triệu tham số; cấu hình laptop: 4 tầng, `n_embd` 256, 5.3
triệu tham số), đủ 100 bài validation (664 568 ký tự, 190 923 token). Đo trên PC ngày 2026-11-01, `llama-cpp-python` 0.3.36 bản
CPU, 4 luồng, máy đang bận (load trung bình 8-18 trên 36 luồng); tốc độ sinh là **một** lần sinh 200 token greedy từ "Hà Nội là",
nên chỉ so được thô.

Kiểm tệp: tokenizer của llama.cpp cho đúng 26 token id như tokenizer gốc trên một câu tiếng Việt có dấu và số; bản f32 chạy bằng
llama.cpp cho bpc 1.5395 (laptop) và 1.3472 (PC), trùng PyTorch tới 4 chữ số. llama.cpp dùng GELU xấp xỉ tanh còn GPT mini dùng GELU
chính xác: trên 20 001 token đầu, đổi sang dạng tanh chỉ làm bpc PyTorch lệch $$10^{-5}$$.

| Định dạng | Laptop: MB | Laptop: bpc (Δ) | PC: MB | PC: bpc (Δ) | PC: token/giây |
| --- | --- | --- | --- | --- | --- |
| f32 | 21.37 | 1.5395 | 55.55 | 1.3472 | 462 |
| f16 | 10.85 | 1.5395 (+0.0000) | 27.97 | 1.3472 (+0.0000) | 1 012 |
| `Q8_0` | 6.11 | 1.5399 (+0.0004) | 15.34 | 1.3475 (+0.0003) | 801 |
| `Q6_K` | 4.85 | 1.5412 (+0.0017) | 14.48 | 1.3478 (+0.0006) | 897 |
| `Q5_K_M` | 4.56 | 1.5422 (+0.0027) | 12.23 | 1.3495 (+0.0023) | 1 024 |
| `Q4_K_M` | 4.28 | 1.5458 (+0.0063) | 11.55 | 1.3509 (+0.0037) | 1 102 |
| `Q4_0` | 4.04 | 1.5502 (+0.0107) | 10.03 | 1.3581 (+0.0109) | 1 387 |
| `Q3_K_M` | 3.95 | 1.5540 (+0.0145) | 10.52 | 1.3543 (+0.0071) | 1 268 |
| `Q2_K` | 3.52 | 1.5991 (+0.0596) | 9.56 | 1.3637 (+0.0165) | 1 178 |

(Nguồn: `logs/gguf_eval_full.log`, `logs/gguf_types.log` của bản tham chiếu.)

Kiểu thật của các ma trận (đọc bằng `gguf.GGUFReader`) giải thích hai điều lạ của cột PC:

| Tệp | Laptop (`n_embd` 256) | PC (`n_embd` 384) |
| --- | --- | --- |
| `Q4_K_M` | 12 `Q4_K`, 5 `Q6_K` | 16 `Q5_0`, 4 `Q4_K`, 2 `Q6_K`, 3 `Q8_0` |
| `Q3_K_M` | 4 `Q3_K`, 10 `Q4_K`, 2 `Q5_K`, 1 `Q6_K` | 10 `Q5_0`, 2 `Q5_1`, 6 `Q4_K`, 6 `Q4_0`, 1 `Q8_0` |
| `Q2_K` | 4 `Q2_K`, 12 `Q3_K`, 1 `Q6_K` | 18 `Q4_0`, 6 `Q3_K`, 1 `Q8_0` |

k-quant làm việc theo siêu khối 256 phần tử trên mỗi hàng. Ở cấu hình PC mọi ma trận có 384 cột (trừ `ffn_down` 1 536 cột) không
chia hết cho 256, llama.cpp in "falling back" và dùng kiểu legacy (`Q5_0`, `Q4_0`, `Q8_0`). Vì vậy tệp "Q4_K_M" của PC **lớn hơn**
`Q4_0`, còn "Q2_K" của PC thật ra phần lớn là 4 bit nên bpc chỉ tăng 0.017 (so với 0.060 ở laptop). Tên tệp là ý định, không phải
nội dung. Qwen2.5-0.5B (hidden 896) gặp đúng chuyện này (bài Advanced 02).

Đặt cạnh các phương pháp tự cài (cùng validation, chỉ lượng tử hoá các lớp Linear trong khối, embedding giữ float32):

| Phương pháp, 4 bit | Laptop Δbpc | PC Δbpc |
| --- | --- | --- |
| RTN nhóm 32 | +0.0133 | +0.0144 |
| GPTQ nhóm 32 | +0.0060 | +0.0076 |
| AWQ nhóm 32 | +0.0127 | +0.0119 |
| GGUF `Q4_K_M` (lượng tử hoá cả embedding) | +0.0063 | +0.0037 |

`Q4_K_M` tốt ngang GPTQ dù không có dữ liệu hiệu chỉnh: scale con 6 bit được chọn bằng tìm kiếm tối thiểu sai số, và hỗn hợp
giữ các tensor nhạy ở `Q6_K` (ở PC còn được "tặng" 5 bit do fallback). Tốc độ: tăng từ f32 lên f16/`Q8_0` rõ rệt (đọc ít byte hơn),
nhưng giữa các mức 2-5 bit không có thứ tự rõ: model 13.8 triệu tham số quá nhỏ để băng thông là nút thắt, chi phí cố định mỗi
token (gọi hàm, sampling, đồng bộ luồng) và độ ồn của máy đang bận lấn át. Đó là ví dụ thật của "nhỏ hơn không phải nhanh hơn".

## Quyết định cần cân nhắc

- Đánh giá bằng token id, không bằng chuỗi: tránh lệch tokenization; nhưng vẫn kiểm tokenizer của llama.cpp riêng, vì người dùng
  thật đưa chuỗi vào.
- `n_ctx` bằng `block_size` (256): GPT mini dùng position embedding học được, không ngoại suy được quá độ dài train.
- So sánh công bằng: cùng tập validation, cùng cửa sổ trượt, và ghi rõ phương pháp nào lượng tử hoá embedding.
- Tốc độ: lặp vài lần, bỏ lần đầu, ghi số luồng và tải máy; với model tí hon, đừng kết luận về băng thông.
- Phát hành: Modelfile `FROM ./gpt-mini-vi-Q4_K_M.gguf` cho Ollama; ghi bpc và cấu hình vào model card.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | 3 hàm pass mọi test (kể cả so logits với llama.cpp nếu đã cài) |
| Tệp GGUF đúng | 15 | chứng minh tokenizer và bpc f32 khớp PyTorch, giải thích mọi chênh lệch |
| Bảng đánh đổi | 25 | ít nhất 4 mức llama.cpp và 3 phương pháp tự cài, cùng validation, có dung lượng, bpc, Δ, tốc độ kèm điều kiện đo |
| Phân tích | 25 | đọc kiểu tensor thật và giải thích fallback; giải thích vì sao tốc độ không tỉ lệ với dung lượng; so phương pháp theo mức bit |
| Khuyến nghị và tái lập | 20 | chọn một định dạng có lý do bằng số, hướng dẫn chạy bằng Ollama/llama.cpp, giới hạn của phép đo |

Đạt từ 70 điểm. Báo cáo không đo bpc trên validation, hoặc chỉ dựa vào tên tệp mà không đọc kiểu tensor, không quá 50 điểm.
