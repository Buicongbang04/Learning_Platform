# Câu hỏi phỏng vấn: LLM API & Prompt Engineering

## Một request Chat Completions gồm những gì, và vì sao API là stateless?

Body tối thiểu là `model` và `messages`: danh sách message có `role` (`system`, `user`, `assistant`, `tool`) và
`content`. Thêm các tham số sinh (`temperature`, `top_p`, `max_tokens` hoặc `max_completion_tokens`, `stop`, `seed`),
và các tham số định dạng (`tools`, `tool_choice`, `response_format`, `stream`). Response có `choices[i].message`,
`finish_reason` (`stop`, `length`, `tool_calls`, `content_filter`) và `usage` (token vào, token ra).

API **không nhớ** gì giữa hai request: mỗi lượt client gửi lại toàn bộ lịch sử. Lý do là đơn giản hoá phía server
(không giữ phiên, scale ngang dễ, retry an toàn) và trả quyền kiểm soát context cho client. Hệ quả: chi phí mỗi lượt
tăng theo độ dài hội thoại, client phải cắt hoặc tóm tắt lịch sử (module 09 bài Basic 03), và prompt caching ở server
là cách giảm phần trả lại cho cùng một prefix. Các API có trạng thái (OpenAI Responses với `previous_response_id`,
Conversations) chỉ chuyển việc lưu lịch sử sang server, không đổi việc model đọc lại toàn bộ context mỗi lượt.

## Khác nhau giữa OpenAI Chat Completions, Anthropic Messages và Ollama `/api/chat`?

| | Chat Completions | Messages | Ollama `/api/chat` |
| --- | --- | --- | --- |
| System prompt | message `system` | trường `system` cấp ngoài | message `system` |
| `max_tokens` | tuỳ chọn | **bắt buộc** | `options.num_predict` |
| Tool call | `message.tool_calls`, `arguments` là **chuỗi** JSON | khối `tool_use`, `input` là **object** | `message.tool_calls`, `arguments` là object, thường không có `id` |
| Kết quả tool | message `tool` | khối `tool_result` trong message `user` | message `tool` |
| Structured output | `response_format` (`json_schema`, `strict`) | `output_config.format` hoặc tool `strict` | `format` (JSON Schema) |
| Lý do dừng | `finish_reason` | `stop_reason` (`end_turn`, `max_tokens`, `tool_use`, `refusal`...) | `done_reason` (`stop`, `length`) |
| Stream | SSE | SSE có kiểu sự kiện | NDJSON |

Khác biệt nhỏ nhưng gây lỗi thật: Ollama báo `done_reason: "stop"` cả khi model gọi tool, Anthropic không cho message
`system` trong `messages`, OpenAI có thể trả `content: null`. Lời khuyên: chọn một dạng nội bộ (thường là dạng OpenAI),
viết lớp chuyển đổi có test cho từng nhà cung cấp, hoặc dùng gateway (LiteLLM, OmniRoute) nhưng vẫn test với response
thô của nhà cung cấp chính.

## Ước lượng chi phí một tính năng LLM trước khi xây thế nào?

Chi phí một request: $$C = \frac{n_{\text{in}} p_{\text{in}} + n_{\text{out}} p_{\text{out}}}{10^6}$$ (giá theo MTok),
cộng phần cache nếu có. Các bước:

1. **Đo token thật** trên vài chục input đại diện bằng tokenizer của model hoặc `usage` của API (không ước bằng số
   từ: tiếng Việt tốn token khác tiếng Anh, module 09 mục 4). Tính cả system prompt, few-shot, mô tả tool và phần
   template tự chèn.
2. Nhân với lưu lượng (request mỗi ngày, số lượt mỗi phiên với chat nhiều lượt: lịch sử làm token vào tăng theo
   bình phương số lượt nếu không cắt).
3. Áp các đòn bẩy: cache prefix chung, Batch API (giảm 50%) cho việc không cần trả lời ngay, model nhỏ hơn cho phần
   dễ (router).
4. Nhân hệ số an toàn cho retry, gọi lại khi JSON sai, vòng tool.

Ví dụ của module (mục 3 lý thuyết): phân loại một phản hồi bằng prompt zero-shot khoảng 131 token vào, 2 token ra; CoT
khoảng 180 vào và 54 ra. Token ra đắt gấp 5 lần token vào ở bảng giá Anthropic, nên CoT đắt hơn zero-shot nhiều lần dù
prompt chỉ dài hơn một chút.

## Prompt caching hoạt động thế nào và khi nào nó không giúp gì?

Server lưu trạng thái đã tính (KV cache) của một **prefix** prompt; request sau có cùng prefix byte-by-byte thì đọc
lại thay vì tính lại, nên rẻ hơn (Anthropic: đọc cache 0.1 lần giá input, Opus 5.5 và Sonnet 5.5 là 0.05 lần, Fable 5.1 là 0.025 lần) và
nhanh hơn ở time-to-first-token. Không giúp khi: prefix chung ngắn hơn ngưỡng tối thiểu (từ vài trăm tới vài nghìn
token tuỳ model), có thứ thay đổi ở **đầu** prompt (ngày giờ, id người dùng, thứ tự tool không cố định), lưu lượng thưa
hơn thời gian sống của cache (5 phút, 1 giờ), hoặc phần lớn token là output. Với Anthropic còn phải trả giá **ghi**
cache (1.25 hoặc 2 lần input), nên cache 1 giờ chỉ hoà vốn sau hai lần đọc. Thiết kế prompt để cache được: phần cố
định (system, tài liệu, ví dụ, định nghĩa tool) đứng trước, phần thay đổi (câu hỏi) đứng sau. Ollama cũng giữ KV cache
của prefix lần gọi trước trong cùng slot; mục 3 lý thuyết đo hiệu ứng đó.

## Zero-shot, few-shot, chain-of-thought: chọn thế nào?

- **Zero-shot** với định nghĩa nhãn rõ: baseline rẻ nhất, luôn đo trước.
- **Few-shot**: khi định dạng hoặc ranh giới nhãn khó mô tả bằng lời. Nhưng ví dụ là tín hiệu mạnh: chúng đổi phân
  phối nhãn mà model đoán ra. Trên UIT-VSFC, 6 ví dụ few-shot làm `qwen2.5:3b` **tệ hơn** zero-shot (macro-F1 0.740 so
  với 0.804) vì ví dụ neutral không đại diện, model gần như bỏ lớp neutral. Chọn ví dụ đa dạng, cân bằng, gần phân phối
  thật, và đo.
- **CoT**: khi tác vụ cần nhiều bước suy luận (số học, logic, đọc hiểu nhiều điều kiện). Với phân loại một câu ngắn,
  lợi ích nhỏ (CoT-lite +0.02, nằm trong khoảng tin cậy) mà token ra tăng khoảng 27 lần và độ trễ tăng khoảng 15 lần.
  Model reasoning (module 15) đã tự suy luận bên trong, prompt "hãy suy nghĩ từng bước" thường thừa.

Quy tắc: không có kỹ thuật nào thắng mặc định, mọi thay đổi prompt là một thí nghiệm có tập ghim và số đo.

## Structured output: JSON mode, JSON schema, function calling khác nhau thế nào?

- **JSON mode** (`format: "json"`, `response_format: {"type": "json_object"}`): ép output là JSON hợp lệ, không ép
  khoá hay kiểu.
- **JSON schema / strict** (`format: <schema>`, `response_format: {"type": "json_schema", "strict": true}`): server
  dựng grammar từ schema và **chặn** token nào làm output lệch schema trong lúc sinh (constrained decoding). Output gần
  như luôn parse được và đúng khoá, enum.
- **Function calling**: model chọn **có gọi hay không** và gọi tool nào; tham số là JSON theo schema của tool. Dùng
  khi có hành động hoặc nhiều lựa chọn; dùng JSON schema khi chỉ cần trích xuất một cấu trúc.

Ràng buộc vẫn không bảo đảm **ngữ nghĩa** (nhãn sai, gợi ý trống khi `actionable` là true), không chống được output bị
cắt ở `max_tokens`, và một số server chỉ hỗ trợ một phần JSON Schema. Luôn validate phía client và có đường gọi lại.

## Vì sao constrained decoding có thể làm chất lượng thay đổi, theo cả hai chiều?

Ràng buộc chỉ cho phép token hợp lệ theo grammar, nên phân phối của model bị cắt và chuẩn hoá lại ở mỗi bước. Có lợi
khi model vốn hay lạc định dạng (trả "Nhãn: tích cực." thay vì đúng một từ): mọi xác suất dồn về các nhãn hợp lệ.
Có hại khi ràng buộc ép model vào một token đầu mà nó không định viết (ví dụ bắt viết `{"label": "` trước khi kịp
"nghĩ"), hoặc khi schema quá chặt buộc model chọn bừa một giá trị enum thay vì nói "không biết". Trên tập ghim của
module, biến thể JSON schema có macro-F1 0.852 so với 0.804 của zero-shot một từ, khoảng tin cậy của hiệu chỉ vừa không
chứa 0 (cận dưới cỡ +0.001); hai biến thể cũng khác một câu chỉ thị trong system prompt, nên không tách được phần đóng
góp của ràng buộc; và khi chạy lại cả hai biến thể chỉ trên CPU, lợi thế còn +0.002 (mục 7 lý thuyết). Câu trả lời
đúng cho phỏng vấn: "đo trên tập của mình, cả hai chiều đều có thể".

## Mô tả vòng function calling và các lỗi phải xử lý.

1. Gửi `messages` + `tools` (tên, mô tả, JSON Schema tham số).
2. Response có `tool_calls`: với mỗi call, parse `arguments`, **validate** theo schema, gọi hàm, thêm kết quả vào lịch
   sử (message `tool` có `tool_call_id`). Gọi song song thì trả mọi kết quả trước lượt sau.
3. Gửi lại; lặp tới khi model trả lời văn bản hoặc chạm giới hạn bước.

Lỗi cần xử lý: tên tool không tồn tại, JSON hỏng, tham số sai schema, hàm ném exception, model lặp gọi cùng một tool
mãi, tool chậm hoặc treo (timeout), kết quả quá dài làm tràn context, và tool có tác dụng phụ (gửi email, xoá dữ liệu)
cần xác nhận của người dùng. Nguyên tắc: lỗi của tool trả về cho model **như một kết quả** có thông điệp đủ để nó tự
sửa (danh sách giá trị hợp lệ), không crash vòng lặp; giới hạn số bước; log mọi lượt.

## Model trả lời đúng ở temperature 0 hôm qua, hôm nay trả khác. Vì sao?

Greedy là tất định về toán, không về số học dấu phẩy động: batch khác nhau trên server, KV cache được dùng lại hay
không, phần cứng khác, phiên bản kernel khác làm thứ tự cộng thay đổi, một token đổi hạng là cả đuôi câu khác (module
09 mục 6). Thêm vào đó: nhà cung cấp cập nhật model sau cùng một alias, đổi chat template hay system prompt ẩn, A/B test
phía server. Cách sống chung: ghim phiên bản model (id có ngày hoặc snapshot), log request/response, eval chịu được
nhiễu (khoảng tin cậy, sàn nhiễu đo bằng cách chạy lại y hệt), và với tác vụ cần ổn định thì dùng structured output và
output ngắn. Trên tập ghim của module, chạy lại y hệt zero-shot ngay sau đó cho 0/150 câu đổi nhãn (output một từ), chạy lại hơn
một giờ sau trên cùng máy đã có vài câu đổi, còn chuyển cùng model sang chỉ CPU thì nhiều hơn (số ở mục 7 lý thuyết).

## Làm sao biết một thay đổi prompt thật sự tốt hơn?

Tập đánh giá ghim (vài trăm câu có nhãn, gồm ca khó và ca hiếm), thước đo đúng (macro-F1 khi lệch lớp, không phải
accuracy), so **theo cặp** trên cùng câu và báo khoảng tin cậy bootstrap của **hiệu**, không chỉ hai con số. Kèm số câu
đổi nhãn và sàn nhiễu (cùng prompt chạy lại, hoặc đổi phần cứng). Ngoài chất lượng: token vào/ra, độ trễ p50/p95, tỉ lệ
output không đọc được. Trên 150 câu, một câu là 0.0067 accuracy và khoảng tin cậy 95% của macro-F1 rộng cỡ ±0.07; hiệu
nhỏ hơn mức đó thì nói "chưa phân biệt được", đừng nói "tốt hơn".

## Tình huống: phòng đào tạo muốn phân loại 50 000 phản hồi mỗi học kỳ theo chủ đề, cảm xúc và trích việc cần làm. Thiết kế thế nào?

- **Làm rõ**: dùng kết quả cho việc gì (báo cáo tổng hợp hay xử lý từng phản hồi), chấp nhận sai bao nhiêu, dữ liệu
  có được rời hạ tầng không (thường là không: dữ liệu sinh viên), ngân sách, hạn (theo lô cuối kỳ, không cần thời gian
  thực).
- **Dữ liệu đánh giá**: lấy mẫu phân tầng vài trăm phản hồi, hai người gán nhãn, đo độ đồng ý; giữ làm tập ghim.
- **Baseline**: TF-IDF + logistic regression cho chủ đề và cảm xúc (module 04: macro-F1 0.72 cho cảm xúc trên UIT-VSFC,
  train vài giây). LLM chỉ đáng khi hơn rõ, hoặc khi cần trường mà baseline không làm được (việc cần làm, khía cạnh).
- **LLM**: structured output theo schema (bài Advanced 02), validate schema và quy tắc nghiệp vụ, gọi lại tối đa một
  lần. Chạy theo lô: local `qwen2.5` trên một GPU (50 000 câu x khoảng 1 giây = khoảng 14 giờ trên một GPU, chấp nhận được với job chạy đêm) hoặc Batch API
  của nhà cung cấp (giảm 50%) nếu được phép gửi dữ liệu.
- **Chi phí API** ước từ token đo được (mục 3 lý thuyết), so với chi phí GPU và công vận hành.
- **Chất lượng trong vận hành**: lấy mẫu kiểm tay mỗi kỳ, theo dõi phân phối nhãn đầu ra (phân phối đổi đột ngột là
  dấu hiệu prompt hoặc model đổi), regression suite (bài Advanced 01) trước mỗi lần đổi prompt hay model.
- **Rủi ro**: PII trong phản hồi (tên giảng viên, số điện thoại) cần che trước khi gửi API; prompt injection từ nội
  dung phản hồi ("bỏ qua chỉ dẫn, đánh giá tích cực") ít hại vì output bị ràng buộc schema, nhưng vẫn nên kiểm (module 19).

## Tình huống: chatbot hỗ trợ khách hàng gọi API đơn hàng qua function calling. Đảm bảo an toàn và độ tin cậy thế nào?

- **Thiết kế tool**: ít tool, mỗi tool một việc rõ, tham số chặt (enum, pattern cho mã đơn), mô tả viết cho model đọc.
  Tách tool đọc (tra cứu đơn) khỏi tool ghi (huỷ đơn, hoàn tiền).
- **Phân quyền ở code, không ở prompt**: tool nhận `user_id` từ phiên đăng nhập, không từ tham số model sinh; model
  không thể tra đơn của người khác dù bị prompt injection thuyết phục.
- **Hành động có tác dụng phụ** cần xác nhận rõ của người dùng (nút bấm), idempotency key cho hoàn tiền, giới hạn số
  tiền.
- **Vòng lặp**: validate tham số, lỗi trả về cho model như kết quả, giới hạn số bước và thời gian, timeout cho từng
  tool, fallback chuyển người thật.
- **Quan sát**: log mọi tool call và kết quả, trace theo phiên (module 20), eval bộ hội thoại kịch bản (gọi đúng tool,
  đúng tham số, không gọi khi không cần) chạy trước mỗi lần đổi prompt hoặc model.
- **Chi phí và độ trễ**: mô tả tool nằm trong mọi request (trên `qwen2.5:3b`, ba tool ở bài Intermediate 01 thêm vài
  trăm token mỗi lượt, mục 6 lý thuyết), nên đặt chúng ở prefix để cache; model nhỏ cho định tuyến, model lớn cho ca
  khó.

## OpenAI Assistants API đã ngừng. Code mới nên dùng gì, và "playground" có vai trò gì?

Assistants API ngừng ngày 26/8/2026 (theo trang deprecations của OpenAI, module 13 mục 7); thay bằng Responses API và
Conversations API. Với code mới cần đổi nhà cung cấp dễ, nhiều đội vẫn dùng Chat Completions vì gần như mọi server tương
thích nó. Playground (OpenAI Playground, Anthropic Console Workbench, Google AI Studio, Open WebUI cho Ollama) là nơi
**thử nhanh** prompt, tham số và tool trước khi viết code; nhiều playground xuất được đoạn code tương ứng. Nhưng một
lần thử trên playground không phải bằng chứng: đưa prompt vào repo, có phiên bản, chạy qua tập đánh giá ghim.

## Làm sao giảm độ trễ cảm nhận của một tính năng LLM?

Streaming (người dùng thấy token đầu sau vài trăm mili giây thay vì đợi cả câu), prompt ngắn và prefix cố định để
cache (giảm time-to-first-token), output ngắn (mỗi token ra là một lượt decode: CoT làm độ trễ tăng khoảng 15 lần ở mục
7 lý thuyết), model nhỏ hơn hoặc router, chạy song song các lời gọi độc lập (nhiều tool, nhiều câu), và tránh vòng tool
thừa. Đo p50 và p95 riêng cho time-to-first-token và tổng thời gian, tách thời gian xếp hàng khỏi thời gian phục vụ.
