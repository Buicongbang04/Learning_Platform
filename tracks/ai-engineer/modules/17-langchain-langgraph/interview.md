# Câu hỏi phỏng vấn: LangChain & LangGraph

## LCEL là gì? `prompt | model | parser` thật ra tạo ra cái gì?

LCEL (LangChain Expression Language) là cách ghép các thành phần thành một `Runnable`. Mọi thành phần (prompt template,
chat model, output parser, retriever, hàm bọc `RunnableLambda`) cùng cài một giao diện: `invoke`, `batch`, `stream` và
bản async `ainvoke`, `abatch`, `astream`, cộng `with_retry`, `with_fallbacks`, `with_config`. Toán tử `|` gọi
`__or__` và trả một `RunnableSequence`: output bước trước là input bước sau. Một dict trong chuỗi được đổi thành
`RunnableParallel` (chạy các nhánh trên cùng input, trả dict kết quả); `RunnablePassthrough.assign(k=r)` giữ dict đầu vào
và thêm khoá `k`.

Cái được: mọi chuỗi tự có batch song song, streaming, retry, fallback, callback và tracing (LangSmith) mà không viết thêm
code. Cái mất: một tầng trừu tượng (stack trace dài, kiểu dữ liệu đi qua mỗi bước khó thấy), và overhead nhỏ: trên PC của
track, một `prompt | fake_model | parser` tốn khoảng 0.6 ms mỗi lần gọi, không đáng kể so với vài giây của một lượt LLM
thật, nhưng đáng kể nếu bạn bọc hàng nghìn hàm Python nhỏ thành `RunnableLambda`.

## `with_structured_output` hỏng theo những cách nào? Bạn xử lý thế nào?

Ba cách, và chúng **không** giống nhau. Với cách mặc định dựa trên tool calling: tham số sai schema ném
`ValidationError`; model gọi một tool lạ ném `OutputParserException`; model trả chữ thường (không gọi tool) thì parser
trả **`None`** mà không báo lỗi. Cái thứ ba nguy hiểm nhất vì `None` đi tiếp vào pipeline và lỗi xuất hiện ở chỗ khác.

Xử lý: biến `None` thành exception ngay sau bước structured output; **không** retry lỗi output với `temperature` 0 (cùng
prompt, cùng model cho cùng kết quả), mà dùng fallback (một cách khác: model khác, method khác như `json_schema` dùng
constrained decoding, hoặc một phân tích không dùng LLM); chỉ retry lỗi tạm thời (mất kết nối, timeout, 429). Và ép
không gian output càng hẹp càng tốt: `Literal`, `bool`, enum thay cho chữ tự do. Ở bài Intermediate 03, đổi trường
"thông tin còn thiếu" tự do thành hai trường `traffic_fine: bool` và `vehicle: Literal[...]` rồi để code suy ra quyết định
đã biến một bước lập kế hoạch gần như vô dụng với model 3B thành dùng được.

## Vì sao cần LangGraph khi đã có LCEL?

LCEL mô tả một **DAG không trạng thái**: dữ liệu đi một chiều qua các bước. Agent cần ba thứ LCEL không có: **vòng lặp**
(gọi model, chạy tool, quay lại), **state** chung được nhiều bước đọc và ghi theo quy tắc rõ ràng, và **điều khiển luồng
lúc chạy** (đi đâu tiếp phụ thuộc kết quả). LangGraph mô hình hoá ứng dụng thành `StateGraph`: state có kiểu, node là
hàm `state -> cập nhật`, cạnh thường và cạnh có điều kiện, `Send` cho fan-out động, `Command` cho "cập nhật và đi tới".
Kèm theo là những thứ khó tự viết cho đúng: checkpoint mỗi bước, thread, time travel, `interrupt` cho human-in-the-loop,
streaming theo node và theo token.

Dùng LCEL (hoặc code thường) cho các bước cố định; LangGraph khi có vòng lặp, rẽ nhánh theo kết quả, cần dừng chờ người
hay cần sống qua lần khởi động lại.

## Reducer trong LangGraph là gì? Chuyện gì xảy ra khi hai node song song cùng ghi một khoá?

Mỗi khoá của state có một reducer `(giá_trị_cũ, cập_nhật) -> giá_trị_mới`. Không khai báo thì là ghi đè. LangGraph chạy
theo **superstep** (kiểu Pregel / BSP): mọi node được kích hoạt trong một bước chạy song song, đọc cùng một state, rồi các
cập nhật được áp vào state qua reducer ở cuối bước. Hai node cùng ghi một khoá **không có reducer** trong cùng bước thì
LangGraph ném `InvalidUpdateError` ("Can receive only one value per step") vì không biết giữ cái nào.

Reducer cho khoá được ghi song song phải **giao hoán và kết hợp**. LangGraph 1.2.16 áp các cập nhật theo thứ tự tất
định (sắp theo tên node và chỉ số `Send`), nhưng đó là chi tiết cài đặt, không phải cam kết của API. Ví dụ hỏng tinh vi:
gộp evidence theo uid, "bằng điểm thì giữ bản cũ": đồ thị chạy được nhưng kết quả phụ thuộc thứ tự các vế trong câu hỏi
hay tên node, tức những thứ không mang nghĩa, và có thể đổi khi nâng phiên bản.
Reducer cũng không được sửa đầu vào tại chỗ, vì giá trị cũ nằm trong checkpoint. `add_messages` là reducer có sẵn cho
message: nối thêm, **thay** message cùng `id`, xoá bằng `RemoveMessage`; `Overwrite(value)` bỏ qua reducer khi cần ghi đè.

## Checkpointer lưu gì, khi nào? Thread là gì?

Checkpointer lưu một **snapshot của toàn bộ state** sau mỗi superstep (cộng các write đang chờ), gắn với `thread_id`
trong config. Một lượt hội thoại một node tạo 3 checkpoint: `input`, trước node, sau node. Thread là một dòng thời gian
độc lập: mỗi người dùng, mỗi cuộc hội thoại một thread. Snapshot có `values`, `next` (node sẽ chạy), `config` (có
`checkpoint_id`), `parent_config`, `metadata` (`step`, `source`), và `interrupts`.

Chúng cho: trí nhớ ngắn hạn (lượt sau thấy lượt trước mà không phải truyền lại lịch sử), chạy tiếp sau lỗi hay khởi động
lại (durable execution), human-in-the-loop (dừng chờ người, có thể nhiều giờ), time travel. Giá phải trả: mỗi checkpoint
là state đầy đủ, nên dung lượng tăng theo bình phương số lượt với hội thoại dài (đo bằng fake model: 10 lượt 0.21 MB,
100 lượt 19.4 MB blob trong SQLite), và đó là **dữ liệu cá nhân** cần chính sách lưu và xoá (`delete_thread`).

## Time travel trong LangGraph: replay và fork khác nhau thế nào? Dùng vào việc gì?

`get_state_history(config)` liệt kê mọi checkpoint của thread. **Replay**: `invoke(None, config_có_checkpoint_id)` chạy
lại các node sau checkpoint đó (gọi lại LLM, nên kết quả có thể khác nếu sampling). **Fork**: từ một checkpoint cũ, gửi
input mới hoặc `update_state` để sửa state, rồi chạy tiếp; LangGraph tạo checkpoint mới có `parent_config` là checkpoint
cũ, đầu thread chuyển sang nhánh mới, nhánh cũ vẫn còn và đọc lại được bằng `checkpoint_id`.

Dùng để: debug (quay lại bước agent bắt đầu đi sai, sửa một tool result, xem nó làm gì khác), "sửa câu hỏi trước" trong
UI chat, thử A/B một prompt trên cùng trạng thái giữa chừng. Bẫy: `get_state_history` trộn mọi nhánh; muốn đúng nhánh
hiện tại thì đi ngược theo `parent_config`.

## `interrupt` hoạt động thế nào? Vì sao tác dụng phụ không được nằm trước `interrupt` trong cùng node?

`interrupt(value)` trong một node lưu checkpoint, dừng đồ thị và trả `value` cho người gọi (trong `snapshot.interrupts`
hoặc khoá `__interrupt__` của kết quả). `invoke(Command(resume=x), config)` chạy lại **node đó từ dòng đầu**; lần này
`interrupt` trả `x` thay vì dừng. Một node có nhiều `interrupt` thì giá trị resume khớp theo thứ tự gọi. Bắt buộc có
checkpointer.

Vì node chạy lại từ đầu mỗi lần resume, mọi code trước `interrupt` chạy nhiều lần: gửi email, ghi database, trừ tiền
trước `interrupt` là làm hai lần. Quy tắc: code trước `interrupt` phải idempotent; tác dụng phụ đặt ở node sau điểm dừng.
Bài Intermediate 02 có test bắt đúng lỗi này với hai tool call `[send_email, ask_user]` trong cùng một lượt.

## Thiết kế human-in-the-loop cho một agent có tool gửi email và chuyển tiền

Tách tool theo rủi ro bằng **code**, không bằng prompt: danh sách tool nhạy cảm là cấu hình mà model không lách được. Mọi
tool call đi qua một node `review`: tool an toàn chạy luôn; tool nhạy cảm `interrupt` với payload đủ để người duyệt quyết
định (tên tool, tham số, ngữ cảnh ngắn, số tiền); người duyệt `approve`, `edit` (sửa tham số) hay `reject` kèm lý do.
`edit` thay tham số **trong chính** AIMessage (cùng `id`, `add_messages` thay thế) để audit log ghi cái đã thực thi thật;
`reject` trả một `ToolMessage` lỗi cho đúng tool call để model biết và không có tool call nào bị bỏ lửng (API kiểu OpenAI
từ chối lịch sử như vậy). Tool chạy ở node riêng sau `review`.

Hạ tầng: checkpointer bền (Postgres), payload interrupt đưa vào hàng đợi duyệt của UI; thời hạn và đường huỷ cho thread
chờ quá lâu; người duyệt có thể khác người hỏi (phân quyền); idempotency key cho tác dụng phụ để lỡ chạy lại cũng không
chuyển tiền hai lần; log mọi quyết định. Với chuyển tiền, thêm giới hạn cứng trong code (hạn mức, danh sách người nhận)
trước cả bước duyệt.

## Prebuilt agent (`create_react_agent`, `ToolNode`) hay tự dựng đồ thị?

Prebuilt nhanh để có một agent chạy được, nhưng bạn nhận luôn các mặc định của nó. Hai ví dụ đo được trên LangGraph
1.2.16: `ToolNode` mặc định chỉ biến lỗi **tham số** thành observation, còn exception khi tool chạy (một `ValueError` vì
sai mã sách) bị ném lại và làm hỏng cả lần chạy, nên agent prebuilt mặc định sập ngay khi model đoán sai một mã sách. Và `create_react_agent` đã bị đánh dấu deprecated, chuyển sang `langchain.agents.create_agent` (gói
`langchain` 1.x, có middleware), nghĩa là API prebuilt đổi nhanh hơn API lõi.

Tự dựng một vòng ReAct bằng `StateGraph` chỉ khoảng 30 dòng, và bạn kiểm soát ngân sách bước, xử lý lỗi, system prompt,
chỗ cắm `interrupt`. Hợp lý nhất: hiểu đồ thị tự dựng trước, dùng prebuilt khi mặc định của nó đúng với bạn, và đọc mã
nguồn của nó trước khi đưa vào production.

## Framework có làm agent "thông minh" hơn không? Bạn so LangGraph với vòng lặp tự viết thế nào?

Không. Framework đổi **cấu trúc code** và hạ tầng (checkpoint, streaming, HITL, tracing), không đổi model hay giao thức.
Đo trên 24 task hiệu sách của module 16 với `qwen2.5:3b`: agent LangGraph dùng native tool calling cho tỉ lệ đúng cùng
khoảng với vòng native tự viết, và cả hai cùng thua vòng ReAct văn bản tự viết trên model này; thứ quyết định là giao
thức gọi tool, không phải framework. Thời gian framework mỗi lượt gọi model là vài mili giây, so với giây của model.
Số dòng code: một vòng native với ngân sách bước bằng LangGraph khoảng 34 dòng, so với khoảng 138 dòng (registry sinh
schema + vòng lặp) tự viết ở module 16.

Cách so trung thực: cùng model, cùng prompt, cùng bộ task, cùng ngày, chấm tự động, khoảng tin cậy và so theo cặp; đếm cả
chi phí (lượt LLM, token, giây) và chế độ hỏng, không chỉ tỉ lệ đúng.

## Multi-agent: supervisor, swarm, hierarchical. Khi nào đáng dùng?

- **Supervisor**: một agent điều phối giao việc cho các agent chuyên trách (thường là "agent làm tool"), nhận kết quả
  và tổng hợp. Dễ kiểm soát, nhưng mọi việc đi qua điều phối viên: thêm lượt LLM, và nó có thể tự trả lời thay vì giao.
- **Swarm / handoff**: các agent ngang hàng, agent đang giữ quyền tự chuyển cho agent khác bằng tool handoff
  (`Command(goto=..., graph=Command.PARENT)`), lượt sau bắt đầu ở agent đang giữ quyền. Ít lượt trung gian hơn, nhưng
  dễ chuyển qua lại vòng vòng và khó dự đoán.
- **Hierarchical**: supervisor của các supervisor, cho hệ thống lớn.

Đáng dùng khi việc con thật sự **tách được** và **song song được** (nghiên cứu nhiều nguồn), khi một agent phải cầm quá
nhiều tool hay quá nhiều context, hoặc khi các phần do đội khác nhau sở hữu. Không đáng khi các bước phụ thuộc chặt vào
nhau (thông tin bị mất ở mỗi lần chuyển giao) hoặc khi model nhỏ: mỗi agent thêm là thêm lượt LLM, thêm token, thêm một
chỗ giao sai. Anthropic báo hệ multi-agent nghiên cứu của họ dùng khoảng 15 lần token so với chat; hãy đo trên task của
bạn (bài Advanced 01) trước khi chọn.

## Bạn test một ứng dụng LangGraph thế nào khi không muốn gọi LLM thật?

Tách ba tầng. (1) **Hàm thuần** (reducer, hàm định tuyến, parser, chọn nguồn): unit test thường, kể cả kiểm tính giao
hoán của reducer bằng nhiều thứ tự ngẫu nhiên. (2) **Đồ thị với fake model**: `GenericFakeChatModel` / `FakeListChatModel`
của `langchain-core`, subclass thêm `bind_tools` trả chính nó để `with_structured_output` và tool calling chạy được, trả
`AIMessage` có `tool_calls` theo kịch bản và ghi lại messages mỗi lần gọi; kiểm định tuyến, ngân sách bước, checkpoint và
resume, interrupt, cô lập thread, và giao thức (mỗi tool call đúng một `ToolMessage`). Tool thật thay bằng hàm có đếm số
lần gọi để bắt tác dụng phụ chạy hai lần. (3) **Đánh giá với model thật** trên bộ task ghim, chấm tự động, không phải
unit test: chạy định kỳ và khi đổi model hay prompt.

Thử "mutant": sửa lời giải theo những cách sai hợp lý (bỏ reducer, quên `start_on` khi cắt message, chạy tool trong node
có interrupt) và chắc test bắt được. Test kiểu này từng bắt một lỗi thật của framework: `batch(..., return_exceptions=True)`
của chain có `with_retry` trong `langchain-core` 1.6.12 xếp nhầm kết quả của phần tử lỗi.

## Thiết kế agent hỏi đáp pháp luật (capstone milestone 6) bằng LangGraph

Yêu cầu: tách câu hỏi nhiều vế, tra nhiều bước, hỏi lại khi thiếu thông tin, trả lời có trích dẫn, không bịa điều luật.

Đồ thị: `plan` (structured output hẹp: các vế, các trường slot như loại phương tiện; code suy ra "thiếu gì") ->
`clarify` (`interrupt` hỏi lại, tối đa một lần) -> fan-out `Send` một nhánh `retrieve` mỗi vế (hybrid + rerank từ module
13, truy vấn được code bổ sung thông tin người dùng vừa trả lời) -> reducer gộp evidence theo uid -> `answer` (mỗi vế có
chỗ riêng trong prompt, trích `[i]` kiểm bằng code, từ chối khi không có nguồn). Checkpointer Postgres theo thread để câu
hỏi đang chờ người dùng sống qua khởi động lại; `recursion_limit` đặt tường minh.

Đo: bộ câu thường (có tìm được điều đúng không), bộ câu hai vế (cả hai vế đều có nguồn đúng không), bộ câu thiếu thông
tin (có hỏi lại không, sau khi hỏi có tìm đúng điều theo câu trả lời không) và bản đủ thông tin của chúng (có hỏi thừa
không); lượt LLM, độ trễ p50/p95. Agent tốn thêm ít nhất một lượt LLM mỗi câu so với RAG một lượt, nên một bản
production nên **định tuyến**: câu đơn giản đi đường RAG một lượt, chỉ câu nhiều vế hay thiếu dữ kiện mới vào agent, và
chính quyết định định tuyến đó cũng được đo trên các bộ câu ở trên.

## LangChain, LangGraph đổi API rất nhanh. Bạn giữ một codebase ổn định thế nào?

Ghim phiên bản (`langchain-core`, `langgraph`, các gói tích hợp) và nâng có chủ đích, đọc changelog; dựa vào lớp lõi ổn
định (`Runnable`, message, `StateGraph`, checkpointer) và bọc phần prebuilt trong code của mình để thay được; test với
fake model chạy trong CI để mỗi lần nâng cấp biết ngay cái gì đổi hành vi (ví dụ `recursion_limit` mặc định ở LangGraph
1.2.16 là 10 007 thay vì 25 của các bản cũ hơn; `create_react_agent` deprecated). Schema của state là **dữ liệu đã lưu**:
đổi tên hay kiểu một khoá thì checkpoint cũ không đọc được đúng nữa, nên thêm khoá có giá trị mặc định thay vì đổi khoá cũ,
và có đường migrate hoặc xoá thread cũ.
