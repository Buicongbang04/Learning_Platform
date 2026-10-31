# Câu hỏi phỏng vấn: LLM & model mã nguồn mở

## Pre-trained model là gì? Base model và instruct model khác nhau thế nào, khi nào dùng cái nào?

Pre-trained model là model đã được train sẵn trên lượng dữ liệu khổng lồ (với LLM: hàng nghìn tỉ token văn bản) bằng
mục tiêu tự giám sát, với LLM decoder-only là **dự đoán token tiếp theo**. Bạn dùng lại trọng số đó thay vì train từ
đầu, thứ mà gần như không công ty nào ngoài vài phòng lab tự làm nổi.

- **Base model** (vd. `Qwen/Qwen2.5-7B`) chỉ học nối tiếp văn bản. Hỏi "Thủ đô Việt Nam là gì?" nó có thể sinh tiếp
  thêm ba câu hỏi nữa, như một trang đề thi. Dùng khi: fine-tune cho tác vụ riêng, few-shot completion, nghiên cứu,
  hoặc cần phân phối "thô" chưa bị chỉnh.
- **Instruct / chat model** (vd. `Qwen2.5-7B-Instruct`) là base model đã qua SFT trên hội thoại và thường thêm
  preference tuning (RLHF, DPO). Nó theo chỉ dẫn, dừng đúng chỗ, từ chối yêu cầu nguy hiểm, và **chỉ hoạt động tốt
  với đúng chat template** đã dùng lúc fine-tune.

Ứng viên tốt nhắc thêm: instruct model không "biết nhiều hơn" base model, nó chỉ được dạy cách trả lời. Kiến thức gần
như hoàn toàn đến từ pre-training.

## Nêu các giới hạn của LLM pre-trained mà một AI Engineer phải thiết kế xung quanh.

| Giới hạn | Hệ quả | Cách xử lý |
| --- | --- | --- |
| Knowledge cut-off | Không biết sự kiện sau ngày dữ liệu train dừng; trả lời tự tin bằng thông tin cũ | RAG, tool/search, ghi ngày hiện tại vào prompt |
| Hallucination | Bịa chi tiết nghe hợp lý | Grounding bằng nguồn, trích dẫn, kiểm chứng, cho phép "không biết" |
| Context length hữu hạn | Prompt dài bị cắt hoặc lỗi; chất lượng giảm ở giữa context dài | Đếm token, chunking, tóm tắt lịch sử, chọn model context dài |
| Không xác định (sampling) | Cùng câu hỏi ra câu trả lời khác | temperature 0 hoặc thấp, seed, structured output, eval nhiều lần |
| Tính toán, đếm chính xác kém | Sai số học, đếm ký tự sai (do tokenizer) | Tool gọi code/calculator |
| Chi phí, độ trễ theo token | Hoá đơn và latency tăng tuyến tính theo độ dài | Model nhỏ hơn, cache, cắt prompt |
| Thiên kiến, an toàn | Kết quả lệch, bị prompt injection | Guardrail, red-teaming (module 19) |

Điểm cộng: nói được rằng tokenizer là gốc của nhiều lỗi "ngớ ngẩn" (đếm chữ cái, đảo chuỗi), và rằng tiếng Việt tốn
nhiều token hơn tiếng Anh nên giới hạn context và chi phí đến sớm hơn.

## Knowledge cut-off là gì và làm sao biết cut-off của một model?

Là thời điểm dữ liệu pre-training dừng thu thập. Sau mốc đó model không có thông tin, và quan trọng hơn: **nó không
biết là nó không biết**, nên vẫn trả lời bằng kiến thức cũ.

Cách biết: model card hoặc docs của nhà cung cấp (nguồn đáng tin nhất, nhiều model đóng công bố rõ); hỏi chính model
thì **không đáng tin** (model hay đoán sai mốc của chính mình vì dữ liệu gần mốc cut-off thưa); thăm dò bằng câu hỏi
về sự kiện có ngày rõ ràng theo từng tháng và xem độ chính xác rơi ở đâu (có ích khi model card không ghi).

Hệ quả thiết kế: với domain thay đổi nhanh (luật, giá, sản phẩm), đừng dựa vào kiến thức trong trọng số; đưa dữ liệu
vào lúc hỏi bằng RAG hoặc tool, và đưa **ngày hiện tại** vào system prompt.

## Context length là gì? "Model hỗ trợ 128k token" có nghĩa là bạn dùng được 128k token không?

Context length là số token tối đa (prompt + câu trả lời) model xử lý trong một lần gọi, giới hạn bởi cách train vị
trí (RoPE, cửa sổ train) và bộ nhớ. Con số quảng cáo là **trần lý thuyết**, thực tế bị giới hạn bởi:

- **Cấu hình runtime**: Ollama nạp model với `num_ctx` mặc định nhỏ hơn nhiều (máy của track: `qwen2.5:3b` hỗ trợ
  32 768 nhưng nạp với 4 096) và **cắt prompt dài mà không báo lỗi**. Đo ở bài Intermediate 02: prompt khoảng 6 000
  token bị cắt còn 4 096, model trả lời sai.
- **Bộ nhớ**: KV cache tăng tuyến tính theo context; 32k token có thể tốn nhiều VRAM hơn chính trọng số Q4 (với model
  MHA như Phi-3 mini: 1.5 GiB cho mỗi 4 096 token).
- **Chất lượng**: model dùng thông tin ở giữa context dài kém hơn ở đầu và cuối ("lost in the middle"); khả năng
  thật đo bằng needle-in-a-haystack hoặc benchmark như RULER, không phải bằng con số trên model card.
- **Chi phí, độ trễ**: thời gian xử lý prompt tăng theo độ dài; API tính tiền từng token input.

## Temperature, top-k, top-p hoạt động thế nào? Bạn đặt chúng ra sao cho từng loại tác vụ?

Model trả logits $$z$$ cho mọi token. Temperature chia logits trước softmax:
$$p_i = \frac{e^{z_i/T}}{\sum_j e^{z_j/T}}$$. $$T < 1$$ làm phân phối nhọn (ít đa dạng), $$T > 1$$ làm phẳng,
$$T \to 0$$ là greedy. Top-k giữ $$k$$ token xác suất cao nhất. Top-p (nucleus) giữ tập nhỏ nhất có tổng xác suất
$$\ge p$$: số token giữ lại **thích nghi** theo độ chắc chắn của model ở từng bước, nên thường tốt hơn top-k cố định.
Hugging Face áp theo thứ tự penalty, temperature, top-k, top-p.

| Tác vụ | Cấu hình gợi ý |
| --- | --- |
| Trích xuất, phân loại, code, JSON | $$T = 0$$ (hoặc 0.1), cộng structured output |
| Hỏi đáp có nguồn (RAG) | $$T$$ 0 tới 0.3 |
| Chat thông thường | $$T$$ 0.7, top-p 0.8 tới 0.95 (Qwen2.5 khuyên 0.7 / 0.8 / top-k 20) |
| Sáng tác, brainstorm, sinh dữ liệu đa dạng | $$T$$ 0.9 tới 1.2, top-p 0.95 |

Lưu ý: $$T = 0$$ trên API không đảm bảo tất định tuyệt đối (batching, phần cứng khác nhau làm phép cộng float khác
thứ tự); cần thì đặt `seed` và chấp nhận dao động nhỏ.

## Repetition penalty khác presence/frequency penalty thế nào?

- **Repetition penalty** (CTRL, Hugging Face, `repeat_penalty` của llama.cpp/Ollama): với mỗi token đã xuất hiện,
  logit dương chia cho $$\theta$$, logit âm nhân với $$\theta$$ (nhân với số > 1 làm logit âm càng âm). Không phụ
  thuộc số lần lặp. $$\theta = 1$$ là tắt.
- **Presence / frequency penalty** (OpenAI API): trừ thẳng vào logit: $$z_j - \alpha_p \mathbb{1}[c_j > 0] - \alpha_f c_j$$.
  Frequency tăng theo số lần token đã xuất hiện; presence chỉ một lần. 0 là tắt.

Bẫy: viết repetition penalty chỉ bằng phép chia làm logit âm **tăng** về 0, tức là thưởng cho lặp lại. Và penalty
phạt cả dấu câu, từ chức năng, nên đặt cao làm câu văn méo.

## Model đóng và model mở: so sánh và cách bạn chọn cho một dự án.

| Tiêu chí | Đóng (OpenAI, Anthropic Claude, Google Gemini, Mistral API, Cohere) | Mở trọng số (Qwen, Llama, Gemma, Mistral, DeepSeek, Phi) |
| --- | --- | --- |
| Chất lượng đỉnh | Thường dẫn đầu ở tác vụ khó, đa phương thức, context dài | Khoảng cách thu hẹp, model mở lớn rất mạnh; model nhỏ chạy local kém hơn rõ |
| Chi phí | Theo token, không đầu tư hạ tầng | Hạ tầng GPU, vận hành; rẻ khi lưu lượng lớn và ổn định |
| Dữ liệu, tuân thủ | Dữ liệu rời khỏi hạ tầng của bạn (có điều khoản, region) | Dữ liệu ở lại on-prem, hợp với dữ liệu nhạy cảm |
| Kiểm soát | Model đổi/ngừng theo nhà cung cấp, rate limit | Ghim phiên bản, fine-tune, quantize, sửa template |
| Độ trễ | Phụ thuộc mạng và tải của nhà cung cấp | Tự tối ưu được, chạy offline, edge |
| Giấy phép | Điều khoản dịch vụ | **Đọc kỹ**: Apache-2.0 / MIT tự do; Llama, Gemma có điều khoản riêng; `qwen2.5:3b` mang giấy phép `qwen-research` (không thương mại) dù `qwen2.5:7b` là Apache-2.0 |

Cách chọn: bắt đầu bằng model đóng mạnh để chứng minh bài toán làm được và có tập eval; rồi thử model mở nhỏ hơn
trên **cùng tập eval** khi chi phí, độ trễ, quyền riêng tư hoặc offline là ràng buộc. Thiết kế qua một lớp trừu tượng
(OpenAI-compatible API, `llmkit`) để đổi model không phải viết lại ứng dụng.

## "Open source" và "open weights" khác nhau thế nào?

Open source theo nghĩa chặt (OSI, Open Source AI Definition) đòi đủ để **tái tạo**: code train, mô tả đầy đủ dữ liệu
và quyền dùng, sửa, phân phối không hạn chế mục đích. Phần lớn model "mở" phổ biến chỉ là **open weights**: công bố
trọng số và code inference, không công bố dữ liệu train, đôi khi kèm giấy phép giới hạn (ngưỡng người dùng hằng tháng,
cấm dùng output để train model khác, không thương mại). Ví dụ có đủ dữ liệu và code: OLMo (AI2), Pythia (EleutherAI).

Hệ quả thực tế: kiểm `license` trong model card (và cả tag riêng của từng biến thể, như `qwen2.5:3b` khác `qwen2.5:7b`)
trước khi đưa vào sản phẩm thương mại; không biết dữ liệu train thì khó đánh giá rò rỉ benchmark và thiên kiến.

## Bạn tìm và đánh giá một model mở trên Hugging Face Hub thế nào?

1. **Lọc** theo task (`pipeline_tag`, vd. text-generation), ngôn ngữ, giấy phép, kích thước; sắp theo downloads,
   likes, trending. Xem các leaderboard có cùng loại tác vụ, nhưng coi chúng là điểm khởi đầu.
2. **Đọc model card**: base model, dữ liệu, ngôn ngữ hỗ trợ, context length, chat template, giới hạn, giấy phép, cách
   đánh giá. Card nghèo nàn là dấu hiệu rủi ro.
3. **Đọc `config.json`**: số tầng, head, KV head, vocab, `max_position_embeddings` để ước lượng VRAM và KV cache.
4. **Kiểm định dạng**: `safetensors` (an toàn, không chạy code khi nạp) thay vì `.bin` pickle; GGUF cho llama.cpp/Ollama;
   repo yêu cầu `trust_remote_code` thì đọc code trước khi chạy. Repo gated (Llama, Gemma) cần đồng ý điều khoản và token.
5. **Đo trên dữ liệu của bạn**: tập eval nhỏ (50 tới 200 mẫu có nhãn), so 2 tới 4 model ứng viên về chất lượng, độ trễ
   p50/p95, bộ nhớ. Benchmark công khai không thay được bước này, nhất là với tiếng Việt.

## Ước lượng VRAM để chạy một LLM. Qwen2.5-7B có chạy được trên GPU 4 GB không?

Bộ nhớ ≈ trọng số + KV cache + phần dư.

- Trọng số = số tham số × byte/tham số: fp16/bf16 2 byte, int8 1, Q4_K_M khoảng 5 bit (đo trên GGUF của Ollama).
- KV cache = $$2 \cdot L \cdot h_{kv} \cdot d_{head} \cdot n_{ctx} \cdot B \cdot \text{byte}$$.
- Phần dư (activation, buffer, CUDA context): thường thêm 10 tới 20%, cộng vài trăm MB cố định.

Qwen2.5-7B: 7.62 tỉ tham số, Q4_K_M khoảng 4.43 GiB chỉ riêng trọng số, nên **không vừa** GPU 4 GB. Ollama vẫn chạy
được bằng cách đặt một phần tầng trên CPU (partial offload), đổi lại tốc độ sinh giảm mạnh vì băng thông RAM CPU thấp
hơn VRAM nhiều lần. Phương án: model 3B Q4 (khoảng 1.8 GiB trọng số), hoặc GPU 12 GB, hoặc API.

## Vì sao sinh token chậm hơn đọc prompt nhiều lần? KV cache giúp gì?

**Prefill** (đọc prompt) xử lý mọi token prompt song song trong một lượt: phép nhân ma trận lớn, GPU chạy gần hết công
suất (compute-bound). **Decode** sinh từng token một: mỗi token phải đọc **toàn bộ trọng số** từ bộ nhớ để làm vài phép
nhân vector, nên bị giới hạn bởi băng thông bộ nhớ (memory-bound). Vì vậy tốc độ đọc prompt thường gấp hàng chục lần
tốc độ sinh, và token/s khi decode xấp xỉ băng thông bộ nhớ chia kích thước model.

KV cache lưu K, V của các token đã xử lý, nên mỗi bước decode chỉ tính cho token mới thay vì chạy lại cả chuỗi. Không
cache, chi phí một bước tăng theo độ dài chuỗi và tổng chi phí sinh $$n$$ token tăng cỡ bình phương. Cái giá là bộ nhớ
(công thức ở câu trên), lý do các kiến trúc mới dùng GQA, MQA (module 05) và lý do các server như vLLM quản lý KV cache
theo trang (PagedAttention).

## Ollama là gì, chạy model thế nào, và bạn dùng nó trong sản phẩm ra sao?

Ollama là server chạy LLM local dựa trên llama.cpp: model đóng gói dạng GGUF (thường đã quantize, vd. Q4_K_M), quản lý
bằng tên và tag (`qwen2.5:3b`), cấu hình bằng **Modelfile** (`FROM`, `PARAMETER`, `SYSTEM`, `TEMPLATE`), phục vụ qua
REST (`/api/chat`, `/api/generate`, `/api/embed`, stream NDJSON) và endpoint tương thích OpenAI (`/v1/chat/completions`).

Dùng tốt cho: phát triển và test offline, prototype, ứng dụng nội bộ ít người dùng, máy cá nhân, edge. Những điều cần
biết khi dựa vào nó: `num_ctx` mặc định nhỏ và cắt prompt im lặng; một model nạp với `num_ctx` khác là nạp lại;
`keep_alive` quyết định model ở lại bộ nhớ bao lâu (lần gọi đầu sau khi hết hạn chịu thêm thời gian load); song song
nhiều request bị giới hạn (`OLLAMA_NUM_PARALLEL`). Phục vụ nhiều người dùng đồng thời với throughput cao thì dùng
server có continuous batching (vLLM, TGI, SGLang, llama.cpp server) (module 20).

## Case: Một công ty luật muốn chatbot tư vấn nội bộ, dữ liệu hồ sơ khách hàng không được rời khỏi văn phòng, ngân sách một máy GPU 24 GB. Bạn chọn model và kiến trúc thế nào?

1. **Ràng buộc trước**: dữ liệu on-prem, nên model đóng qua API bị loại (trừ khi có triển khai riêng có hợp đồng);
   chọn model mở trọng số chạy local. Kiểm giấy phép cho phép dùng thương mại (Apache-2.0 như Qwen2.5-7B/14B, hoặc
   điều khoản Llama/Gemma).
2. **Kích thước**: 24 GB vừa model 14B ở Q4/Q5 (khoảng 9 tới 10 GB) hoặc 7-8B ở Q8, còn chỗ cho KV cache của context
   16-32k token và vài request đồng thời. Ước lượng bằng công thức VRAM, rồi đo thật.
3. **Kiến thức luật** không nằm trong trọng số đáng tin (cut-off, hallucination): kiến trúc RAG trên văn bản pháp luật
   và hồ sơ nội bộ, có phân quyền theo người dùng ở tầng retrieval, trích dẫn nguồn (module 13).
4. **Chọn model bằng đo**: tập eval 100 tới 200 câu hỏi thật có đáp án do luật sư duyệt; so 2 tới 3 ứng viên (vd.
   Qwen2.5-7B, Qwen2.5-14B, một model fine-tune tiếng Việt) về độ chính xác, trích dẫn đúng, độ trễ p95.
5. **Serving**: vLLM hoặc llama.cpp server nếu nhiều người dùng đồng thời; Ollama đủ cho thử nghiệm. Ghim phiên bản
   model, log prompt/đáp án nội bộ để đánh giá, guardrail chống lộ hồ sơ giữa khách hàng.

## Case: Sản phẩm đang gọi GPT-class API, hoá đơn tăng nhanh; sếp muốn "chuyển hết sang model mở tự host". Bạn tiếp cận thế nào?

Không chuyển một lần. Trình tự:

1. **Đo hiện trạng**: phân loại request theo tác vụ (phân loại, trích xuất, tóm tắt, chat tự do), lưu lượng, độ dài
   token in/out, chi phí từng loại. Thường 20% loại tác vụ chiếm 80% chi phí.
2. **Tập eval cho từng loại**, lấy từ log thật (đã ẩn danh), có nhãn hoặc tiêu chí chấm.
3. **Thử model mở nhỏ trên tác vụ đơn giản trước** (phân loại, trích xuất JSON): model 3B-8B quantize thường đủ, có thể
   cộng fine-tune. Giữ API cho tác vụ khó (lập luận dài, đa phương thức).
4. **Tính tổng chi phí sở hữu**: GPU (mua hoặc thuê), điện, vận hành, on-call, độ sẵn sàng, so với giá token. Tự host
   chỉ rẻ khi tải đủ lớn và đều để GPU không ngồi không; tải thất thường thì API hoặc serverless rẻ hơn.
5. **Kiến trúc router**: một lớp gateway OpenAI-compatible định tuyến theo tác vụ và có fallback sang API khi model local
   lỗi hoặc quá tải; theo dõi chất lượng online sau khi chuyển.

Kết quả thường là **lai**, không phải "hết", và quyết định dựa trên số đo của chính hệ thống.
