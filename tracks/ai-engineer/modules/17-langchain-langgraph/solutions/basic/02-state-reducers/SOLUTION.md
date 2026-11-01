# Lời giải: StateGraph tra cứu nhiều vế

## Cách làm

**`merge_evidence`.** Duyệt `left` rồi `right`, giữ trong một dict theo `uid` bản tốt hơn theo khoá
`(score, -part)`: điểm cao hơn thắng, bằng điểm thì `part` nhỏ hơn thắng. Rồi `sorted(..., key=(-score, uid))`. Hai
điểm dễ sai:

- **Quy tắc bằng điểm phải đầy đủ.** "Bằng điểm thì giữ bản cũ" nghe tự nhiên nhưng "cũ" là bản được áp trước. Ở
  LangGraph 1.2.16, `apply_writes` sắp các task theo đường dẫn (tên node, chỉ số `Send`) trước khi áp, nên thứ tự là
  tất định chứ không phụ thuộc thread nào xong trước; nhưng nó gắn với thứ tự các vế trong câu hỏi, và là chi tiết cài
  đặt có thể đổi giữa các phiên bản. Với quy tắc "giữ bản cũ", chỉ cần người dùng viết hai vế theo thứ tự ngược lại là
  evidence gắn với vế khác. Test gộp 20 thứ tự và chạy đồ thị với các vế đảo thứ tự bắt được điều này. Reducer của khoá
  được ghi song song phải **giao hoán và kết hợp**.
- **Không sửa list đầu vào.** LangGraph giữ giá trị cũ trong checkpoint; sửa tại chỗ là sửa luôn lịch sử.

**`ResearchState`.** `evidence: Annotated[list[Evidence], merge_evidence]`, `attempts: Annotated[int, operator.add]`.
`parts` không có reducer vì `rewrite` **thay** danh sách. Bỏ reducer của `evidence` thì hai nhánh `retrieve` cùng bước
ghi một khoá và LangGraph ném `InvalidUpdateError: At key 'evidence': Can receive only one value per step`; dùng
`operator.add` thì không lỗi nhưng điều trùng xuất hiện hai lần và mất thứ tự theo điểm.

**`route_parts`.** "Chưa tra" = không có evidence nào gắn `part` đó. Nhờ vậy cùng một hàm dùng được sau `split` (mọi
vế) và sau `rewrite` (chỉ vế vừa đổi tên), không cần cờ trạng thái riêng. Không còn vế nào thì trả `"answer"`: một
hàm định tuyến trả list `Send` rỗng làm đồ thị **dừng im lặng** không có câu trả lời.

Hệ quả cần biết: vế tra ra rỗng thì vẫn được coi là "chưa tra"; nếu `rewrite_fn` trả lại đúng chuỗi cũ thì vế đó bị
tra lại tới hết ngân sách. Ngân sách `max_attempts` là thứ chặn trường hợp này, đúng như vai trò của `max_steps` trong
vòng ReAct module 16.

**`should_continue`.** `"answer"` khi không còn vế yếu hoặc `attempts >= max_attempts`. Dùng `>` là chạy thừa một
vòng (test ngân sách bắt được).

**`build_graph`.** Năm node; `add_conditional_edges("split", route_parts, ["retrieve", "answer"])` (khai báo đích để
đồ thị vẽ được và LangGraph kiểm tra tên node); `add_edge("retrieve", "judge")` làm `judge` chạy **một lần** sau khi
mọi nhánh `Send` của bước đó xong (mô hình superstep kiểu Pregel); `partial(should_continue, min_score=...,
max_attempts=...)` cho cạnh từ `judge`. Node `retrieve` khai báo input `PartState`, nên nó nhận đúng `{"part": p}` từ
`Send`, còn cập nhật nó trả về đi qua reducer của state chung.

## Kiểm thêm

Chạy `build_graph(...).get_graph().draw_mermaid()` để in sơ đồ mermaid của đồ thị đã compile và so với sơ đồ trong đề.
Đồ thị này dừng nhờ `max_attempts`, không nhờ framework. `recursion_limit` (số superstep tối đa của một lần chạy) mặc
định là **10 007** ở LangGraph 1.2.16 (đọc từ biến môi trường `LANGGRAPH_DEFAULT_RECURSION_LIMIT`; các bản cũ hơn dùng 25
của LangChain): một đồ thị lặp vô hạn bằng hàm Python mất 3.2 giây mới chạm giới hạn đó trên PC của track (log
`.superpowers/scratch/logs/recursion_limit.log`), còn một agent gọi LLM thì có thể là hàng nghìn lượt gọi model. Luôn có
điều kiện dừng trong state, và đặt `recursion_limit` tường minh trong config như lưới an toàn thứ hai.
