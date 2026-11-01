# Câu hỏi phỏng vấn: Fine-tuning LLM

## Khi nào bạn fine-tune, khi nào dùng prompt hoặc RAG?

Bắt đầu bằng câu hỏi: model sai vì thiếu **kiến thức** hay thiếu **hành vi**?

- Thiếu kiến thức (tài liệu nội bộ, dữ liệu mới, cần trích nguồn): RAG hoặc tool. Fine-tune để nạp kiến thức không trích
  nguồn được, lỗi thời khi dữ liệu đổi, và model vẫn bịa ở chỗ nhớ không chắc.
- Thiếu hành vi (định dạng, văn phong, kỹ năng hẹp, dùng tool, độ dài): thử prompt tốt hơn và structured output trước,
  **đo** trên một tập ghim. Chỉ fine-tune khi prompt không đạt, hoặc khi đạt nhưng bằng model quá đắt, quá chậm, và bạn có
  vài trăm tới vài nghìn mẫu sạch có giấy phép.

Fine-tune hay đi kèm RAG chứ không thay nó: fine-tune embedding model cho retrieval tốt hơn, hoặc fine-tune generator để
luôn trả lời đúng khuôn có trích dẫn. Ứng viên tốt nêu cả baseline cần đánh bại và cách đo trước khi train, và nhắc chi
phí sở hữu: mỗi lần model gốc ra bản mới, adapter phải train và đánh giá lại.

## Giải thích LoRA. Vì sao B khởi tạo bằng 0 và hệ số alpha / r để làm gì?

LoRA giữ $$W$$ đóng băng và học cập nhật hạng thấp $$\Delta W = \frac{\alpha}{r} B A$$ với $$A \in \mathbb R^{r \times d_{in}}$$,
$$B \in \mathbb R^{d_{out} \times r}$$, $$r$$ nhỏ (8 tới 64). Mỗi lớp thêm $$r(d_{in} + d_{out})$$ tham số thay vì $$d_{in} d_{out}$$:
với Qwen2.5-7B, r = 16 trên cả 7 lớp tuyến tính là khoảng 40 triệu tham số, 0.53% model.

- $$B = 0$$ để $$\Delta W = 0$$ lúc đầu: model sau khi gắn adapter cho đúng output cũ, train bắt đầu từ model đã tốt. $$A$$ phải
  ngẫu nhiên, vì gradient của $$A$$ tỉ lệ với $$B$$ và ngược lại: cả hai bằng 0 thì không bao giờ học. Ở bước đầu chỉ $$B$$
  nhận gradient.
- $$\alpha / r$$ giữ độ lớn cập nhật gần như không đổi khi đổi $$r$$, nên không phải dò lại learning rate mỗi lần đổi hạng.
  Với $$r$$ lớn, rsLoRA đề xuất $$\alpha / \sqrt r$$.

Sau train có thể merge $$W \leftarrow W + \frac{\alpha}{r} B A$$: model có đúng kiến trúc gốc, phục vụ không thêm độ trễ.

## LoRA hay full fine-tune? Khi nào bạn chọn full fine-tune?

LoRA: bộ nhớ chỉ cần trọng số đóng băng + gradient và optimizer cho vài phần trăm tham số; adapter nhỏ, nhiều adapter dùng
chung một model gốc; ít quên năng lực cũ hơn vì cập nhật bị ràng buộc hạng thấp. Với SFT hành vi trên dữ liệu vừa phải,
LoRA trên mọi lớp tuyến tính thường gần full fine-tune.

Full fine-tune khi: thay đổi lớn và nhiều dữ liệu (continued pretraining trên ngôn ngữ hoặc miền mới, hàng tỉ token), model
nhỏ đủ để bộ nhớ không là vấn đề, hoặc đo thấy LoRA bị chặn chất lượng ở tác vụ của bạn. Cái giá: bộ nhớ AdamW cỡ
12 tới 16 byte mỗi tham số, mỗi phiên bản là một bản sao đầy đủ, và dễ catastrophic forgetting hơn.

## QLoRA hoạt động thế nào? Gradient đi qua trọng số 4 bit bằng cách nào?

QLoRA lưu trọng số đóng băng ở NF4 (16 mức theo phân vị phân phối chuẩn, scale absmax theo khối 64), lượng tử hoá luôn
các scale bằng 8 bit (double quantization, chi phí scale từ 0.5 xuống khoảng 0.127 bit mỗi tham số), và để trạng thái
optimizer ở bộ nhớ phân trang để không OOM khi có đỉnh.

Trọng số 4 bit không được train: khi forward, bitsandbytes giải lượng tử từng khối về bf16 rồi nhân; backward tính
gradient theo **activation** qua phép nhân đó (dùng lại trọng số đã giải lượng tử), nên gradient chảy tới adapter LoRA ở
tầng trước mà không cần gradient theo trọng số 4 bit. Chỉ adapter bf16 được cập nhật.

Hệ quả vận hành: QLoRA chậm hơn LoRA bf16 (giải lượng tử ở mọi lượt nhân). Model sau train là "4 bit + adapter"; muốn
merge thì merge vào bản bf16 gốc rồi quantize lại cho phục vụ, và đo lại chất lượng sau quantize.

## Ước lượng VRAM để fine-tune Qwen2.5-7B trên một GPU 24 GB. Full, LoRA hay QLoRA?

Tính theo khoản (7.6 tỉ tham số):

- Full fine-tune bf16 + AdamW: trọng số 15 GB + gradient 15 GB + hai trạng thái AdamW 30 GB (bf16) tới 60 GB (fp32): không vừa.
- LoRA bf16: trọng số 15 GB (đóng băng), tham số LoRA r = 16 khoảng 40 triệu × (2 + 2 + 8) byte, khoảng 0.5 GB, cộng
  activation. Vừa 24 GB với batch nhỏ, gradient checkpointing, chuỗi không quá dài.
- QLoRA: trọng số tuyến tính khoảng 3.4 GB ở 4.127 bit, embedding và `lm_head` bf16 khoảng 2 GB (7B không dùng chung hai
  ma trận này), cộng adapter và activation: vừa cả GPU 12 GB.

Activation là khoản khó đoán nhất (tỉ lệ batch × độ dài × số tầng, logits cỡ batch × độ dài × 152 nghìn từ vựng ở fp32).
Câu trả lời tốt kết thúc bằng "đo một bước train với cấu hình thật" thay vì tin hoàn toàn vào ước lượng.

## Trong SFT, vì sao chỉ tính loss trên phần trả lời? Kể vài lỗi dựng label bạn từng gặp.

Mục tiêu là dạy model **trả lời**, không dạy nó đoán system prompt và câu hỏi. Với bài ngắn, phần trả lời có khi chỉ vài
phần trăm số token; tính loss trên cả chuỗi thì gradient bị phần prompt chi phối, loss trông thấp mà hành vi học được kém.

Lỗi hay gặp:

- Tự dịch label một vị trí, trong khi model Hugging Face đã tự dịch: model học đoán token cách hai bước.
- Bỏ token kết thúc lượt (`<|im_end|>`) khỏi label: model fine-tune xong không biết dừng.
- Pad bằng `eos` và để pad trong label: model học sinh hàng loạt `eos` hoặc, ngược lại, không học được `eos` thật vì nó bị
  mask cùng pad.
- Tokenize từng message rồi nối, hoặc thêm BOS hai lần: lệch với chuỗi lúc serve.
- Template lúc train khác lúc serve (sửa tay một dấu xuống dòng): model vẫn chạy, chỉ kém đi, lỗi im lặng.

Cách bắt: in chuỗi đã decode của các token có label cho vài mẫu, và viết test so loss của model với cross-entropy tính tay.

## Padding, packing và padding-free khác nhau thế nào?

- **Padding**: mỗi batch pad tới mẫu dài nhất; đơn giản, lãng phí khi độ dài lệch. Batch theo độ dài (xếp mẫu theo độ dài,
  gom theo ngân sách token) giảm lãng phí mà không đổi ngữ nghĩa.
- **Packing**: nối nhiều mẫu vào một khối dài cố định, không còn pad. Nhưng với attention thông thường, mẫu sau nhìn thấy
  mẫu trước: `position_ids` đếm lại từ 0 không chặn attention. Đo trên Qwen2.5-0.5B ở mục 2 lý thuyết: loss của mẫu sau
  khi đứng một mình và khi nối sau mẫu khác khác nhau, chỉ mask khối chéo mới khớp.
- **Padding-free / varlen**: nối mọi mẫu thành một chuỗi và đưa ranh giới cho kernel (FlashAttention varlen); không pad,
  không rò. TRL gọi là `padding_free`.

Chọn: padding + batch theo độ dài khi dữ liệu vừa phải; packing khi chấp nhận rò nhỏ hoặc có mask khối; padding-free khi
có kernel hỗ trợ.

## Bạn chuẩn bị một bộ instruction tải từ Hugging Face thế nào trước khi train?

1. Đọc giấy phép ở ba tầng: bộ dữ liệu, model đã sinh câu trả lời (GPT-4, Claude...), nguồn câu hỏi gốc.
2. Đọc tận mắt vài chục mẫu mỗi nguồn; tìm lỗi hệ thống (trường rỗng, system prompt hỏng do dịch máy).
3. Chuẩn hoá Unicode (NFC), khoảng trắng; đưa về `messages`.
4. Khử trùng chính xác bằng hash nội dung đã chuẩn hoá; khử gần trùng bằng MinHash + LSH, **kiểm lại** ước lượng Jaccard
   trước khi gộp (văn bản cùng khuôn chạm nhau rất dễ).
5. Lọc độ dài theo đúng tokenizer và chat template; bỏ mẫu quá dài thay vì cắt cụt.
6. Chia train/validation theo nhóm (nguồn, cụm gần trùng) bằng hash, không random từng mẫu.
7. Kiểm nhiễm bẩn với mọi tập đánh giá (n-gram), đọc cái gì trùng.

Ứng viên tốt nhắc: chất lượng hơn số lượng (LIMA: 1 000 mẫu chọn kỹ), và dữ liệu phải giống phân phối lúc dùng thật.

## Dẫn ra loss của DPO. Beta và reference model đóng vai trò gì?

RLHF tối đa $$\mathbb E[r] - \beta\,\mathrm{KL}(\pi \| \pi_{\text{ref}})$$, nghiệm đóng $$\pi^* \propto \pi_{\text{ref}}\exp(r/\beta)$$. Đảo lại:
$$r = \beta\log\frac{\pi^*}{\pi_{\text{ref}}} + \beta\log Z(x)$$. Thế vào Bradley-Terry cho cặp $$(y_w, y_l)$$, $$\log Z$$ triệt tiêu:

$$
\mathcal L = -\log\sigma\left(\beta\log\frac{\pi_\theta(y_w \mid x)}{\pi_{\text{ref}}(y_w \mid x)} - \beta\log\frac{\pi_\theta(y_l \mid x)}{\pi_{\text{ref}}(y_l \mid x)}\right)
$$

- $$\beta$$ là độ chặt của ràng buộc KL: lớn thì policy bám reference, nhỏ thì đi xa và dễ khai thác chỗ sai của dữ liệu
  ưu tiên. Gradient mỗi cặp có trọng số $$\sigma(-\beta h)$$: cặp đang xếp sai được đẩy mạnh.
- Reference (thường là model SFT, đóng băng) neo policy và làm reward ngầm có nghĩa. Bỏ reference là thành một loss xếp
  hạng thuần, model dễ đẩy cả hai câu xuống thấp và trôi khỏi phân phối.

Dấu hiệu cài đúng: loss bước đầu bằng $$\log 2$$ vì policy trùng reference.

## DPO khác PPO (RLHF) thế nào? Khi nào vẫn cần RL?

DPO: không reward model, không sinh văn bản trong vòng train, hai model trong bộ nhớ (policy, reference; với LoRA chỉ một
model và tắt adapter làm reference), ổn định, dễ chạy. Nhưng nó **offline**: chỉ học trên cặp có sẵn, không khám phá câu
trả lời mới, và tối ưu xác suất tương đối nên có thể làm giảm log-prob của cả câu tốt.

PPO và RL nói chung (GRPO ở module 15): sinh câu trả lời mới trong lúc train và chấm bằng reward model hoặc checker, nên
khám phá được; tốn bộ nhớ (tới bốn model), chậm, nhạy siêu tham số. Cần RL khi reward **kiểm được** (toán, code, định dạng
có checker) và muốn model vượt xa dữ liệu mẫu, hoặc khi cặp ưu tiên offline đã cạn tín hiệu. Thực tế nhiều pipeline:
SFT → DPO (hoặc biến thể) cho văn phong và an toàn → RL có reward kiểm được cho suy luận.

## Bạn dựng cặp ưu tiên cho DPO từ đâu khi không có người gán nhãn?

- **Đáp án mẫu + lỗi của chính model (on-policy)**: chạy model sau SFT, output nào checker đánh sai thành câu bị loại,
  đáp án vàng thành câu được chọn. Sát lỗi thật của model; chỉ dùng được khi có checker.
- **Đáp án mẫu + bản làm hỏng**: đổi nhãn, phá định dạng, cắt câu. Rẻ, nhưng lỗi nhân tạo có thể quá dễ phân biệt, model
  học nhận ra kiểu hỏng chứ không học sửa lỗi thật.
- **Nhiều mẫu từ model, chấm bằng LLM-as-judge**: thừa hưởng thiên vị của judge (câu dài, giọng tự tin).

Luôn nói rõ giới hạn và có đối chứng công bằng: DPO trên $$n$$ cặp so với SFT thêm trên cùng dữ liệu. Nếu SFT thêm cho kết
quả bằng hoặc hơn, DPO không đáng độ phức tạp.

## Loss validation giảm đều nhưng người dùng nói model tệ hơn. Bạn kiểm tra gì?

- **Loss đo cái gì**: phần trả lời hay cả chuỗi? Validation có lọt bản gần trùng của train không (chia theo mẫu thay vì
  theo nhóm)? Perplexity thấp hơn có thể chỉ là model giống **văn phong** dữ liệu hơn.
- **Thước đo tác vụ**: có một bộ đo kiểm được bằng code (định dạng, exact-match, F1) trên tập ghim không? So với baseline
  prompt mạnh nhất, không phải baseline yếu.
- **Phân phối**: dữ liệu train có giống câu hỏi thật của người dùng không (độ dài, chủ đề, ngôn ngữ)?
- **Quên**: chạy lại các bộ đo năng lực chung cũ; fine-tune hẹp có thể làm hỏng kỹ năng khác (catastrophic forgetting).
- **Serve khác train**: chat template, system prompt, tham số sinh (temperature, `max_tokens`), quantize sau khi merge.

## Model sau fine-tune trả lời đúng nội dung nhưng không dừng, lặp lại hoặc tự viết thêm lượt "user". Nguyên nhân?

Gần như luôn là token kết thúc lượt:

- Label không chứa token kết thúc lượt (`<|im_end|>` với Qwen, `<|eot_id|>` với Llama 3), nên model không học dừng.
- `pad_token` trùng `eos_token` và pad bị mask, kéo theo token kết thúc thật cũng bị mask.
- Template lúc train khác lúc serve, hoặc `generation_config` thiếu id kết thúc lượt trong `eos_token_id`.
- Dữ liệu bị cắt cụt ở độ dài tối đa: model thấy nhiều câu trả lời không có kết thúc.

Debug: decode các token có label của vài mẫu để thấy token kết thúc có mặt; kiểm `generation_config.eos_token_id`; sinh
với vài prompt ngắn và in cả token đặc biệt.

## Thiết kế hệ thống: phân loại ticket hỗ trợ khách hàng tiếng Việt, 50 nghìn ticket mỗi ngày, cần JSON ổn định và chi phí thấp.

Khung trả lời:

1. **Baseline**: model API lớn hoặc model mở 7B với prompt + JSON Schema trên 300 ticket gán nhãn tay (tập ghim, chia theo
   khách hàng/thời gian). Đo F1 từng nhãn, tỉ lệ JSON hợp lệ, độ trễ p95, chi phí mỗi nghìn ticket.
2. **Dữ liệu**: vài nghìn ticket đã được nhân viên xử lý (nhãn có sẵn trong hệ thống), làm sạch PII, khử trùng lặp, chia
   theo khách hàng để không lọt; nhãn hiếm được lấy mẫu thêm.
3. **Model**: SFT LoRA trên model nhỏ (0.5B tới 3B) vì tác vụ hẹp, nhãn nhiều; output chỉ là JSON ngắn nên token ra ít.
   Cân nhắc DPO trên lỗi còn lại nếu có checker phân biệt được.
4. **Đánh giá**: so trên tập ghim với baseline mạnh nhất, ngoài nhiễu; thêm bộ hồi quy các ticket khó.
5. **Phục vụ**: merge adapter, quantize (module 10), server batch (module 20); hoặc multi-LoRA nếu mỗi phòng ban một adapter.
   Constrained decoding vẫn bật làm bảo hiểm định dạng.
6. **Vận hành**: giám sát phân phối nhãn và tỉ lệ JSON lỗi, lấy mẫu ticket để người kiểm hằng tuần, train lại theo lịch
   khi nhãn trôi; ghi lại phiên bản dữ liệu, template, adapter.

Ứng viên tốt nói rõ con số nào quyết định (chi phí và độ trễ ở 50 nghìn ticket/ngày) và khi nào **không** fine-tune
(baseline prompt đã đạt và chi phí chấp nhận được).

## Thiết kế hệ thống: trợ lý pháp luật cho người dân. Fine-tune ở đâu trong hệ thống, ở đâu không?

- **Không** fine-tune để nạp văn bản luật: hàng chục nghìn điều luật, thay đổi hằng tuần, cần trích dẫn chính xác và hiệu
  lực. Đó là việc của RAG có metadata hiệu lực (module 13). Bài Advanced 02 của module đo điều này: model fine-tune thuộc
  câu đã thấy nhưng không trích đúng điều cho câu mới.
- **Fine-tune embedding model** trên cặp (câu hỏi, điều luật) của split train, chia theo câu hỏi, kiểm không lọt điều của
  tập đánh giá: thường là cải thiện lớn nhất cho retrieval tiếng Việt chuyên ngành (capstone milestone 5).
- **Fine-tune generator** (LoRA) cho hành vi: luôn trả lời theo khuôn "Căn cứ ... thì ...", trích `[i]` đúng định dạng, từ
  chối đúng câu khi thiếu căn cứ. Dữ liệu: câu trả lời mẫu do luật sư duyệt; DPO trên cặp (trả lời có trích dẫn đúng, trả
  lời bịa hoặc từ chối sai) nếu có checker trích dẫn.
- **Đánh giá**: retrieval (recall@k, MRR), tỉ lệ trích dẫn đúng điều, tỉ lệ từ chối đúng/sai, kiểm bởi người với mẫu ngẫu
  nhiên; không dùng LLM-as-judge làm thước đo duy nhất.
- **Rủi ro**: model fine-tune tự tin hơn khi sai; luôn hiển thị nguồn, cập nhật index khi luật đổi, ghi phiên bản.

## Phục vụ 20 adapter LoRA cho 20 khách hàng trên một cụm GPU. Bạn làm thế nào?

- Không merge: một model gốc trong VRAM, 20 adapter vài chục MB. Server multi-LoRA (vLLM, các server tương đương) gộp
  request của nhiều adapter trong cùng batch, áp nhánh LoRA theo từng request.
- Giới hạn số adapter nạp sẵn trên GPU, phần còn lại ở RAM, nạp theo LRU; đo độ trễ khi đổi adapter.
- Cùng model gốc và cùng `r`/lớp đích giúp batch hiệu quả hơn; adapter khác hạng vẫn chạy nhưng kernel kém tối ưu.
- Khi một khách hàng chiếm phần lớn lưu lượng, merge riêng adapter đó thành một deployment riêng để bỏ chi phí nhánh LoRA.
- Vận hành: định danh adapter trong mọi log và trace, đánh giá từng adapter trước khi nạp, rollback theo phiên bản adapter,
  và train lại toàn bộ khi model gốc đổi.
