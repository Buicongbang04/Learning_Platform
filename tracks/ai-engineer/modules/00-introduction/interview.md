# Câu hỏi phỏng vấn: AI Engineer là gì

## AI Engineer khác ML Engineer ở đâu? Bạn tự xếp mình vào đâu?

ML Engineer thường bắt đầu từ **dữ liệu có nhãn của bài toán** và tạo ra **model riêng** (feature, train, đánh giá
offline, pipeline train/serve, chống drift). AI Engineer bắt đầu từ **model nền tảng có sẵn** (LLM, embedding, model đa
phương thức) và tạo ra **tính năng, ứng dụng, agent**: chọn model, thiết kế context (prompt, RAG, tool), dựng bộ eval,
kiểm soát chi phí, độ trễ, an toàn. Vòng lặp của AI Engineer nhanh hơn (bản đầu tính bằng giờ), nhưng bị đo trên những
thứ khó hơn: câu trả lời mở, hallucination, prompt injection.

Câu trả lời tốt không vẽ ranh giới cứng: AI Engineer giỏi vẫn cần nền ML (đánh giá, overfitting với bộ eval nhỏ,
thống kê khi so hai prompt), và chạm sang việc ML Engineer khi phải fine-tune hay distill. Điểm cộng là nói được khi nào
**không** dùng LLM: bài toán dạng bảng có đủ nhãn (churn, chấm điểm tín dụng) thì model gradient boosting rẻ hơn hàng
trăm lần, nhanh hơn và giải thích được hơn.

## Trong một dự án LLM, AI Engineer chịu trách nhiệm những gì?

Theo vòng đời: (1) đóng khung bài toán và chỉ số thành công cùng product; (2) chọn model (API hay tự host, đọc model
card, giấy phép, giới hạn context); (3) thiết kế context: prompt, retrieval, tool; (4) dựng **bộ eval** có nhãn và chạy
nó mỗi khi đổi bất cứ thứ gì; (5) triển khai với giới hạn chi phí, độ trễ p95, guardrail; (6) giám sát: log, phản hồi
người dùng, lỗi mới, rồi đưa trường hợp hỏng vào bộ eval. Người phỏng vấn hay chờ nghe chữ **eval**: ứng viên chỉ nói
về prompt và framework mà không nói cách đo là dấu hiệu chưa từng đưa thứ gì ra production.

## AI và AGI khác nhau thế nào? Một PM hỏi "khi có AGI thì có cần đội mình không?", bạn trả lời ra sao?

Mọi AI đang dùng là AI hẹp theo nghĩa có biên năng lực đo được: giỏi ở việc này, hỏng khó đoán ở việc khác. AGI là AI
có năng lực tổng quát ngang người trên phần lớn công việc trí tuệ; không có định nghĩa thống nhất (OpenAI Charter đo
bằng giá trị kinh tế, "Levels of AGI" của DeepMind dùng hai trục hiệu năng × độ tổng quát).

Với PM, câu trả lời thực dụng: quyết định sản phẩm dựa trên **năng lực đo được hôm nay trên bài toán của mình**, không
dựa trên dự đoán. Biên năng lực "răng cưa" (Dell'Acqua và cộng sự, 2023): trong thí nghiệm với tư vấn viên BCG, GPT-4
giúp ở việc trong biên nhưng làm người dùng **sai nhiều hơn** ở việc ngoài biên vì họ tin câu trả lời nghe hợp lý. Vì vậy
đội cần một bộ eval, chạy lại mỗi khi có model mới: model mạnh hơn làm phần việc của đội thay đổi (ít prompt hack hơn,
nhiều thiết kế hệ thống và đánh giá hơn), không làm nó biến mất.

## Training và inference khác nhau thế nào về chi phí và ai trả chi phí đó?

Training cập nhật trọng số: forward, backward, optimizer trên dữ liệu khổng lồ; ước lượng $$6ND$$ FLOPs. Inference chỉ
forward với trọng số cố định: khoảng $$2N$$ FLOPs mỗi token. Với Qwen2.5-3B (3.09 tỉ tham số, 18 nghìn tỉ token
pretrain) training khoảng $$3.3 \times 10^{23}$$ FLOPs, tương đương khoảng 100 GPU-năm ở 100 TFLOPS hiệu dụng, còn inference
khoảng $$6 \times 10^{9}$$ FLOPs mỗi token.

Training là chi phí một lần, do nhà phát hành model trả. Inference là chi phí **mỗi request, mãi mãi**, tỉ lệ với số người
dùng: giá vốn của sản phẩm, do đội AI Engineer chịu. Hệ quả: tối ưu inference (model nhỏ hơn, quantization, cache, output
ngắn) thường đáng tiền hơn mọi tối ưu khác ở quy mô lớn.

## Prefill và decode là gì? Vì sao token output đắt và chậm hơn token input?

Prefill xử lý cả prompt **song song** trong một lần: nhiều phép nhân ma trận lớn, giới hạn bởi compute, nhanh. Decode
sinh **từng token một**; mỗi token phải đọc toàn bộ trọng số từ bộ nhớ để làm ít phép tính: giới hạn bởi băng thông bộ
nhớ, chậm và tuần tự. Trên RTX 3050 Laptop với `qwen2.5:3b` (Q4_K_M, 1.93 GB): prefill khoảng 3 300 token/giây, decode
khoảng 74 token/giây, khoảng 75% trần lý thuyết 192 GB/s ÷ 1.93 GB ≈ 99 token/giây.

Nhà cung cấp tính giá output gấp nhiều lần input (5 lần ở bảng giá Anthropic, OpenAI, Gemini kiểm 2026-10-30) vì mỗi
token output giữ GPU lâu hơn. Hệ quả thiết kế: giới hạn độ dài câu trả lời, dùng structured output ngắn, stream để che độ
trễ decode.

## Token là gì? Vì sao văn bản tiếng Việt tốn nhiều token hơn, và điều đó ảnh hưởng gì?

Token là đơn vị model đọc và sinh, thường là mảnh từ do BPE học từ dữ liệu train. Tokenizer học chủ yếu trên tiếng Anh
có ít mảnh cho âm tiết tiếng Việt có dấu, nên chặt chúng thành nhiều mảnh. Đo trên 1 268 cặp câu IWSLT'15: bản tiếng
Việt dài hơn 8% theo ký tự, nhưng tốn gấp 2.42 lần token với `cl100k_base` (GPT-4) và khoảng 1.4 lần với `o200k_base`
và Qwen2.5 (từ vựng lớn hơn).

Ảnh hưởng: chi phí, độ trễ (nhiều token output hơn) và context hiệu dụng (ngân sách 3 000 token chứa 57 câu tiếng Việt
với `cl100k_base`, 103 câu với Qwen2.5). Không so giá MTok giữa model khác tokenizer; so chi phí mỗi tác vụ trên văn bản
thật.

## Ước lượng chi phí hàng tháng cho một chatbot hỗ trợ khách hàng: 10 000 hội thoại mỗi ngày.

Trả lời theo khung, nói rõ giả định: mỗi hội thoại khoảng 4 lượt; mỗi lượt gửi lại lịch sử, nên input tăng dần (giả sử
trung bình 2 000 token input, 250 token output mỗi lượt). Mỗi ngày 40 000 lượt, tháng 1.2 triệu lượt: 2.4 tỉ token input,
0.3 tỉ token output. Với model nhỏ giá 0.10 / 0.50 USD/MTok: $$2400 \times 0.10 + 300 \times 0.50 = 390$$ USD/tháng; model
lớn 2 / 10: $$4800 + 3000 = 7800$$ USD/tháng.

Điểm cộng: (1) nhận ra lịch sử hội thoại làm input tăng theo bình phương số lượt, nên tóm tắt lịch sử hoặc cắt cửa sổ;
(2) system prompt và tài liệu cố định dùng prompt caching (đọc cache rẻ 10 tới 40 lần tuỳ model); (3) routing: câu hỏi dễ
cho model nhỏ; (4) cộng biên cho tokenizer (tiếng Việt) và cho tăng trưởng; (5) chi phí API thường nhỏ so với chi phí
người, nhưng phải có cảnh báo khi vượt ngân sách.

## Khi nào nên tự host model mở thay vì gọi API?

Tự host trả theo giờ GPU: $$\frac{g}{r \cdot 3600 \cdot u} \cdot 10^6$$ USD mỗi triệu token, với $$u$$ là tỉ lệ thời gian GPU
bận. Với tải thấp hoặc thất thường, $$u$$ nhỏ và tự host đắt hơn API nhiều lần (GPU 1 USD/giờ, 1 000 token/giây: 0.93 USD/MTok
khi bận 30%, 5.6 USD/MTok khi bận 5%).

Tự host hợp lý khi: dữ liệu không được rời hạ tầng (y tế, ngân hàng, hợp đồng); tải lớn và đều; cần model đã fine-tune
hoặc kiểm soát phiên bản model tuyệt đối; cần độ trễ thấp trong mạng nội bộ. API hợp lý khi: cần model mạnh nhất, tải
nhỏ hoặc dao động, đội không có người vận hành GPU (serving, autoscaling, giám sát, cập nhật). Câu trả lời senior nhắc
chi phí ẩn của tự host: kỹ sư vận hành, GPU dự phòng cho giờ cao điểm, thời gian cập nhật model mới.

## Trước khi đưa một model mở vào sản phẩm, bạn đọc gì trong model card và config?

Model card (frontmatter và nội dung): **giấy phép** (Qwen2.5-0.5B và 7B là Apache-2.0, nhưng Qwen2.5-3B là
`qwen-research`, chỉ phi thương mại), model gốc (`base_model`), ngôn ngữ được hỗ trợ, cách train, giới hạn và rủi ro
được nêu, kết quả eval và trên benchmark nào. `config.json`: kiến trúc, số layer, `hidden_size`, số head và **head KV**
(GQA), `max_position_embeddings` (context), `vocab_size`, MoE hay dense. Từ config tính được số tham số chính xác, VRAM
cho trọng số và KV cache.

Rồi tự kiểm: chạy bộ eval của mình, đo tốc độ trên phần cứng đích, xem template chat và cách model xử lý tiếng Việt. Không
tin con số trong tên model ("7B" của Qwen2.5 là 7.62 tỉ, của Mistral là 7.25 tỉ).

## Qwen2.5-7B-Instruct có chạy được trên GPU 12GB không? Trên laptop 4GB thì sao?

Tính: 7.62 tỉ tham số. bf16: $$7.62 \times 2 = 15.2$$ GB chỉ riêng trọng số, không vừa 12GB. 4 bit: khoảng 3.8 GB. KV
cache: $$2 \times 28 \text{ layer} \times 4 \text{ head KV} \times 128 \times 2 \text{ byte} = 57\,344$$ byte mỗi token, 0.23 GB cho 4 096 token.
Cộng khoảng 0.5 GB đệm: khoảng 4.5 GB. Vừa 12GB thoải mái (còn chỗ cho context 32K hoặc nhiều request đồng thời), không
vừa 4GB; trên laptop phải dùng 3B, hoặc để một phần layer chạy CPU (chậm hẳn).

Bẫy hay gặp: tính KV cache bằng số head query (28) thay vì head KV (4), sai 7 lần; quên rằng KV cache tăng tuyến tính theo
context **và** batch, nên với nhiều người dùng đồng thời và context dài, KV cache chứ không phải trọng số mới là giới hạn.

## Giải thích embedding, vector database và RAG cho một product manager.

Embedding biến một đoạn văn thành một dãy số sao cho hai đoạn cùng nghĩa có dãy số gần nhau, kể cả khi khác chữ ("phạt
lỗi không đội mũ bảo hiểm" gần "mức xử phạt người không đội nón"). Vector database lưu hàng triệu dãy số đó và tìm nhanh
những dãy gần nhất. RAG ghép hai thứ với LLM: khi người dùng hỏi, tìm vài đoạn tài liệu gần nghĩa nhất, đưa vào prompt,
yêu cầu LLM chỉ trả lời dựa trên đó và trích nguồn.

Lợi ích cho PM: model trả lời về **tài liệu riêng** và **mới** mà không cần train lại; câu trả lời có nguồn để người dùng
kiểm. Giới hạn: tìm sai tài liệu thì trả lời sai; phải đo riêng chất lượng tìm kiếm và chất lượng trả lời (module 13).

## AI agent là gì? Khi nào không nên dùng agent?

Agent là LLM chạy trong vòng lặp: đọc mục tiêu, quyết định gọi tool nào (tìm kiếm, chạy code, gọi API), đọc kết quả, lặp
tới khi xong. Khác một lời gọi LLM ở chỗ **model quyết định luồng điều khiển**.

Không nên dùng khi luồng đã biết trước (một pipeline cố định "tìm, rồi trả lời" rẻ, nhanh, dễ kiểm hơn agent), khi mỗi
bước sai có hậu quả không đảo ngược được mà không có người duyệt (chuyển tiền, xoá dữ liệu), khi ngân sách độ trễ thấp
(mỗi bước thêm một lời gọi LLM), và khi chưa có cách đo thành công. Lỗi tích luỹ: 5 bước, mỗi bước đúng 95%, chỉ còn
khoảng 77% đúng cả chuỗi.

## Hallucination là gì, vì sao xảy ra, và bạn giảm nó thế nào?

LLM sinh token theo phân phối xác suất học từ văn bản; nó được train để sinh văn bản **nghe hợp lý**, không để biết mình
không biết. Khi thiếu thông tin, câu trả lời hợp lý nhất về mặt ngôn ngữ vẫn được sinh ra, với giọng tự tin như câu đúng.

Giảm, không triệt tiêu: (1) grounding bằng RAG và bắt trích nguồn, kiểm trích dẫn bằng code; (2) cho phép và khuyến khích
từ chối ("không tìm thấy căn cứ"), có cổng điểm retrieval trước khi gọi LLM; (3) temperature thấp cho tác vụ tra cứu;
(4) structured output với kiểm tra schema; (5) đo tỉ lệ hallucination trên bộ eval, theo dõi trong production; (6) UX
cho người dùng thấy nguồn và báo sai. Ở miền rủi ro cao (pháp luật, y tế) cần người duyệt.

## Case: PM muốn "thêm AI vào ô tìm kiếm sản phẩm" của một sàn thương mại điện tử. Bạn đóng khung bài toán thế nào?

Trước giải pháp, hỏi vấn đề: người dùng đang thất bại ở đâu (không tìm thấy vì gõ sai, dùng từ khác người bán, câu hỏi
mô tả nhu cầu "quà cho mẹ dưới 500k")? Đo bằng gì (tỉ lệ tìm kiếm không có kết quả, tỉ lệ click, chuyển đổi)? Ràng buộc:
độ trễ tìm kiếm phải dưới vài trăm mili giây, hàng triệu truy vấn mỗi ngày.

Rồi đi theo thang chi phí: phần lớn giá trị thường đến từ **embedding và hybrid search** (BM25 + vector, module 12, 13),
không cần LLM trong đường nóng: rẻ, nhanh, đo được bằng A/B test. LLM dùng ở chỗ có lợi rõ: viết lại truy vấn mô tả nhu
cầu thành bộ lọc (chỉ cho truy vấn dài, có cache), sinh mô tả hoặc thuộc tính sản phẩm offline (batch API, giảm 50%), hoặc
một trợ lý mua sắm riêng cho người muốn hội thoại. Kế hoạch: baseline đo được, eval offline với truy vấn thật có nhãn, A/B
online, theo dõi chi phí mỗi truy vấn. Ứng viên trả lời "dùng GPT cho mọi truy vấn" mà không tính độ trễ và chi phí cho
hàng triệu truy vấn là trượt câu này.

## Case: hoá đơn API tăng 30% sau khi đổi sang model mới cùng giá mỗi triệu token. Bạn điều tra thế nào?

Tách chi phí thành (số request) × (token input + token output mỗi request) × giá. Giá không đổi, nên tìm ở token:

1. **Tokenizer đổi**: model mới có thể dùng tokenizer khác. Trang giá Anthropic ghi rõ từ Claude 4.7 trở đi tokenizer mới
   "tạo ra khoảng 30% nhiều token hơn cho cùng văn bản". Kiểm bằng cách đếm token cùng một tập prompt với cả hai model
   (API đếm token hoặc trường `usage` trong response).
2. **Output dài hơn**: model mới dài dòng hơn, hoặc là reasoning model sinh thinking tokens tính giá output. So phân phối
   `output_tokens` trước và sau.
3. **Cache mất hiệu lực**: prompt cache gắn với model; đổi model hoặc đổi tiền tố prompt làm tỉ lệ cache hit tụt.
4. **Số request tăng**: retry vì lỗi định dạng, agent đi nhiều bước hơn.

Sửa theo nguyên nhân (giới hạn `max_tokens`, sửa prompt cho ngắn, giữ tiền tố cố định để cache, routing), và rút bài học:
bộ eval khi đổi model phải đo **chi phí mỗi tác vụ** và độ trễ, không chỉ chất lượng.
