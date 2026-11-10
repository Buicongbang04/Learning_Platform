# Hướng làm: Qwen2.5-0.5B, chọn cấu hình quantize cho laptop GPU 4 GB và server CPU

Bài không có một đáp án duy nhất; dưới đây là hướng làm, kết quả của bản tham chiếu (giữ ngoài repo) và rubric.

## Bốn hàm được chấm

- `gguf_to_hf_name`: bảng ánh xạ cố định; tên không khớp mẫu `blk.{i}.{x}.{weight|bias}` thì `KeyError` (ví dụ `attn_qkv` của kiến
  trúc khác) để không nạp nhầm im lặng.
- `load_gguf_state_dict`: `gguf.GGUFReader(path)`, với mỗi tensor `gguf.quants.dequantize(t.data, t.tensor_type)` rồi `reshape` theo
  `reversed(t.shape)`; GGUF ghi `ne0` (chiều trong cùng) trước. Không có tensor `output.weight` trong tệp của Qwen2.5-0.5B: model
  dùng chung `lm_head` với embedding, nạp `model.embed_tokens.weight` là đủ. Kiểm đường đo bằng tệp `F16`: phải cho đúng bpc của
  bf16 (bản tham chiếu: 1.1846 cả hai).
- `pareto_front`: dòng $$a$$ trội dòng $$b$$ nếu không tệ hơn ở mọi cột và tốt hơn hẳn ở ít nhất một cột; giữ các dòng không bị dòng
  nào trội. Hai dòng bằng nhau không trội nhau.
- `pick_config`: lọc theo ngân sách bộ nhớ (`<=`) và độ tăng bpc, chọn `speed_key` lớn nhất, hoà thì ít bộ nhớ hơn.

## Kết quả bản tham chiếu

Validation 100 bài (664 568 ký tự, 204 203 token Qwen), cửa sổ 1 024, stride 512. PC RTX 3060 12 GB, ngày 2026-11-01; phần lớn số
GPU đo khi **GPU dùng chung** với một server LLM khác (cột cuối ghi VRAM tiến trình khác đang giữ và % sử dụng GPU lúc đo).

| Cấu hình (GPU) | bpc | Δ | Sau khi nạp | Đỉnh khi sinh | Token/giây | GPU lúc đo |
| --- | --- | --- | --- | --- | --- | --- |
| bf16 | 1.1846 | | 950 MiB | 964 MiB | 26.1 | 10.5 GB, 19% |
| fp16 | 1.1845 | −0.0001 | 950 MiB | 964 MiB | 31.3 | 10.5 GB, 20% |
| bitsandbytes int8 | 1.1879 | +0.0033 | 602 MiB | 617 MiB | 5.8 | 10.2 GB, 8% |
| bitsandbytes NF4 | 1.2508 | +0.0662 | 452 MiB | 466 MiB | 20.0 | 10.0 GB, 11% |
| bitsandbytes NF4 + double quant | 1.2507 | +0.0661 | 436 MiB | 450 MiB | 20.0 | 9.9 GB, 12% |
| bitsandbytes FP4 | 1.3429 | +0.1583 | 452 MiB | 466 MiB | 19.8 | 10.0 GB, 11% |
| GGUF `Q8_0` giải lượng tử | 1.1850 | +0.0004 | | | | |
| GGUF `Q4_K_M` giải lượng tử | 1.2106 | +0.0260 | | | | |
| GGUF `q3_K_M` giải lượng tử | 1.2310 | +0.0464 | | | | |
| RTN int4 nhóm 128 | 1.3865 | +0.2019 | | | | |
| AWQ int4 nhóm 128 (tự cài) | 1.3032 | +0.1186 | | | | |
| GPTQ int4 nhóm 128 (tự cài) | 1.2457 | +0.0611 | | | | |

| Định dạng (CPU 4 luồng; Ollama GPU khi GPU rảnh) | Tệp | llama.cpp sinh | llama.cpp prompt | Ollama CPU | Ollama GPU |
| --- | --- | --- | --- | --- | --- |
| `F16` | 994 MB | 31 | 451 | 31 | 226 |
| `Q8_0` | 531 MB | 51 | 335 | 51 | 364 |
| `Q4_K_M` | 398 MB | 53 | 330 | 51 | 392 |
| `q3_K_M` | 355 MB | 65 | 443 | 52 | 417 |
| Transformers bf16 / fp32 (CPU) | | 20 / 14 | | | |

(Nguồn: `logs/qwen_gpu.json`, `qwen_cpu.json`, `ollama_speed.log`, `qwen_gguf_types.log` của bản tham chiếu.)

Kiểu thật trong tệp GGUF của Ollama (hidden size 896 không chia hết cho 256):

| Tệp | attn_q/k, ffn_gate/up | attn_output | attn_v | ffn_down | embedding |
| --- | --- | --- | --- | --- | --- |
| `q4_K_M` | `Q5_0` | `Q5_0` | 12 `Q8_0`, 12 `Q5_0` | 12 `Q6_K`, 12 `Q4_K` | `Q8_0` |
| `q3_K_M` | `IQ4_NL` | `Q5_0` | `Q5_0` (2 `Q5_1`) | 23 `Q4_K`, 1 `Q5_K` | `Q8_0` |

Chỉ `ffn_down` (4 864 cột = 19 × 256) dùng được k-quant; phần còn lại rơi về kiểu dự phòng 4.5-5.5 bit. Vì vậy "q3_K_M" của Ollama
thực chất gần 4.5 bit, và `Q4_K_M` mất ít hơn NF4 một phần là nhờ được "tặng" bit.

Kiểm chéo đường đo GGUF trên 5 bài đầu: giải lượng tử cho 1.1239 (`F16`) và 1.1489 (`Q4_K_M`); llama.cpp chạy thật cho 1.1236 và
1.1506. Kernel CPU của llama.cpp lượng tử hoá activation sang 8 bit khi nhân, thêm khoảng 0.002 bpc.

## Đọc kết quả và quyết định

- **Pareto front GPU** trên (bpc, đỉnh VRAM, token/giây), sáu dòng bitsandbytes/bf16/fp16: fp16 (nhanh nhất, chính xác nhất),
  bitsandbytes int8 (chính xác gần bf16, ít VRAM hơn, rất chậm), NF4 + double quant (ít VRAM nhất) và NF4 (nhanh hơn NF4 + double
  quant 0.04 token/giây, tức chỉ nhờ nhiễu đo: một ví dụ vì sao Pareto front cần sai số đo đi kèm). bf16 bị fp16 trội; FP4 bị NF4 trội ở
  mọi cột. Double quant chỉ bớt 16 MiB (scale của
  khối 64 lượng tử thêm một lần), bpc không đổi.
- **Laptop GPU 4 GB**: bf16 chỉ cần dưới 1 GiB trọng số và 2.4 GiB đỉnh khi đánh giá cửa sổ 1 024 token, nên vừa; `pick_config`
  với 3 000 MiB và Δbpc ≤ 0.01 chọn fp16. Nếu cần phục vụ thật, Ollama `Q8_0` trên GPU (364 token/giây, Δ 0.0004) hơn hẳn mọi lựa
  chọn Transformers. Lượng tử 4 bit trên GPU chỉ đáng khi bộ nhớ là ràng buộc (model lớn hơn), và khi đó GGUF `Q4_K_M` hoặc GPTQ có
  hiệu chỉnh, không phải RTN.
- **Server CPU**: `Q8_0` qua llama.cpp gần như không mất chất lượng và sinh nhanh hơn `F16` 1.6 lần; `Q4_K_M` sinh gần bằng `Q8_0` (vì
  phần lớn tensor là `Q5_0`) mà mất 0.026 bpc; `q3_K_M` nhanh nhất nhưng mất 0.046. Với ngưỡng Δbpc ≤ 0.01, chọn `Q8_0`. Nếu prompt
  dài (RAG), nhớ rằng `F16` xử lý prompt nhanh hơn `Q8_0`/`Q4_K_M` trên CPU.
- **Nhỏ hơn không phải nhanh hơn**: bitsandbytes int8 nhỏ hơn bf16 mà chậm 5 lần; NF4 chậm hơn bf16; xử lý prompt trên CPU chậm đi
  khi lượng tử. Tốc độ do kernel, runtime và nút thắt (bộ nhớ hay tính toán) quyết định.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | 4 hàm pass mọi test |
| Đo chất lượng đúng | 20 | cùng validation, cùng cửa sổ cho mọi dòng; kiểm đường đo GGUF bằng `F16`; nói rõ dòng nào chỉ đo trọng số |
| Đo bộ nhớ và tốc độ có điều kiện | 20 | `max_memory_allocated` quanh đúng đoạn, khởi động trước khi bấm giờ, lặp và lấy trung vị, ghi GPU/CPU, số luồng, máy bận hay rảnh |
| Đọc định dạng | 15 | đọc kiểu tensor thật trong tệp GGUF và giải thích fallback; giải thích vì sao bitsandbytes không giảm 4 lần bộ nhớ |
| Quyết định | 20 | Pareto front và `pick_config` cho từng máy với ràng buộc ghi rõ, khuyến nghị có số, nêu đánh đổi khi ràng buộc đổi |
| Trình bày | 10 | bảng gọn, không kết luận vượt số đo, giới hạn của phép đo |

Đạt từ 70 điểm. Báo cáo so chất lượng bằng perplexity của tokenizer khác nhau, hoặc kết luận tốc độ mà không ghi điều kiện đo,
không quá 50 điểm.
