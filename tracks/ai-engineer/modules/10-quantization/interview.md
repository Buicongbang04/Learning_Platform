# Câu hỏi phỏng vấn: Quantization

## Quantization là gì? Vì sao nó làm LLM rẻ và nhanh hơn, và nó không làm gì?

Quantization biểu diễn trọng số (và có thể cả activation, KV cache) bằng ít bit hơn: thay vì 16 bit bf16, mỗi trọng số là một
mã số nguyên 8 hay 4 bit cộng một scale dùng chung cho một nhóm. Lợi ích chính là **bộ nhớ**: Qwen2.5-7B ở bf16 cần khoảng
14 GiB chỉ cho trọng số, ở Q4_K_M khoảng 4.4 GiB (module 09), nên vừa GPU 8 GB. Lợi ích thứ hai là **tốc độ sinh token**: với
batch nhỏ, mỗi token sinh ra phải đọc toàn bộ trọng số từ bộ nhớ một lần, phép tính thì ít; đọc ít byte hơn là sinh nhanh hơn,
**nếu** có kernel đọc thẳng dạng nén và giải lượng tử ngay trong thanh ghi.

Nó không làm: không giảm số phép tính khi chỉ quantize trọng số (vẫn nhân ở bf16 sau khi giải nén), không tự nhanh hơn nếu
kernel không hỗ trợ định dạng đó (bitsandbytes int8 trong bài Advanced 02 chậm hơn bf16 nhiều lần), và không miễn phí về chất
lượng: cái giá phải đo trên chính tác vụ của bạn.

## Absmax và zero-point khác nhau thế nào? Khi nào dùng cái nào?

Absmax (đối xứng): $$s = \max\lvert x\rvert / (2^{b-1}-1)$$, mã $$\mathrm{round}(x/s)$$ quanh 0, không cần zero-point. Zero-point
(bất đối xứng): ánh xạ khoảng $$[\min, \max]$$ (nới để chứa 0) lên $$[0, 2^b-1]$$, cộng một zero-point nguyên. Trọng số phân phối
gần đối xứng quanh 0 nên absmax là mặc định ở 8 bit (rẻ hơn khi nhân: không phải trừ zero-point). Activation sau ReLU/GELU lệch
hẳn về một phía nên zero-point dùng được gần gấp đôi số mức. Ở 2-4 bit, mỗi mức đều quý: absmax với $$q_{max} = 2^{b-1}-1$$ bỏ phí
một mã (int4 chỉ còn 15 mức, int2 chỉ còn 3), nên các định dạng thấp bit thường có zero/min riêng cho từng nhóm (`Q4_1`, GPTQ
mặc định bất đối xứng).

## Per-tensor, per-channel, per-group: chọn thế nào?

Một scale cho cả ma trận thì một trọng số ngoại lai kéo scale lên, mọi trọng số nhỏ bị làm tròn về vài mã quanh 0. Per-channel
(một scale mỗi hàng output) chặn ảnh hưởng của ngoại lai trong một hàng và gần như miễn phí về dung lượng; ở 8 bit thường là đủ.
Ở 4 bit trở xuống cần **nhóm** 32-128 trọng số liền nhau: scale bám sát độ lớn cục bộ, đổi lại mỗi nhóm tốn thêm 16 bit scale
(nhóm 128 thêm 0.125 bit mỗi trọng số, nhóm 32 thêm 0.5 bit). Nhóm nhỏ hơn chính xác hơn nhưng tệp lớn hơn và kernel phức tạp
hơn; nhóm 128 là điểm cân bằng phổ biến của GPTQ/AWQ, khối 32 là của `Q4_0`/`Q8_0`, siêu khối 256 với scale con 6 bit là của
k-quant.

## Ngoại lai activation là gì và vì sao nó làm W8A8 khó hơn W8A16?

Ở LLM vài tỉ tham số trở lên, một số ít kênh của hidden state có độ lớn gấp hàng chục tới hàng trăm lần phần còn lại, và xuất
hiện ở gần như mọi token (Dettmers và cộng sự, LLM.int8(), 2022). Quantize trọng số không đụng tới chúng, nên W8A16/W4A16 vẫn
ổn. Quantize **activation** per-tensor thì scale bị các kênh đó chiếm, phần còn lại mất gần hết độ chính xác. Các cách xử lý:
LLM.int8() tách các kênh vượt ngưỡng ra nhân bằng fp16 (chính xác nhưng chậm); SmoothQuant chuyển độ khó từ activation sang trọng
số bằng một phép scale theo kênh gộp được vào lớp trước; quantize activation per-token; hoặc dùng fp8 (dải động rộng hơn int8
nhiều).

## Giải thích GPTQ trong hai phút.

GPTQ quantize từng lớp tuyến tính sao cho **đầu ra** trên dữ liệu hiệu chỉnh thay đổi ít nhất:
$$\min_{\hat W}\lVert XW^\top - X\hat W^\top\rVert^2$$. Hàm mất mát này bậc hai, Hessian theo mỗi hàng là $$H = 2X^\top X$$ (giống
nhau cho mọi hàng). Duyệt các cột theo thứ tự: làm tròn cột $$j$$, rồi cập nhật các cột **chưa** làm tròn để bù sai số vừa gây ra,
theo công thức Optimal Brain Surgeon: $$\delta = -\frac{w_j - q_j}{[H^{-1}]_{jj}}\,[H^{-1}]_{j,:}$$. Mẹo làm nó chạy được trên model
175B: dùng chung một thứ tự cột cho mọi hàng, lấy các hàng cần thiết của $$H^{-1}$$ từ nhân tử Cholesky (tính một lần, ổn định số
nhờ dampening $$\lambda I$$), và cập nhật theo khối (lazy batch) để tận dụng GPU. Kết quả: sai số trọng số thường **lớn hơn** RTN
nhưng sai số đầu ra nhỏ hơn, vì GPTQ tối ưu đúng thứ quan trọng.

## AWQ khác GPTQ ở đâu?

AWQ không sửa trọng số theo Hessian. Nó quan sát rằng một phần nhỏ trọng số "quan trọng" là những trọng số gặp kênh activation
lớn, và bảo vệ chúng bằng một phép scale tương đương: nhân cột $$k$$ của $$W$$ với $$s_k$$, chia input kênh $$k$$ cho $$s_k$$ (gộp
vào LayerNorm hoặc lớp tuyến tính phía trước), rồi mới RTN. Scale $$s = \bar{\lvert x\rvert}^{\alpha}$$, $$\alpha$$ tìm trên lưới để
sai số đầu ra nhỏ nhất. Ưu điểm: không bị overfit tập hiệu chỉnh như cập nhật bậc hai, quantize nhanh, định dạng đầu ra vẫn là
int4 theo nhóm bình thường. Hiệu quả của AWQ phụ thuộc vào việc model có kênh activation nổi trội hay không; trên một model nhỏ
không có hiện tượng đó, AWQ gần như không hơn RTN (bài Intermediate 02 cho bạn đo).

## Straight-through estimator là gì? Vì sao QAT cần nó?

Hàm làm tròn có đạo hàm bằng 0 ở mọi nơi, nên nếu để autograd tự lan truyền qua fake quantization, gradient của trọng số bằng 0.
STE giả vờ phép làm tròn là hàm đồng nhất khi lan truyền ngược (giữ gradient bằng 0 ở chỗ bị kẹp). Forward dùng trọng số đã làm
tròn, nên loss phản ánh model lượng tử thật; backward cập nhật bản trọng số float32 "chủ", nên các thay đổi nhỏ hơn một bước
lượng tử vẫn được tích luỹ cho tới khi đủ để nhảy sang mã kế bên. Đó là thứ PTQ không làm được: PTQ chỉ chọn cách làm tròn,
QAT dời luôn trọng số tới chỗ hợp lưới.

## PTQ hay QAT: bạn chọn thế nào?

PTQ (RTN, GPTQ, AWQ) không cần train, vài phút tới vài giờ, chỉ cần vài trăm đoạn văn bản hiệu chỉnh; ở 8 bit và 4 bit nhóm 128
thường mất rất ít. QAT cần pipeline train, dữ liệu gần phân phối gốc, bộ nhớ của train (trọng số float32, optimizer state), và
dễ làm model trôi khỏi phân phối gốc nếu dữ liệu fine-tune hẹp. Chọn QAT khi bit rất thấp (2-3 bit) mà PTQ mất quá nhiều, khi
model sẽ chạy trên phần cứng chỉ hỗ trợ int (điện thoại, NPU) với số lượng lớn, hoặc khi nhà phát hành model muốn một bản 4 bit
tốt nhất có thể (Meta phát hành Llama 3.2 1B/3B lượng tử bằng QAT kết hợp LoRA; Google phát hành Gemma 3 bản QAT). Luôn so với
đối chứng "fine-tune float32 cùng ngân sách rồi PTQ", không thì không biết QAT có tác dụng thật không.

## GGUF là gì? `Q4_K_M` nghĩa là gì?

GGUF là định dạng tệp của llama.cpp (và Ollama, LM Studio): một tệp duy nhất gồm metadata (kiến trúc, siêu tham số, tokenizer,
chat template, giấy phép) và các tensor có tên, mỗi tensor một kiểu lượng tử riêng; tệp được map thẳng vào bộ nhớ khi nạp.
`Q4_0`/`Q8_0` là kiểu "legacy": khối 32 trọng số, một scale fp16 mỗi khối (4.5 và 8.5 bit/trọng số). `Q4_K` là k-quant: siêu khối
256 trọng số chia 8 khối con 32, mỗi khối con có scale và min 6 bit, siêu khối có scale fp16, khoảng 4.5 bit. Hậu tố `_S/_M/_L`
là **hỗn hợp**: `Q4_K_M` giữ một số tensor nhạy (một nửa `attn_v` và `ffn_down`, lớp output) ở `Q6_K`. Ngoài ra k-quant cần số cột
chia hết cho 256; tensor không thoả thì llama.cpp dùng kiểu dự phòng, nên "Q4_K_M" của một model cụ thể có thể chứa nhiều kiểu
khác. Đọc kiểu thật bằng `gguf.GGUFReader` trước khi tin vào tên tệp.

## bitsandbytes NF4 là gì? Vì sao QLoRA dùng nó?

NF4 (NormalFloat 4 bit, Dettmers và cộng sự, QLoRA 2023) là 16 mức không đều, đặt tại các phân vị của phân phối chuẩn và chuẩn
hoá về $$[-1, 1]$$, có đúng một mức bằng 0. Trọng số đã train gần phân phối chuẩn, nên mỗi mức được dùng gần như đều nhau: ít lãng
phí hơn int4 đều. Scale absmax theo khối 64; **double quantization** lượng tử luôn các scale đó (fp32 sang 8 bit theo khối 256),
tiết kiệm thêm khoảng 0.37 bit/trọng số. QLoRA giữ model gốc ở NF4 đông cứng và chỉ train adapter LoRA ở bf16 (module 14): bộ nhớ
của trọng số giảm khoảng 4 lần so với bf16 mà chất lượng fine-tune gần như giữ nguyên. NF4 là định dạng **lưu trữ**: khi nhân,
bitsandbytes giải lượng tử về `bnb_4bit_compute_dtype` (bf16), nên nó tiết kiệm bộ nhớ nhiều hơn là tăng tốc.

## fp8 có gì khác int8? GPU nào dùng được?

fp8 là số dấu phẩy động 8 bit: E4M3 (4 bit mũ, 3 bit mantissa, lớn nhất 448) cho trọng số và activation, E5M2 (lớn nhất 57 344)
cho gradient. So với int8 cùng 8 bit, fp8 có **sai số tương đối** gần như không đổi trên cả dải (int8 có sai số tuyệt đối không
đổi), nên chịu được ngoại lai tốt hơn mà không cần tách kênh, và dùng được cho cả train. Tensor core fp8 có từ kiến trúc Ada
(RTX 40xx, L40S) và Hopper (H100); Ampere (RTX 30xx, A100) không có, chỉ mô phỏng được. Blackwell thêm fp4 và các định dạng scale
theo khối (MXFP4, NVFP4).

## Case: model 7B phải chạy trên laptop GPU 8 GB cho 20 người dùng nội bộ. Bạn quantize thế nào?

Tính trước (module 09): 7.6 tỉ tham số ở bf16 là 14 GiB, không vừa; Q4_K_M khoảng 4.4 GiB, còn 3 GiB cho KV cache và context. Với
GQA 4 KV head, 28 tầng, $$d_{head}$$ 128, KV cache fp16 khoảng 56 KiB mỗi token, 3 GiB đủ khoảng 50 nghìn token tổng cho mọi
request đang chạy. Lựa chọn: (1) GGUF Q4_K_M qua llama.cpp server (continuous batching, `-np` vài slot) hoặc Ollama nếu tải nhẹ;
(2) AWQ/GPTQ int4 qua vLLM nếu GPU hỗ trợ kernel Marlin và cần throughput cao. Trước khi chốt: đo trên bộ eval của chính sản phẩm
(không chỉ perplexity) ở bf16 trên máy khác và ở bản quantize; so Q4_K_M với Q5_K_M và Q8_0 (bản Q8 không vừa thì dùng làm trần
chất lượng); đo p95 độ trễ với 20 người dùng mô phỏng. Nếu chất lượng tụt ở một loại câu hỏi (số liệu, tiếng Việt có dấu), thử
imatrix (dữ liệu hiệu chỉnh tiếng Việt) hoặc lên 5 bit trước khi nghĩ tới model nhỏ hơn.

## Case: sau khi chuyển sang bản 4 bit, người dùng phàn nàn câu trả lời tệ hơn ở tiếng Việt. Bạn điều tra thế nào?

Đừng tranh luận bằng cảm giác. (1) Tái hiện: lấy log các câu bị phàn nàn, chạy cùng prompt, cùng tham số sampling trên bản bf16
và bản 4 bit, greedy để loại nhiễu sampling. (2) Đo có hệ thống: perplexity/bpc trên văn bản tiếng Việt (Wikipedia, dữ liệu sản
phẩm) và trên tiếng Anh, cho bf16, 8 bit, 4 bit: nếu khoảng cách ở tiếng Việt lớn hơn rõ rệt, nguyên nhân thường là dữ liệu hiệu
chỉnh (GPTQ/AWQ/imatrix hiệu chỉnh toàn tiếng Anh) hoặc embedding/lớp output bị lượng tử quá mạnh (vocab tiếng Việt nằm ở các hàng
ít được dùng). (3) Sửa theo thứ tự rẻ tới đắt: hiệu chỉnh lại bằng dữ liệu tiếng Việt, giữ embedding/`lm_head` ở 8 bit, lên mức
bit cao hơn cho các lớp nhạy (đo bằng độ nhạy từng lớp như bài Intermediate 01), rồi mới tới QAT. (4) Đưa bộ eval tiếng Việt vào
CI của pipeline quantize để lần sau phát hiện trước khi phát hành.

## Vì sao bản 4 bit có thể chậm hơn bản 16 bit?

Vì tốc độ phụ thuộc kernel, không phụ thuộc số bit. Bản 4 bit chỉ nhanh khi kernel đọc dữ liệu nén và giải lượng tử ngay trong
thanh ghi trong lúc nhân (Marlin, ExLlamaV2, kernel của llama.cpp). Nếu thư viện giải lượng tử cả ma trận ra bf16 rồi mới gọi
GEMM, bạn đọc dữ liệu nén **và** ghi rồi đọc lại bản bf16: chậm hơn không quantize. Với batch lớn (prefill, serving nhiều người),
bài toán chuyển từ đọc bộ nhớ sang tính toán, lợi thế của việc đọc ít byte biến mất trong khi chi phí giải lượng tử vẫn còn. Và
LLM.int8() của bitsandbytes tách kênh ngoại lai ra nhân riêng, thêm nhiều kernel nhỏ: chính xác nhưng chậm. Luôn đo token/giây và
độ trễ trên đúng phần cứng, đúng batch, đúng độ dài context.
