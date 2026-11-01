# Câu hỏi phỏng vấn: Reasoning Models

## Vì sao chain-of-thought làm model trả lời đúng hơn? Khi nào nó không giúp?

Một lượt forward của Transformer chỉ có một số tầng cố định: lượng tính toán "nối tiếp" mà model làm được trước khi phải
nhả một token là có hạn. Bài toán nhiều bước (GSM8K cần 2 tới 8 phép tính) vượt quá độ sâu đó nếu bắt model nhả đáp số
ngay. Viết lời giải ra chữ biến mỗi bước trung gian thành token, và token đó lại là input cho các bước sau: model dùng
chính văn bản của nó làm bộ nhớ nháp, tổng compute tăng theo số token. Đó là lý do CoT giúp nhiều với toán, logic, code
nhiều bước, và giúp ít hoặc không giúp với tác vụ một bước (phân loại cảm xúc, tra cứu một sự kiện): module 11 đo CoT
trên UIT-VSFC chỉ hơn trong mức nhiễu với giá gấp nhiều lần token. CoT cũng có giá: độ trễ, tiền token ra, và lời giải dài
có thể "lạc" (model nhỏ hay tính đúng rồi tự sửa sai ở bước sau). Quyết định dùng CoT phải dựa trên số đo trên tập ghim
của chính tác vụ đó.

## Self-consistency khác best-of-N thế nào? Khi nào chọn cái nào?

Cả hai sinh N lời giải. Self-consistency (Wang và cộng sự, 2022) bỏ phiếu theo **đáp số cuối**: không cần gì ngoài một
bộ trích đáp số, nhưng chỉ dùng được khi đáp số so được bằng nhau (số, lựa chọn, nhãn), và chỉ đúng khi đáp án đúng là
đáp án phổ biến nhất. Best-of-N dùng một **verifier** chấm từng lời giải rồi lấy cái điểm cao nhất: dùng được cho đầu ra
tự do (code, văn bản), và nếu verifier tốt thì tiến tới pass@N, trần của mọi cách chọn. Cái giá là phải có verifier:
test chạy được (code), checker (toán), hay một reward model (đắt, có thể bị khai thác). Verifier yếu (log-prob của chính
model) thường thua cả bỏ phiếu. Thực tế: có verifier chính xác thì best-of-N; đáp số rời rạc mà không có verifier thì bỏ
phiếu; kết hợp được bằng weighted vote (cộng điểm verifier theo đáp số).

## pass@k và maj@k khác nhau ở đâu? Vì sao báo cáo pass@k của một hệ thống không có verifier là gây hiểu lầm?

pass@k là xác suất **có ít nhất một** lời giải đúng trong k lời giải: nó giả định có ai đó chỉ ra lời giải đúng. maj@k
là độ chính xác khi chọn bằng bỏ phiếu, thứ hệ thống thật đạt được không cần oracle. pass@k luôn ≥ maj@k và tăng đơn
điệu theo k; với k lớn nó có thể gần 100% trong khi maj@k đứng yên. Báo cáo pass@k cho một chatbot (người dùng chỉ thấy
một câu trả lời) là thổi phồng. pass@k có nghĩa khi có verifier rẻ và chính xác (code có test, toán có checker), hoặc
khi đo **độ phủ** của model (RL có thu hẹp độ phủ không, như Yue và cộng sự 2025). Công thức không chệch của Chen và cộng
sự (2021) tính từ n ≥ k mẫu, không phải $$1 - (1-p)^k$$.

## Test-time compute có thay được model lớn hơn không?

Một phần. Snell và cộng sự (2024) thấy với câu hỏi dễ và trung bình, tiêu compute lúc inference một cách tối ưu (chọn
giữa sửa tuần tự và lấy mẫu song song theo độ khó) cho model nhỏ đuổi kịp model lớn gấp nhiều lần cùng FLOPs; với câu
khó, model lớn vẫn thắng. Ở quy mô của module: Qwen2.5-0.5B bỏ phiếu 16 lời giải tăng được độ chính xác so với greedy,
nhưng vẫn kém xa `qwen2.5:3b` greedy, và tốn token gấp nhiều lần. Kết luận vận hành: test-time compute là một núm vặn
**theo từng request** (dễ thì ít, khó thì nhiều), còn chọn model là núm vặn cố định. Phải tính cả độ trễ: 16 mẫu song song
tăng chi phí gấp 16 nhưng độ trễ chỉ tăng ít nếu batch được; suy nghĩ tuần tự dài thì độ trễ tăng tuyến tính.

## GRPO khác PPO thế nào? Vì sao nó hợp với reasoning?

PPO cho LLM (module 07) cần một **critic** (value model cùng cỡ policy) để ước lượng advantage theo từng token. GRPO
(Shao và cộng sự, DeepSeekMath 2024) bỏ critic: sinh G lời giải cho cùng prompt, advantage của lời giải i là
$$(r_i - \text{mean}(r))/\text{std}(r)$$ trong nhóm, gán cho mọi token của lời giải đó. Phần còn lại giữ của PPO: ratio
với policy cũ, clipped objective, KL tới reference (ước lượng k3). Hợp với reasoning vì: reward kiểm được thường là
nhị phân ở cuối chuỗi (đúng/sai), critic học rất khó trên tín hiệu thưa như vậy; so trong nhóm cùng câu hỏi tự loại bỏ
độ khó của câu; bỏ critic tiết kiệm gần một nửa bộ nhớ. Cái giá: phải sinh G lời giải mỗi prompt (sinh chiếm phần lớn
thời gian train), và nhóm mà mọi lời giải cùng reward không cho gradient.

## Trong GRPO, chuyện gì xảy ra khi mọi lời giải trong nhóm có cùng reward? Xử lý thế nào?

Advantage bằng 0 cho cả nhóm (tử số $$r_i - \bar r = 0$$; `eps` ở mẫu số chỉ để tránh `0/0`). Prompt đó không đóng góp
gradient, chỉ tốn thời gian sinh. Xảy ra khi câu quá dễ (mọi lời giải đúng) hoặc quá khó (mọi lời giải sai), và rất
nhiều khi định dạng reward quá chặt so với model (mọi lời giải 0 điểm vì sai khung: vấn đề cold start). Xử lý: theo dõi tỉ
lệ nhóm std = 0 (`frac_reward_zero_std` trong TRL); chọn tập train vừa sức (lọc câu model đã luôn đúng hoặc luôn sai);
DAPO dùng dynamic sampling (bỏ nhóm như vậy và sinh thêm cho đủ batch); tăng G; thêm reward định dạng từng phần hoặc
SFT cold start để reward không toàn 0.

## Giải thích ước lượng KL k3. Vì sao không dùng thẳng log π - log π_ref?

Với token lấy mẫu từ policy và $$r = \pi_{\text{ref}}/\pi_\theta$$ tại token đó, $$k_1 = -\log r$$ là ước lượng không chệch của
$$\mathrm{KL}(\pi_\theta\|\pi_{\text{ref}})$$ nhưng âm ở nhiều token và phương sai lớn. $$k_3 = r - 1 - \log r$$ cũng không chệch (vì
$$\mathbb E[r] = 1$$) và luôn không âm, phương sai nhỏ khi hai policy gần nhau (Schulman 2020). GRPO cộng $$\beta k_3$$ thẳng vào
loss thay vì trừ vào reward như PPO-RLHF. Lỗi hay gặp: đổi chỗ hai log-prob, ra ước lượng của chiều ngược lại mà vẫn
không âm, nên chỉ thí nghiệm Monte Carlo mới bắt được. Nhiều công thức hiện nay (DAPO, mặc định `beta = 0` của TRL) bỏ
hẳn KL với reward kiểm được, vì reward khó hack hơn và KL kìm model đi xa khỏi điểm xuất phát, thứ ta muốn với reasoning.

## Reward kiểm được (RLVR) có bị hack không? Cho ví dụ và cách phòng.

Có, chỉ ở dạng thô hơn reward model. Ví dụ: reward chấm "đáp án có trong thẻ answer" thì model liệt kê nhiều số;
reward định dạng chỉ cần có thẻ thì model nhả thẻ rỗng; reward code chạy test thì model sửa test hay in kết quả mong
đợi; reward độ dài hay chuẩn hoá theo độ dài thì model kéo dài hoặc cắt ngắn bất thường; đáp số trích bằng "số cuối
cùng" thì model chép lại số trong đề. Phòng: reward chặt (đúng một số, khung `fullmatch`), tách bộ trích để **đo**
(dễ dãi) khỏi bộ trích để **dạy** (chặt); đọc mẫu thật mỗi vài chục bước; theo dõi độ dài, tỉ lệ định dạng, độ chính
xác trên tập giữ lại bằng bộ trích độc lập; sandbox cho code; giữ một ít KL hoặc giới hạn độ dài.

## Distillation từ reasoning model khác RL trực tiếp ra sao? Khi nào chọn cái nào?

Distill: cho model thầy (lớn, đã giỏi) sinh lời giải, lọc lời giải đúng (rejection sampling), SFT model trò. Rẻ, ổn định,
dùng hạ tầng SFT sẵn có (module 14). DeepSeek-R1 báo cáo distill từ R1 cho model 7B tới 32B tốt hơn chạy RL trực tiếp
trên chính các model đó. RL thì không cần thầy, khám phá được cách giải mới vượt dữ liệu, nhưng đắt (sinh trong vòng
lặp), nhạy siêu tham số và cần model đủ mạnh để reward không toàn 0. Thực tế: distill trước (hoặc SFT cold start), RL sau
để mài; RL thẳng khi không có thầy tốt hơn, hoặc khi tác vụ có verifier mà dữ liệu mẫu thì không có. Lưu ý giấy phép: điều
khoản của nhiều API cấm dùng output để train model cạnh tranh; model mở như R1, Qwen có giấy phép riêng cần đọc.

## Thinking budget là gì? Các API hiện nay cho bạn điều khiển nó thế nào?

Ngân sách token cho phần suy nghĩ trước câu trả lời. Theo tài liệu kiểm ngày 2026-11-01: OpenAI dùng `reasoning.effort`
(hoặc `reasoning_effort`), giá trị tuỳ model (`none` tới `max`); Gemini dùng `thinking_level`; Anthropic đã chuyển từ
`budget_tokens` (cố định, nay deprecated, các model từ 4.7 từ chối) sang `thinking: {type: "adaptive"}` cộng mức
`effort`. Điểm chung: token suy nghĩ tính tiền như token ra, thường bị ẩn (chỉ trả bản tóm tắt), và vẫn chiếm context.
Với model mở (Qwen3, gpt-oss) bạn bật tắt bằng chat template hoặc mức effort trong system prompt, và có thể ép ngân sách
bằng budget forcing (s1): cắt suy nghĩ ở N token rồi chèn "Final answer:", hoặc chèn "Wait" để kéo dài. Ở sản phẩm, đặt
ngân sách theo loại request và đo đường cong accuracy theo token trên tập của mình: quá nhiều là "overthinking", tốn tiền
mà không thêm điểm.

## Bạn đánh giá một model "reasoning" mới tự train thế nào cho trung thực?

Tập giữ lại ghim, không giao với dữ liệu train (kiểm n-gram, 13-gram là mức GPT-3 dùng); bộ trích đáp số cố định và
công bố, tách đo "đúng nội dung" (trích dễ dãi) và "đúng định dạng" (trích chặt), vì GRPO dễ tăng định dạng mà nhìn như
tăng độ chính xác; báo khoảng tin cậy (bootstrap theo cặp trên cùng câu) và nhiều seed train; cùng ngân sách token khi
so (một model nghĩ dài hơn thắng có thể chỉ vì tiêu nhiều compute hơn); so với baseline rẻ (CoT prompt tốt hơn,
self-consistency của model gốc); thêm benchmark biến thể để kiểm học thuộc (GSM-Symbolic đổi số và tên trong câu
GSM8K, nhiều model tụt điểm); đọc lỗi bằng mắt.

## Case: sản phẩm gia sư toán cho học sinh cấp 2, ngân sách cố định mỗi tháng. Thiết kế phần "giải bài" thế nào?

Đóng bài toán: đầu vào là đề tiếng Việt (có thể ảnh), đầu ra là lời giải từng bước đúng và đáp số; sai đáp số là lỗi
nghiêm trọng, chậm vài giây chấp nhận được. Các lớp:

1. **Định tuyến theo độ khó**: model nhỏ, rẻ, không nghĩ (hoặc effort thấp) giải trước; kiểm đáp số bằng một bước
   rẻ (thay số ngược vào đề bằng code, hoặc bỏ phiếu 3 mẫu song song); không nhất quán thì chuyển lên model reasoning
   effort cao.
2. **Verifier bằng code**: với bài số học, cho model viết biểu thức/chương trình Python và chạy trong sandbox; đáp số lấy
   từ kết quả chạy, lời giải chữ lấy từ model. Loại được lỗi tính toán, thứ model nhỏ hay sai nhất.
3. **Đánh giá**: tập ghim vài trăm bài theo chương trình học (không trích từ GSM8K tiếng Anh), nhãn đáp số; đo accuracy,
   chi phí và p95 độ trễ theo từng tuyến; bootstrap theo cặp khi đổi model hay prompt.
4. **Chi phí**: ước lượng token ra trung bình mỗi tuyến × tỉ lệ request đi tuyến đó × giá; reasoning effort cao chỉ cho
   phần nhỏ bài khó. Theo dõi token suy nghĩ vì chúng ẩn mà vẫn tính tiền.
5. **Về lâu dài**: nếu lưu lượng lớn, distill lời giải đúng (đã kiểm bằng code) từ model mạnh sang model nhỏ tự host,
   có thể GRPO thêm với reward là đáp số; nhưng chỉ khi số đo cho thấy tuyến model nhỏ là chỗ tốn tiền nhất.

## Case: team muốn "train một reasoning model riêng" cho nghiệp vụ tính thuế nội bộ bằng GRPO. Bạn tư vấn gì?

Hỏi trước ba điều. (1) **Reward kiểm được không?** Tính thuế có quy tắc rõ, đáp số là con số: viết được checker từ hệ
thống tính hiện có, đó là điều kiện cần của RLVR. (2) **Model gốc đã giải được một phần chưa?** Đo pass@k của model
định dùng trên vài trăm case thật: nếu pass@16 gần 0 thì GRPO không có tín hiệu (mọi nhóm reward 0), cần SFT cold start
bằng lời giải mẫu trước; nếu pass@1 đã cao thì có thể chỉ cần prompt tốt hơn hoặc tool gọi hàm tính thuế. (3) **Có cần
model tự tính không?** Thường đáp án tốt nhất là agent gọi hàm tính thuế (module 16) và model chỉ hiểu đề, chọn quy tắc,
giải thích: ít rủi ro sai số, kiểm toán được.

Nếu vẫn train: tập train và tập giữ lại tách theo khách hàng/kỳ thuế; reward gồm đúng đáp số và đúng định dạng, kiểm
chặt; LoRA trên model 7B tới 14B, G = 8 tới 16, theo dõi reward, độ dài, tỉ lệ nhóm std = 0, KL và độ chính xác trên tập
giữ lại bằng bộ trích độc lập; nhiều seed; so với baseline prompt + self-consistency và distill từ model lớn. Ước lượng
chi phí sinh (phần lớn thời gian train là sinh). Kế hoạch rollback và đánh giá lại mỗi khi luật thuế đổi.

## Vì sao độ dài câu trả lời tăng trong lúc train GRPO? Điều đó có tốt không?

Ba nguyên nhân chồng nhau. (1) Nghĩ dài hơn thật sự giúp giải đúng hơn, nên lời giải dài được thưởng: điều mong muốn,
như R1-Zero báo cáo. (2) Thiên vị của loss: gộp kiểu GRPO gốc (trung bình theo từng chuỗi rồi theo chuỗi) làm mỗi token
của lời giải sai và dài bị phạt nhẹ hơn lời giải sai và ngắn, nên model không có áp lực rút ngắn lời giải sai; Dr. GRPO
và DAPO bỏ thiên vị này bằng cách chia cho hằng số hoặc tổng số token. (3) Cắt cụt: lời giải chạm `max_completion_length`
bị cắt thường sai, kéo theo tín hiệu nhiễu (DAPO lọc hoặc phạt mềm mẫu quá dài). Không tự động tốt: phải xem độ dài tăng
có đi cùng độ chính xác trên tập giữ lại không, và chi phí inference tăng theo. Với model nhỏ và GSM8K, độ dài có thể
**giảm** (model học bỏ phần thừa để kịp định dạng); điều đáng báo cáo là xu hướng và lý do, không phải một chiều cố định.
