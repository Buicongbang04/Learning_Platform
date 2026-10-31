# Câu hỏi phỏng vấn: Transformer và kiến trúc LLM

## Self-attention tính gì? Vì sao chia cho căn bậc hai của số chiều head?

Mỗi token tạo ba vector: query $$q$$ (mình đang tìm gì), key $$k$$ (mình chứa gì để được tìm thấy) và value $$v$$ (mình đóng góp gì
nếu được chọn). Output ở vị trí $$i$$ là trung bình có trọng số của mọi value, trọng số là softmax của $$q_i \cdot k_j$$:

$$
\mathrm{Attention}(Q, K, V) = \mathrm{softmax}\left(\frac{QK^\top}{\sqrt{d}} + M\right) V
$$

Nếu các thành phần của $$q, k$$ độc lập, trung bình 0, phương sai 1 thì $$q \cdot k$$ có phương sai $$d$$. Với $$d = 64$$, score
lệch chuẩn 8, softmax gần như one-hot, gradient qua softmax gần 0 ở mọi vị trí trừ một. Chia $$\sqrt{d}$$ đưa phương sai về 1.
Multi-head chia $$d_{model}$$ thành nhiều head nhỏ để mỗi head học một kiểu quan hệ (vị trí liền trước, chủ ngữ, dấu ngoặc
mở...) với cùng chi phí như một head lớn.

## Causal mask là gì, đặt ở đâu? Thiếu nó thì điều gì xảy ra?

Mask $$M$$ gán $$-\infty$$ cho mọi cặp (query $$i$$, key $$j$$) với $$j > i$$, cộng vào score **trước** softmax, để token $$i$$ chỉ
nhìn được $$0..i$$. Nhờ vậy một forward trên chuỗi $$T$$ token cho $$T$$ bài toán "đoán token kế" cùng lúc, đó là lý do GPT train
song song được. Thiếu mask, model nhìn thấy đáp án: loss train giảm rất nhanh về gần 0, nhưng khi sinh (không có tương lai để
nhìn) model vô dụng. Cách kiểm nhanh mà bài Basic 01 dùng: đổi token ở vị trí 7, logits ở vị trí 0..6 phải không đổi. Nhân mask
**sau** softmax cũng sai: hàng trọng số không còn cộng lại bằng 1.

## Pre-norm và post-norm khác nhau thế nào? Vì sao LLM hiện đại dùng pre-norm?

Post-norm (Transformer 2017, BERT): $$x \leftarrow \mathrm{LN}(x + f(x))$$. Pre-norm (GPT-2 trở đi, Llama):
$$x \leftarrow x + f(\mathrm{LN}(x))$$, thêm một LN cuối trước lớp output. Với pre-norm, đường residual từ output về embedding là
một chuỗi phép cộng không qua norm nào: gradient tới lớp đầu không bị co dãn theo độ sâu, train sâu ổn định hơn, ít phụ thuộc
warmup. Đổi lại, độ lớn của residual stream tăng dần theo số tầng (vì vậy GPT-2 thu nhỏ khởi tạo của lớp chiếu về residual
theo $$1/\sqrt{2L}$$) và tầng cuối cần LN cuối. Post-norm nếu train được thường cho chất lượng nhỉnh hơn một chút; các biến thể
như DeepNorm, "sandwich norm" cố lấy cả hai.

## Weight tying là gì? Khi nào nên và không nên dùng?

Dùng chung ma trận embedding $$E \in \mathbb{R}^{V \times d}$$ cho lớp output: logits $$= h E^\top$$. Hai ma trận cùng ý nghĩa
"vector của token", nên tying tiết kiệm $$Vd$$ tham số và thường không làm kém đi. Ở GPT mini của module (V = 8 000, d = 256),
tying cắt model từ 7.29 triệu xuống 5.24 triệu tham số. Model nhỏ có vocab lớn (Gemma, Qwen2.5 0.5B, Llama 3.2 1B) gần như luôn
tie vì embedding chiếm phần lớn tham số. Model lớn (Llama 3 8B, 70B) thường không tie: chi phí tương đối nhỏ, và tách hai ma
trận cho model thêm tự do. Khi quantize (module 10) hoặc fine-tune với LoRA, nhớ rằng sửa một bên là sửa cả hai.

## BERT, GPT và T5 khác nhau ở đâu? Hôm nay bạn chọn kiến trúc nào cho bài toán nào?

Cùng khối Transformer, khác mask và mục tiêu train. BERT là encoder hai chiều train bằng masked language modeling: mỗi token
thấy cả hai phía, giỏi hiểu (phân loại, NER, embedding cho retrieval), không sinh văn bản được tự nhiên. GPT là decoder nhân quả
train bằng next-token prediction: mỗi token là một ví dụ train, sinh văn bản tự nhiên, và với đủ quy mô làm được mọi việc qua
prompt. T5/BART là encoder-decoder: hợp với biến chuỗi thành chuỗi (dịch, tóm tắt) khi input và output tách bạch. Bài
Intermediate 02 đo: cùng kích thước và ngân sách, BERT điền chỗ trống chính xác hơn GPT nhiều, còn GPT là model duy nhất sinh
được câu đọc trôi.

Chọn hôm nay: sinh văn bản, chat, agent, hầu hết bài toán mở: decoder (dùng qua API hoặc model mở). Phân loại hoặc embedding
khối lượng lớn, độ trễ thấp, chạy CPU: encoder nhỏ fine-tune (PhoBERT cho tiếng Việt, bge-m3 cho embedding, module 12). Dịch
máy chuyên biệt, model nhỏ: encoder-decoder vẫn đáng cân nhắc.

## RoPE hoạt động thế nào và vì sao nó thay position embedding học được?

RoPE quay từng cặp chiều của $$q$$ và $$k$$ một góc $$m\theta_i$$ theo vị trí tuyệt đối $$m$$, với tần số $$\theta_i = b^{-2i/d}$$
($$b = 10\,000$$ hoặc lớn hơn). Vì tích vô hướng của hai vector đã quay chỉ phụ thuộc hiệu góc,
$$\langle R_m q, R_n k\rangle = \langle q, R_{n-m} k\rangle$$: attention score chỉ phụ thuộc **khoảng cách** $$m - n$$, dù mỗi
vector được mã hoá theo vị trí tuyệt đối. Không có tham số nào để học, không có bảng giới hạn số vị trí như position embedding
học được (GPT-2 có đúng 1 024 dòng), và có thể kéo dài context sau khi train bằng cách co dãn tần số (position interpolation,
NTK-aware, YaRN), tăng base (Llama 3 dùng 500 000). Trên GPT mini của module, cùng mọi thứ khác, RoPE cho bpc 1.879 so với 1.918
của position embedding học được (một seed). Chi tiết dễ sai: có hai quy ước ghép cặp chiều (liền kề hoặc nửa đầu với nửa sau),
nạp checkpoint theo quy ước này vào code quy ước kia thì model hỏng.

## KV cache là gì, tốn bao nhiêu bộ nhớ, và những kỹ thuật nào giảm nó?

Khi sinh token thứ $$t$$, K và V của $$t-1$$ token trước không đổi (mask nhân quả), nên lưu lại thay vì tính lại: mỗi bước decode
chỉ chiếu token mới. Không có cache, sinh $$n$$ token tốn $$O(n^2)$$ forward token; có cache, $$O(n)$$. Bộ nhớ:

$$
2 \cdot L \cdot H_{kv} \cdot d_{head} \cdot T \cdot B \cdot \text{bytes}
$$

Llama 3 8B (32 tầng, 8 kv head, $$d_{head} = 128$$, bf16) tốn 128 KiB mỗi token, 1 GiB cho một chuỗi 8 192 token, 16 GiB cho batch 16:
bằng cả trọng số model. Cách giảm: GQA/MQA (ít kv head hơn: Llama 3 dùng 8 thay vì 32, giảm 4 lần), quantize cache (int8, fp8),
sliding window attention (Mistral), MLA nén K, V vào một latent nhỏ (DeepSeek-V2/V3), PagedAttention để không phí bộ nhớ do
cấp phát liền khối (vLLM, module 20), và kiến trúc không có KV cache (Mamba, hybrid).

## MHA, MQA, GQA khác nhau thế nào? Bạn chọn số kv head ra sao?

Multi-head attention: mỗi head query có K, V riêng. Multi-query attention: mọi head query dùng chung một cặp K, V (cache nhỏ
nhất, chất lượng giảm và train kém ổn định ở quy mô lớn). Grouped-query attention: chia head query thành $$G$$ nhóm, mỗi nhóm
một cặp K, V; $$G = H$$ là MHA, $$G = 1$$ là MQA. Decode bị giới hạn bởi băng thông bộ nhớ (mỗi token mới phải đọc cả KV cache),
nên cache nhỏ hơn $$H/G$$ lần gần như là tốc độ decode nhanh hơn chừng đó lần ở context dài. Thực tế: $$G = 8$$ (Llama 3, Mistral)
hoặc 4 (Qwen2.5 7B) là điểm cân bằng. Ở quy mô GPT mini, đo trong module: MHA 1.869 bpc, GQA (2 kv head) 1.879, MQA 1.878, chênh
lệch nằm trong mức dao động giữa hai seed, trong khi cache của MQA nhỏ hơn 4 lần.

## Mixture-of-Experts: vì sao "47 tỉ tham số mà chạy như model 13 tỉ"? Cái giá là gì?

Lớp MLP được thay bằng $$E$$ expert và một router chọn top-k expert cho mỗi token. Mixtral 8x7B có 46.7 tỉ tham số nhưng mỗi token
chỉ đi qua 2/8 expert, khoảng 12.9 tỉ tham số hoạt động: FLOP mỗi token như model 13 tỉ, dung lượng tri thức gần model lớn hơn
nhiều. Cái giá: (1) **bộ nhớ** vẫn phải chứa đủ 46.7 tỉ tham số, nên MoE rẻ về compute chứ không rẻ về VRAM; (2) **cân tải**: router
dễ dồn token vào vài expert (expert khác không học, GPU chờ nhau), cần loss phụ cân tải hoặc bias điều chỉnh (DeepSeek-V3);
(3) giao tiếp giữa GPU khi expert nằm rải (expert parallelism); (4) batch nhỏ (chạy local, một người dùng) thì mỗi bước vẫn phải
đọc trọng số của nhiều expert khác nhau, lợi ích tốc độ ít hơn lý thuyết.

## Mamba khác Transformer ở đâu? Khi nào nó hấp dẫn?

Mamba là state space model chọn lọc: mỗi kênh mang một trạng thái cỡ cố định $$N$$, cập nhật bằng hồi quy tuyến tính
$$h_t = \bar A_t h_{t-1} + \bar B_t x_t$$, với $$\Delta, B, C$$ phụ thuộc token (model chọn nhớ hay quên). Train song song nhờ parallel
scan; inference như RNN: mỗi token mới tốn như nhau, **không có KV cache**, bộ nhớ không tăng theo độ dài. Đổi lại, trạng thái cố
định phải nén mọi thứ đã đọc: các tác vụ cần chép lại chính xác một đoạn xa (tra cứu, "needle in a haystack", in-context
retrieval) kém hơn attention. Vì vậy xu hướng là **hybrid**: phần lớn lớp SSM hoặc linear attention, xen vài lớp attention đầy đủ
(Jamba, Zamba, Samba, các bản Qwen3-Next, Nemotron-H). Hấp dẫn khi context rất dài, chạy trên thiết bị ít bộ nhớ, hay sinh chuỗi
dài với batch lớn.

## Scaling laws nói gì? Chinchilla thay đổi cách train LLM ra sao?

Loss của language model giảm theo power law của số tham số $$N$$, số token $$D$$ và compute $$C \approx 6ND$$, đều đặn qua nhiều bậc
độ lớn (Kaplan và cộng sự, 2020). Kaplan kết luận nên tăng $$N$$ nhanh hơn $$D$$; Chinchilla (Hoffmann và cộng sự, 2022) sửa lại
(lịch learning rate khớp với độ dài train), cho thấy $$N$$ và $$D$$ nên tăng cùng tỉ lệ, khoảng 20 token mỗi tham số. Gopher 280B
train 300 tỉ token thua Chinchilla 70B train 1.4 nghìn tỉ token với cùng compute. Sau Chinchilla, ngành lại vượt xa tỉ lệ đó
(Llama 3 8B: 15 nghìn tỉ token, khoảng 1 900 token mỗi tham số) vì Chinchilla tối ưu **compute train**, còn sản phẩm trả tiền cho
**inference** suốt đời model: model nhỏ train lâu rẻ hơn khi phục vụ. Scaling laws dự đoán loss, không dự đoán trực tiếp năng lực
cụ thể nào xuất hiện.

## Vì sao perplexity của hai LLM khác tokenizer không so trực tiếp được? So thế nào?

Perplexity là $$e$$ mũ NLL trung bình **mỗi token**; tokenizer cắt văn bản thành số token khác nhau nên cùng một văn bản có số
token khác, perplexity khác dù model tốt như nhau. Module 04 đo: model byte có perplexity 3.58, model BPE 8 000 có 117, nhưng bpc
của BPE tốt hơn. So công bằng phải quy về đơn vị của **văn bản**: bits per character, bits per byte, hoặc tổng NLL của cùng văn
bản. Thêm vào đó, cách đánh giá Transformer phải ghi rõ: cắt văn bản thành khúc rời (token đầu mỗi khúc gần như không có ngữ
cảnh, perplexity xấu đi) hay cửa sổ trượt với stride bao nhiêu. Module này dùng cửa sổ trượt stride bằng nửa context, để module
10 so model đã quantize với cùng một thước đo.

## Case: model 7B chạy tốt với prompt 2 000 token, nhưng với 30 000 token thì chậm hẳn và hết VRAM. Bạn phân tích thế nào?

Tách hai giai đoạn. **Prefill** xử lý cả prompt một lần: chi phí attention $$O(T^2)$$; với FlashAttention bộ nhớ score không còn
$$T^2$$ nhưng thời gian vẫn tăng bậc hai, nên thời gian tới token đầu (TTFT) tăng mạnh. **Decode** sinh từng token: mỗi bước đọc
toàn bộ trọng số và KV cache; cache tăng tuyến tính theo $$T$$. Tính trước: với GQA 8 kv head, 32 tầng, $$d_{head}$$ 128, bf16, cache là
128 KiB mỗi token, 30 000 token là 3.7 GiB mỗi chuỗi, cộng 15 GiB trọng số bf16. Hướng xử lý theo thứ tự rẻ dần: quantize
trọng số (int4: còn khoảng 4-5 GiB, module 10) và KV cache (fp8/int8); bật FlashAttention/SDPA thay attention thường; giới hạn batch
đồng thời, dùng PagedAttention (vLLM) để không phí bộ nhớ; nếu nội dung cho phép thì bớt context (RAG lấy đúng đoạn cần, module 13,
tóm tắt lịch sử chat); cuối cùng mới đổi model (context dài hơn được train, sliding window, hybrid SSM). Kiểm chất lượng ở context
dài: model train với context 8k mà kéo RoPE lên 32k không chỉnh thì chất lượng có thể giảm dù chạy được.

## Case: công ty muốn một LLM nhỏ tiếng Việt cho trợ lý nội bộ chạy on-premise, ngân sách GPU hạn chế. Bạn thiết kế kiến trúc và quy trình train thế nào?

Đầu tiên là **không pretrain từ số 0** nếu không bắt buộc: một model mở đa ngữ (Qwen2.5, Llama 3.x, Gemma) đã nói tiếng Việt; tiếp
tục pretrain trên dữ liệu tiếng Việt và dữ liệu nội bộ, rồi fine-tune (module 14) rẻ hơn hàng trăm lần. Nếu phải tự train (yêu cầu
pháp lý, kiểm soát dữ liệu tuyệt đối): (1) **tokenizer** BPE byte-level train trên dữ liệu tiếng Việt thật, vocab 32k-64k, đo token
mỗi âm tiết (module 04) vì đó là chi phí inference; (2) **kiến trúc** kiểu Llama: pre-norm RMSNorm, RoPE base lớn để còn kéo context,
SwiGLU, GQA 4-8 kv head để KV cache nhỏ, tie embedding nếu model dưới 2B; (3) **cỡ model** chọn theo chi phí phục vụ, không theo
Chinchilla: model 1-3B train lâu hơn 20 token/tham số chạy được trên một GPU 24 GB sau khi quantize; (4) **dữ liệu**: lọc chất lượng,
khử trùng lặp, tách tập đánh giá trước, đo bằng bpc trên tập giữ lại và bằng benchmark tác vụ thật; (5) **thử nhỏ trước**: chạy
một loạt model nhỏ như bài Intermediate 03 để khớp scaling law và chọn learning rate, rồi mới chạy lớn; (6) theo dõi loss spike,
lưu checkpoint thường xuyên. Phục vụ: quantize int4/int8, vLLM hoặc llama.cpp, đo độ trễ và VRAM thật.

## Case: loss pretrain đang giảm đều thì nhảy vọt lên (loss spike) ở bước 40 000 rồi không về lại. Bạn làm gì?

Dừng, đừng chờ. Xem log quanh bước đó: grad norm (thường tăng vọt trước loss), learning rate (vừa hết warmup? schedule bị đặt
sai?), batch dữ liệu ngay trước (đoạn rác, chuỗi lặp dài, ký tự lạ, tài liệu cực dài), giá trị activation và attention logit lớn
nhất từng tầng (logit attention phình là nguyên nhân hay gặp, chữa bằng QK-norm hoặc logit soft-capping), dtype (fp16 tràn, nên
dùng bf16). Cách xử lý thực tế của các đội pretrain lớn (OPT, PaLM): quay về checkpoint vài trăm bước trước spike, **bỏ qua** các
batch nghi ngờ, giảm learning rate, rồi chạy tiếp; thêm clip grad norm, z-loss cho logit output, kiểm Adam epsilon và beta2 (0.95
ổn định hơn 0.999 ở LLM). Ghi lại để biết spike có lặp lại ở cùng dữ liệu không.

## Khi nào một AI Engineer cần hiểu kiến trúc tới mức này, khi phần lớn công việc là gọi API?

Khi phải ra quyết định mà API không quyết hộ: chọn model mở nào chạy được trên GPU có sẵn (đếm tham số, KV cache, GQA, MoE nghĩa là
VRAM bao nhiêu), vì sao context dài làm chậm và đắt (prefill bậc hai, cache tuyến tính), vì sao quantize model này dễ còn model kia
khó (module 10), LoRA gắn vào lớp nào (module 14), vì sao tokenizer làm tiếng Việt đắt hơn tiếng Anh, vì sao model "quên" phần giữa
của context dài, và khi debug: lặp từ do sampling hay do model, mất chất lượng sau khi chuyển checkpoint do quy ước RoPE hay do
tokenizer. Hiểu kiến trúc biến những câu hỏi đó từ đoán mò thành phép tính.
