# M04: Quantize LLM và chạy local hiệu quả

## Mục tiêu

Chọn mức quantize cho LLM sinh câu trả lời của trợ lý bằng số, không bằng cảm giác "4 bit thì nhẹ và nhanh": đo chất
lượng trên **văn bản luật** (không phải Wikipedia), tốc độ ở độ dài prompt giống RAG, và bộ nhớ, cho ít nhất ba mức, rồi
chọn trên Pareto front theo ngân sách phần cứng của bạn.

Milestone gắn với [module 10](../../modules/10-quantization/README.md) nên đứng **trước** M01 trong lộ trình. Nó tự đứng
được: chỉ cần đọc `corpus.jsonl` và gọi model, chưa cần retrieval. Khi xong M03, bạn quay lại bước 6 để đo bằng chính
pipeline RAG. Phương pháp đo (bpc, cửa sổ trượt, đo VRAM, tốc độ prompt và sinh tách riêng) là của bài Advanced 02
module 10; ở đây đổi model và văn bản.

**Phần cứng:** GPU 4GB hoặc CPU; khoảng 5 tới 8 giờ làm. Trên PC 12GB có thể thêm mức `fp16` của model 3B.

## Việc cần làm

1. **Chọn model và các mức**: model sinh của capstone là `qwen2.5:3b` (Ollama mặc định là bản `Q4_K_M`). Chọn ít nhất ba
   mức của cùng model, ví dụ `q3_K_M`, `q4_K_M`, `q8_0` (tag `qwen2.5:3b-instruct-<mức>` trên Ollama, hoặc GGUF tự
   lượng tử bằng llama.cpp), thêm `fp16` nếu bộ nhớ cho phép. Laptop không đủ cho 3B ở mức cao: làm cùng bảng với
   `qwen2.5:0.5b` (các tag `q3_K_M`, `q4_K_M`, `q8_0`, `fp16`) và ghi rõ.
2. **Văn bản đo chất lượng**: một mẫu cố định từ corpus luật, ví dụ 200 điều chọn ngẫu nhiên với seed ghi lại, hoặc các
   điều là đáp án của tập ghim. Không dùng split test làm dữ liệu chọn mức nếu bạn còn định so RAG trên nó: ghi rõ mẫu
   lấy từ đâu.
3. **Chất lượng**: bits per character trên mẫu đó, cùng cửa sổ và stride cho mọi mức (module 10 dùng llama.cpp/`gguf` hoặc
   Transformers). Ghi cả bpc tuyệt đối và chênh lệch so với mức cao nhất.
4. **Tốc độ và bộ nhớ**: token/giây phần prompt và phần sinh tách riêng, ở prompt khoảng 1 500 token (cỡ prompt RAG
   có 5 nguồn) và 200 token sinh; trung vị của ít nhất 3 lần sau một lần khởi động; VRAM đỉnh (hoặc RAM nếu chạy CPU);
   kích thước tệp và `bits_per_weight` (`quant.py`). Ghi GPU có đang bị tiến trình khác dùng không.
5. **Quyết định**: `pareto_front` trên (bpc nhỏ, VRAM nhỏ, token/giây lớn); chọn một mức trên front theo ràng buộc của
   bạn (ví dụ "vừa GPU 4GB cùng `bge-m3`") và viết lý do. Đọc lại bảng kiểu tensor thật trong GGUF ở SOLUTION bài
   Advanced 02 module 10: mức danh nghĩa không phải số bit thật.
6. **Quay lại sau M03**: chạy harness của M03 trên 100 câu đầu tập ghim với mức đã chọn và một mức thấp hơn; so tỉ lệ
   từ chối, tỉ lệ trích đúng điều, faithfulness. Đây là phép đo chất lượng thật của hệ thống, bpc chỉ là đại diện.

## Kết quả nộp

- `legal_assistant/quant.py`, test M04 pass; script đo và log.
- `reports/QUANT.md`: bảng các mức (bpc, Δbpc, tệp, bit/tham số, VRAM, token/giây prompt và sinh), Pareto front, mức đã
  chọn và lý do; sau M03 thêm bảng chất lượng RAG.

## Tiêu chí đạt

- [ ] Ít nhất ba mức của **cùng** model, đo trên cùng mẫu văn bản luật, cùng cửa sổ, cùng prompt đo tốc độ.
- [ ] Tốc độ là trung vị của ít nhất 3 lần, tách prompt và sinh; điều kiện máy (GPU dùng chung hay không) ghi cạnh số.
- [ ] `bits_per_weight` tính từ kích thước tệp thật cho mọi mức GGUF; báo cáo chỉ ra ít nhất một mức có số bit thật khác
      tên gọi, hoặc giải thích vì sao model của bạn không có hiện tượng đó.
- [ ] Mức được chọn nằm trên Pareto front; lý do nêu ràng buộc phần cứng bằng số (VRAM còn lại cho `bge-m3` và reranker).
- [ ] Sau M03: bảng RAG trên cùng 100 câu cho hai mức; chênh lệch được đọc theo số câu (100 câu, một câu là 0.01).

## Gợi ý

- Ollama giữ model trong VRAM một lúc sau mỗi lời gọi: đo VRAM khi chỉ có một model được nạp, và nạp model trước khi bấm
  giờ.
- Token/giây phần prompt quyết định độ trễ RAG nhiều hơn bạn nghĩ: 5 nguồn dài là hàng nghìn token đọc vào cho mỗi câu
  trả lời vài trăm token.
- bpc trên văn bản luật của model nhỏ có thể khác hẳn bpc trên Wikipedia; đừng mang Δ của module 10 sang mà không đo.
- Nếu llama.cpp chưa cài: `uv sync --group llama` (cần gcc, cmake), xem README track.
