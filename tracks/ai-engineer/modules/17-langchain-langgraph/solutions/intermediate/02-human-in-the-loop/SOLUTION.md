# Lời giải: human-in-the-loop với interrupt

## Cách làm

**`route_after_agent`.** Message cuối là `AIMessage` có `tool_calls` thì `"review"`, ngược lại `END`. Mọi tool call
đều đi qua `review`, kể cả tool an toàn: một chỗ duy nhất quyết định cái gì cần người.

**`make_review`.** Duyệt các tool call theo thứ tự và dựng hai thứ: danh sách call (đã sửa nếu cần) và các
`ToolMessage` trả lời ngay.

- `ask_user`: `answer = interrupt({"type": "ask", "question": ...})`, rồi `ToolMessage(answer, tool_call_id=...)`.
  Hỏi lại được mô hình hoá như **một tool**: model tự quyết khi nào thiếu dữ kiện (như quyết định gọi `search_law`), và
  câu trả lời quay lại đúng giao thức tool call, không cần loại message riêng.
- Tool nhạy cảm: `interrupt({"type": "approve", "tool", "args"})`. `approve` giữ call; `edit` thay `args` của **chính**
  call đó (giữ `id`); `reject` giữ call trong AIMessage nhưng thêm `ToolMessage("REJECTED: <lý do>", status="error")`.
  Không được bỏ call bị từ chối khỏi AIMessage: `ToolMessage` của nó thành mồ côi, và các API kiểu OpenAI từ chối
  lịch sử có `tool_call_id` không khớp call nào.
- Trả `Command(goto="tools" | "agent", update={"messages": [AIMessage(..., id=ai.id), *replies]})`. Cùng `id` nên
  `add_messages` **thay** AIMessage cũ: state ghi tham số đã thực thi thật, không phải bản nháp model đề xuất (audit
  log cần đúng điều này). Tạo AIMessage mới không có `id` là có hai AIMessage, một bản nháp không bao giờ được trả lời.

**Vì sao `review` không chạy tool.** Khi resume, LangGraph chạy lại node bị dừng **từ dòng đầu**; các `interrupt` đã
có giá trị thì trả ngay giá trị đó, `interrupt` kế tiếp thì dừng tiếp. Với hai tool call `[send_email, ask_user]`: lần
resume thứ nhất (duyệt) chạy lại `review`, đi qua `send_email` rồi dừng ở `ask_user`; lần resume thứ hai chạy lại
`review` **một lần nữa**. Gửi email trong `review` là gửi hai lần (test
`test_approval_then_question_side_effect_once` bắt đúng chuyện này). Quy tắc chung: code trước `interrupt` phải
idempotent; tác dụng phụ nằm ở node **sau** điểm dừng.

**`make_tool_runner`.** Tìm AIMessage cuối, chạy các call **chưa có** `ToolMessage` (đã hỏi lại hoặc đã từ chối thì
bỏ qua), bắt mọi exception thành `ToolMessage("ERROR: ...", status="error")`. `ToolNode` dựng sẵn không làm được vì
nó chạy mọi call của AIMessage cuối. Cũng lưu ý mặc định của `ToolNode` ở `langgraph-prebuilt` 1.1.1: chỉ lỗi tham số
(`ToolInvocationError`) thành observation, còn exception khi tool chạy thì bị **ném lại** và làm hỏng cả lần chạy; muốn
hành vi "lỗi là observation" như module 16 phải đặt `handle_tool_errors=True`.

**`build_app`.** `add_node("review", make_review(sensitive), destinations=("tools", "agent"))` vì node trả `Command`
chứ không có cạnh tĩnh. Compile với checkpointer: `interrupt` **bắt buộc** có checkpointer, vì state lúc dừng phải nằm
đâu đó cho lần resume.

**`start`, `resume`.** Sau mỗi `invoke`, đọc `app.get_state(config).interrupts`: có thì trả `(None, [i.value ...])`,
không thì trả nội dung message cuối. `resume` kiểm trước là thread có đang chờ không: `invoke(Command(resume=x))` trên
thread đã chạy xong không báo lỗi mà trả lại state cũ, còn trên thread chưa tồn tại thì ném một `KeyError` khó hiểu
(thử trên LangGraph 1.2.16, log `.superpowers/scratch/logs/resume_without_interrupt.log`), nên lỗi phải được bắt ở tầng
của bạn. Ở LangGraph
1.2.16, `invoke(..., version="v2")` trả `GraphOutput(value, interrupts)` thay vì dict có khoá `__interrupt__`; đọc
`get_state` thì dùng được với cả hai.

## Đánh đổi khi đưa vào sản phẩm

- **Ai trả lời interrupt.** Hỏi lại thì người hỏi trả lời; duyệt gửi email ra ngoài thì có thể là người khác (quản lý).
  Giá trị interrupt nên mang đủ thông tin để người duyệt quyết định mà không cần đọc cả hội thoại.
- **Hết hạn.** Thread chờ duyệt mãi chiếm chỗ trong checkpointer; cần thời hạn và đường hủy.
- **Duyệt theo chính sách, không theo cảm tính.** Danh sách `sensitive` là code, không phải prompt: model không lách
  được. Module 16 mục 6 dùng cùng ý (guard bằng code) cho agent điều khiển trình duyệt; module 19 đi sâu.
