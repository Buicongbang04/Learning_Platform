---
title: GPT mini tiếng Việt từ PyTorch tới GGUF và llama.cpp (portfolio)
level: advanced
services: []
files:
  - path: starter/gguf_portfolio.ipynb
    note: 3 hàm chấm, còn lại tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_gguf_portfolio.py
    note: Không sửa
run:
  - uv sync --group llama
  - uv run jupyter lab tracks/ai-engineer/modules/10-quantization/exercises/advanced/01-gpt-mini-gguf-portfolio/starter/gguf_portfolio.ipynb
  - uv run pytest tracks/ai-engineer/modules/10-quantization/exercises/advanced/01-gpt-mini-gguf-portfolio -q
---

## Mục tiêu

Đưa GPT mini tiếng Việt của module 05 qua đúng con đường của một model mở thật: xuất GGUF, quantize bằng llama.cpp ở nhiều mức,
chạy bằng `llama-cpp-python` hoặc Ollama, và đặt cạnh các phương pháp tự cài của bài Intermediate trong một bảng đánh đổi có
điều kiện đo rõ ràng. Sản phẩm: một tệp GGUF chạy được và một báo cáo portfolio trả lời "nên phát hành model này ở định dạng
nào, cho máy nào".

## Đề bài

**Phần cứng:** CPU · ~360 phút

Thời gian trên là thời gian làm bài. Bản tham chiếu trên PC (CPU 4 luồng, máy dùng chung): xuất GGUF và quantize 7 mức dưới 10
giây cho mỗi checkpoint; mỗi lần đánh giá bpc trên đủ validation bằng llama.cpp khoảng 2-3 phút. Không cần GPU; có GPU thì thêm
được các dòng bitsandbytes.

1. Trong `starter/gguf_portfolio.ipynb`, viết 3 hàm được chấm: `gguf_tensor_name`, `export_gguf`, `sequence_nll` (đặc tả trong
   notebook). Test kiểm metadata, tokenizer, tensor đọc lại bằng `gguf.GGUFReader`, và (nếu đã cài `llama-cpp-python`) logits
   của llama.cpp khớp PyTorch trên một model tí hon.
2. Xuất checkpoint `gpt-mini-v1` của bạn ra f32 và f16; chứng minh tệp đúng: tokenizer của llama.cpp cho cùng token id với
   tokenizer gốc, bpc của bản f32 chạy bằng llama.cpp khớp PyTorch.
3. Quantize bằng llama.cpp ít nhất `Q8_0`, `Q4_0`, `Q4_K_M`, `Q2_K`; đọc lại kiểu thực của từng tensor.
4. Đo bpc (cùng validation, cùng cửa sổ trượt với module 05), dung lượng tệp, tốc độ sinh token; thêm các dòng RTN/GPTQ/AWQ/QAT
   của bài Intermediate ở cùng số bit.
5. Viết `starter/REPORT.md`, rồi làm phần trắc nghiệm của bài trong app.

Không có checkpoint của module 05: dùng checkpoint dự phòng mà bài Intermediate 01 tự train; ghi rõ trong báo cáo.

## Tiêu chí đạt

- 3 hàm pass mọi test; tệp GGUF xuất ra nạp được bằng llama.cpp.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng, dùng bpc, nói về GGUF; hình (nếu có) phải tồn tại.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`llama_cpp.Llama(model_path=..., n_ctx=<block_size>, logits_all=True, verbose=False)`; mỗi cửa sổ: `llm.reset()`,
`llm.eval(list_token_id)`, rồi `llm.scores[:len(ids)]` là logits từng vị trí. Đưa thẳng token id (không đưa chuỗi) để chắc cùng
tokenization với PyTorch. Quantize: `llama_cpp.llama_model_quantize(src.encode(), dst.encode(), ctypes.byref(params))` với
`params = llama_cpp.llama_model_quantize_default_params()` và `params.ftype` là mã của mức quantize (enum `LlamaFileType` trong
gói `gguf` có cùng số).

### Gợi ý 2

Log của llama.cpp khi quantize nói rõ tensor nào phải dùng kiểu khác ("falling back"); k-quant làm việc theo siêu khối 256 phần
tử trên mỗi hàng. Đo tốc độ: chạy vài lần, bỏ lần đầu (nạp tệp, cache), ghi số luồng và tải máy lúc đo; sinh token với batch 1 là
bài toán đọc bộ nhớ, không phải bài toán tính toán.
