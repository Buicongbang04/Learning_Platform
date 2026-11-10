# Câu hỏi phỏng vấn: Evaluation & Production

## Eval offline và eval online khác nhau thế nào? Vì sao cần cả hai?

Eval **offline** chạy hệ thống trên một tập cố định có nhãn (hoặc có judge đã hiệu chuẩn) trước khi deploy: nhanh, rẻ, tái
lập được, so theo cặp trên cùng câu nên phát hiện được chênh lệch nhỏ với ít mẫu. Nó là cổng chặn hồi quy trong CI.
Giới hạn: tập cố định chỉ đại diện cho người dùng lúc tạo tập, không đo được hành vi thật (hỏi lại, bỏ đi), và không thấy
tương tác với phần còn lại của hệ thống (cache, guardrail, độ trễ thật).

Eval **online** đo trên lưu lượng thật sau khi deploy: A/B test, interleaving, canary, phản hồi người dùng, judge trên mẫu
ngẫu nhiên, guardrail metric (p95, lỗi, chi phí, tỉ lệ từ chối). Nó đo đúng thứ cần đo nhưng chậm (cần nhiều người dùng),
nhiễu, và có rủi ro (người dùng thật gặp bản tệ). Quy trình đúng: offline chặn phần lớn lỗi, online xác nhận tác động thật
và bắt drift; mỗi sự cố online thành một ca mới trong tập offline.

## Bạn có một tập eval 150 câu. Prompt mới tăng accuracy từ 0.80 lên 0.83. Có merge không?

Chưa đủ thông tin để nói "tốt hơn". Ba câu cần hỏi:

1. **Khoảng tin cậy của hiệu, theo cặp.** 150 câu, 3 điểm phần trăm là 4 hoặc 5 câu. Bootstrap theo cặp (cùng chỉ số cho
   cả hai prompt) cho khoảng 95% của hiệu; với cỡ này khoảng thường chạm 0. Nhìn số câu bất đồng (prompt cũ đúng mới sai và
   ngược lại) thay vì chỉ nhìn hai tổng.
2. **Sàn nhiễu.** Chạy lại y hệt prompt cũ (hoặc trên phần cứng khác) đổi bao nhiêu câu? Module 11 đo được 5% câu đổi nhãn
   khi chỉ đổi GPU sang CPU. Chênh lệch nhỏ hơn sàn nhiễu không phải tín hiệu.
3. **Guardrail metric và lớp hiếm.** Token, độ trễ, chi phí, F1 từng lớp, số output hỏng.

Quyết định hợp lý: merge nếu không tệ hơn ở mọi guardrail và có lý do khác (rẻ hơn, output chắc chắn hơn); không ghi
"cải thiện 3%" vào changelog. Muốn chứng minh được chênh lệch 3 điểm cần cỡ vài nghìn câu nếu hai nhóm độc lập, ít hơn
nhiều nếu so theo cặp và hai prompt bất đồng ít.

## Statistical power là gì và vì sao quan trọng khi so hai hệ thống LLM?

Power là xác suất thí nghiệm phát hiện được một chênh lệch **có thật** với kích thước cho trước. Thí nghiệm power thấp
thường kết luận "không khác biệt" khi thật ra có, và khi nó báo "có khác biệt" thì chênh lệch đo được thường bị phóng đại
(winner's curse). Số mẫu cần tăng theo $$1/\delta^2$$: phát hiện chênh lệch 5 điểm từ 80% cần cỡ một nghìn mẫu mỗi nhóm,
2 điểm cần cỡ sáu nghìn rưỡi.

Thực hành: trước khi chạy, viết ra chênh lệch nhỏ nhất đáng quan tâm (MDE) và tính số mẫu; dùng thiết kế theo cặp
(cùng câu cho cả hai hệ thống offline, interleaving online) để giảm phương sai; không dừng A/B test sớm khi thấy p < 0.05
lần đầu (peeking làm tăng tỉ lệ dương tính giả) trừ khi dùng phương pháp sequential được thiết kế cho việc đó.

## Interleaving là gì, khi nào dùng thay A/B test?

Interleaving trộn kết quả của hai ranker vào **một** danh sách cho cùng một người dùng (team-draft: hai "đội" luân phiên
chọn kết quả tốt nhất chưa có trong danh sách, tung đồng xu xem đội nào chọn trước mỗi vòng), ghi đội của từng kết quả, rồi
xem người dùng click đội nào nhiều hơn. Vì so ngay trong cùng một lượt, khác biệt giữa người dùng và câu hỏi bị loại bỏ,
nên cần ít người dùng hơn A/B để thấy cùng một khác biệt thứ tự.

Dùng khi output là danh sách (search, retrieval, gợi ý) và cần lọc nhanh nhiều ứng viên ranker. Không dùng để đo tác động
kinh doanh, độ trễ, chi phí, hay cho output sinh chữ tự do; quyết định ra mắt vẫn cần A/B. Bẫy: kết quả trùng nhau giữa
hai ranker không mang thông tin, và mô hình click (người dùng xem từ trên xuống, dừng khi hài lòng) quyết định độ nhạy.

## Làm sao biết LLM judge đáng tin? Cohen's kappa nói gì mà accuracy không nói?

Đáng tin nghĩa là judge khớp với người trên chính loại dữ liệu và tiêu chí của bạn. Cách kiểm: lấy 50 tới 200 câu có nhãn
người (giao thức gán nhãn ghi trong repo), chạy judge với model, prompt, tham số đã ghim, đo:

- **Cohen's kappa** $$\kappa = (p_o - p_e)/(1 - p_e)$$: trừ phần khớp do may rủi. Khi một lớp chiếm 90%, judge luôn nói
  lớp đó có accuracy 0.9 nhưng kappa 0. So kappa judge–người với kappa người–người trên cùng tập: đó là trần thực tế.
- **Hướng sai**: false pass (cho qua câu người nói sai) và false fail. Judge dùng để chặn hồi quy thì false pass nguy hiểm hơn.
- **Thiên vị**: đổi chỗ khi so cặp, độn chữ vô nghĩa, nguồn sai (module 13), tự ưu ái.
- **Độ ổn định**: chạy lại, số câu không đọc được verdict.

Hiệu chuẩn lại mỗi khi đổi judge, prompt judge, hoặc phân phối input thay đổi.

## Thiên vị vị trí của judge pairwise là gì, xử lý thế nào?

Judge so hai câu trả lời có xu hướng chọn theo vị trí (thường câu đứng trước, có model thích câu đứng sau) thay vì theo
nội dung, nhất là judge nhỏ. Cách xử lý chuẩn: chấm **hai lần** với hai thứ tự, đổi verdict về "A thắng / B thắng / hoà";
hai lần khác nhau thì tính là hoà (không đọc được ưu thế) và báo tỉ lệ nhất quán. Đo thiên vị bằng tỉ lệ verdict chọn vị
trí đầu trên mọi lần chấm (0.5 là không thiên vị). Nếu tỉ lệ nhất quán thấp, judge đó không dùng được cho pairwise ở tác vụ
này: đổi judge mạnh hơn, đổi định dạng (cho điểm từng câu rồi so), hoặc thêm tiêu chí cụ thể vào prompt.

## Thiết kế observability cho một trợ lý RAG phục vụ 50 000 câu hỏi mỗi ngày.

Trace mỗi request bằng OpenTelemetry: span gốc cho request (phiên bản prompt, id người dùng đã băm, câu hỏi đã che PII
hoặc chỉ độ dài), span con cho viết lại câu hỏi, retrieval (top-k, id tài liệu, điểm), rerank, mỗi lần gọi LLM (model, token
vào/ra, token cache, chi phí, độ trễ, `finish_reason`), guardrail (quyết định, lý do), tool call. Thuộc tính theo semantic
conventions GenAI để đổi backend không phải sửa code.

Metric (histogram, counter) cho dashboard và cảnh báo: request/giây, TTFT và E2E p50/p95/p99 với bucket quanh ngưỡng SLO,
tỉ lệ lỗi theo loại, token/phút, chi phí/giờ, tỉ lệ từ chối, tỉ lệ cache trúng. Cảnh báo theo burn rate của SLO, không theo
ngưỡng tức thời.

Lấy mẫu: giữ 100% trace lỗi và chậm (tail sampling ở collector), 1 tới 5% trace bình thường; nội dung prompt/câu trả lời chỉ
lưu ở mẫu nhỏ đã che PII, có hạn lưu và phân quyền đọc. Mẫu ngẫu nhiên hằng ngày đi qua judge đã hiệu chuẩn để theo dõi chất
lượng, và một phần cho người xem. Backend: Langfuse/Phoenix tự host nếu dữ liệu nhạy cảm, hoặc dịch vụ managed nếu được
phép đưa trace ra ngoài.

## Head sampling và tail sampling khác nhau thế nào?

Head sampling quyết định giữ trace ngay ở span gốc (theo trace id, ví dụ 5%), span con đi theo quyết định của cha nên trace
luôn đầy đủ. Rẻ, không cần giữ gì trong bộ nhớ, nhưng bỏ ngẫu nhiên cả những request lỗi hiếm mà bạn cần nhất. Tail
sampling quyết định sau khi trace hoàn tất (thường ở OpenTelemetry Collector): giữ mọi trace có lỗi, mọi trace chậm hơn
ngưỡng, và một tỉ lệ nhỏ trace bình thường. Đúng thứ cần debug, đổi lại collector phải giữ span của mọi trace đang mở trong
bộ nhớ và mọi span của một trace phải tới cùng một collector. Thường dùng cả hai: head sampling nhẹ ở ứng dụng khi lưu lượng
rất lớn, tail sampling ở collector.

## Vì sao một LLM server có continuous batching phục vụ được nhiều người hơn hẳn chạy từng request?

Decode bị chặn bởi băng thông bộ nhớ: mỗi bước đọc toàn bộ trọng số để sinh một token cho một chuỗi. Gộp $$b$$ chuỗi vào
cùng bước thì trọng số chỉ đọc một lần cho $$b$$ token, nên thông lượng tổng tăng gần tuyến tính theo $$b$$ cho tới khi chạm
giới hạn tính toán hoặc bộ nhớ KV. Static batching phải đợi cả batch xong; continuous batching xếp lịch từng bước decode,
chuỗi xong rời ngay, request mới vào ngay, nên GPU luôn đầy mà request không chờ batch.

Cái giá: mỗi request decode chậm hơn một chút khi batch lớn (inter-token latency tăng), và KV cache của cả batch phải vừa bộ
nhớ, đó là lý do PagedAttention quan trọng. Server không có batching (như `llama_cpp.server` một context) thì thông lượng
phẳng theo số request đồng thời, TTFT tăng tuyến tính vì request xếp hàng bên trong.

## PagedAttention giải quyết vấn đề gì?

KV cache của mỗi chuỗi tăng theo độ dài, không biết trước dài bao nhiêu. Cấp phát liền khối theo độ dài tối đa thì phí
phần lớn bộ nhớ (chỗ dành sẵn chưa dùng, phân mảnh), nên batch nhỏ. PagedAttention (vLLM) chia KV thành block cố định (ví dụ
16 token), cấp phát theo nhu cầu, và mỗi chuỗi có bảng ánh xạ block logic sang block vật lý như bộ nhớ ảo phân trang. Kết
quả: gần như không phí bộ nhớ, batch lớn hơn nhiều, và block chung (system prompt chung, beam search, nhiều mẫu cho cùng
prompt) được chia sẻ bằng copy-on-write, tức prompt caching tự động giữa các request.

## Speculative decoding hoạt động thế nào, khi nào nó không giúp?

Một cách đoán rẻ (model nháp nhỏ cùng tokenizer, hoặc tra n-gram trong prompt) đề xuất $$k$$ token; target kiểm cả khối
trong một forward, nhận phần đầu khớp, sửa token sai đầu tiên. Với greedy output trùng target; với sampling, quy tắc nhận
$$\min(1, p/q)$$ giữ đúng phân phối. Số token trung bình mỗi lượt là $$(1 - \alpha^{k+1})/(1 - \alpha)$$ với $$\alpha$$ là tỉ lệ
nhận.

Không giúp khi: tỉ lệ nhận thấp (chat tự do với model nháp yếu); forward $$k+1$$ token tốn gấp nhiều lần forward 1 token
(CPU, model nhỏ, batch lớn trên GPU đã bận tính); model nháp không đủ rẻ. Đo trên CPU của track, model nháp 0.5B cho target
3B làm tác vụ tự do **chậm hơn**, và prompt lookup của một thư viện làm decode chậm gấp ba khi đoán sai nhiều. Cũng phải
nhớ: "output không đổi" đúng về toán, nhưng kiểm theo khối đổi thứ tự cộng số thực nên có thể đổi vài token.

## Bạn được giao dựng dịch vụ hỏi đáp pháp luật cho 200 người dùng nội bộ, ngân sách một GPU 24 GB. Trình bày cách bạn đặt SLO và kiểm chứng.

1. **SLI và SLO**: TTFT p95 dưới 2 giây (stream), E2E p95 dưới 15 giây, tỉ lệ lỗi (gồm timeout, output hỏng) dưới 1%, trong
   cửa sổ 28 ngày; SLO chất lượng: điểm faithfulness của judge đã hiệu chuẩn trên mẫu 50 câu mỗi tuần không thấp hơn mốc,
   tỉ lệ từ chối đúng trên tập câu ngoài phạm vi.
2. **Ước lưu lượng**: 200 người, giờ cao điểm mỗi người 10 câu/giờ, tức khoảng 0.6 request/giây; định luật Little với E2E
   10 giây cho khoảng 6 request đồng thời.
3. **Chọn server và model**: vLLM hoặc `llama-server` có continuous batching, model 7B đến 14B quantize (module 10), context
   đủ cho 5 đoạn luật; tính KV cho 6 tới 12 chuỗi (module 21).
4. **Load test open loop** với phân phối độ dài thật (câu hỏi thật, prompt RAG thật) ở 0.5, 1, 1.5, 2 lần lưu lượng cao
   điểm; báo p95 có khoảng tin cậy, tách hàng đợi khỏi thời gian phục vụ; tìm mức tải mà TTFT p95 chạm 2 giây, giữ
   headroom ít nhất 2 lần.
5. **Prompt caching**: system prompt và chỉ dẫn cố định đặt trước, kiểm tỉ lệ cache trúng.
6. **Vận hành**: trace OpenTelemetry, cảnh báo burn rate hai cửa sổ, runbook khi vượt (giảm `max_tokens`, bật hàng đợi có
   thông báo, chặn tác vụ nền), và một bài test tải lại sau mỗi lần đổi model hoặc server.

## Một đồng nghiệp báo "server mới nhanh gấp 3 lần". Bạn hỏi lại những gì?

- **Đo cái gì**: TTFT, inter-token, E2E hay thông lượng tổng? Ở mức đồng thời nào? Một server có thể có thông lượng cao hơn
  nhưng TTFT p95 tệ hơn.
- **Load generator**: closed hay open loop? Closed loop che hàng đợi (coordinated omission). Bao nhiêu request, p95/p99 có
  khoảng tin cậy không?
- **Có công bằng không**: cùng model, cùng định dạng/quantization, cùng phân phối độ dài prompt và output (prompt ngắn và
  `max_tokens` nhỏ cho số đẹp), cùng phần cứng, có ai khác dùng máy không, cache đã ấm cả hai bên chưa?
- **Có đúng không**: tỉ lệ request thành công ở mỗi mức tải, output
  có giống không (kiểm vài chục câu trên tập eval).
- **Chi phí**: VRAM, số GPU, chi phí mỗi 1 000 request ở mức SLO.

## Tính chi phí mỗi 1 000 request cho một trợ lý RAG dùng API, và cách giảm.

Lấy phân phối token thật từ trace (không dùng một request trung bình đẹp): token vào gồm system, tài liệu, lịch sử, câu
hỏi; phần nào là prefix cố định được cache; token ra (kể cả token suy nghĩ nếu model có). Chi phí một request
$$(n_{\text{in}} - n_{\text{cache}}) p_{\text{in}} + n_{\text{cache}} p_{\text{cache}} + n_{\text{out}} p_{\text{out}}$$, cộng phí
ghi cache nếu nhà cung cấp tính riêng, nhân 1 000. Ví dụ 2 000 token vào (1 500 cache được) và 200 token ra với giá đã kiểm
ngày 2026-11-01: model nhỏ cỡ 0.17 tới 0.30 USD, model tầm trung cỡ 3 tới 6 USD mỗi 1 000 request.

Cách giảm theo thứ tự hiệu quả: đặt phần cố định trước để cache trúng; bớt tài liệu thừa (ít đoạn hơn, đoạn ngắn hơn,
rerank tốt hơn); giới hạn `max_tokens` và yêu cầu trả lời ngắn; router gửi câu dễ sang model rẻ (đo chất lượng bằng eval);
batch API cho việc không cần trả ngay; self-host khi lưu lượng đủ lớn và đều (module 21).

## Bạn đánh giá một AI code editor cho đội 30 kỹ sư thế nào?

Không dựa vào benchmark công khai hay cảm nhận (nghiên cứu có đối chứng của METR năm 2025 thấy lập trình viên giàu kinh
nghiệm chậm hơn 19% với công cụ AI thời đó dù họ tin mình nhanh hơn). Dựng bộ 20 tới 50 việc thật đã làm gần đây trên repo
của đội, mỗi việc có test ẩn hoặc tiêu chí review; chạy có và không có công cụ (hoặc hai công cụ) theo cặp; đo tỉ lệ pass
test ẩn có khoảng tin cậy, thời gian tới khi merge được, số vòng sửa của reviewer, thay đổi ngoài phạm vi, token hoặc tiền
mỗi việc. Kiểm an toàn: prompt injection qua file trong repo, quyền chạy lệnh, đọc bí mật, chính sách dữ liệu của nhà cung
cấp. Đo lại mỗi quý vì model phía sau đổi; triển khai dần (một nhóm thử trước) và theo dõi chất lượng sau merge (lỗi
production, revert).
