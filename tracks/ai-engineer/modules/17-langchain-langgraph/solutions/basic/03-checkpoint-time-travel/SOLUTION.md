# Lời giải: checkpoint và time travel

## Cách làm

**`build_chat`.** Node `chat` gửi `[SystemMessage(SYSTEM), *window]` với
`window = trim_messages(messages, strategy="last", token_counter=len, max_tokens=max_messages, start_on="human")`.
`token_counter=len` biến "token" thành "message". `start_on="human"` bỏ các message đầu cửa sổ cho tới message người
dùng đầu tiên: một cửa sổ bắt đầu bằng câu trả lời của assistant (hay tệ hơn, một `ToolMessage` không có tool call đi
trước) làm nhiều chat template báo lỗi hoặc làm model hiểu sai lượt. System prompt **không** nằm trong state: nó là cấu
hình, đổi prompt không cần sửa mọi thread đã lưu.

**`open_saver`.** `SqliteSaver(sqlite3.connect(path, check_same_thread=False))`. `SqliteSaver` có khoá riêng để tuần
tự hoá truy cập, nhưng `sqlite3` mặc định từ chối mọi kết nối dùng từ thread khác thread đã mở nó (`ProgrammingError`),
và LangGraph chạy node trên thread pool. Trong ứng dụng async dùng `AsyncSqliteSaver` (gói `aiosqlite`) hoặc Postgres.

**`turn`.** `app.invoke({"messages": [HumanMessage(text)]}, {"configurable": {"thread_id": thread_id}})`. Không cần
truyền lại lịch sử: reducer `add_messages` của `MessagesState` nối message mới vào state đọc từ checkpoint.

**`timeline`.** Từ `app.get_state(config)` (checkpoint mới nhất của thread), đi ngược theo `parent_config` tới gốc rồi
đảo ngược. `get_state_history` cho **mọi** checkpoint của thread theo thời gian giảm dần, kể cả nhánh đã bỏ: sau một lần
rẽ nhánh, nó có 9 checkpoint thay vì 6 và trộn hai nhánh. Thread chưa có gì thì `get_state` trả snapshot rỗng
(`config` không có `checkpoint_id`).

Hai lượt hội thoại cho 6 checkpoint: mỗi lượt có checkpoint `input` (step `-1` rồi `2`, nhận message mới, `next` là
`__start__`), checkpoint trước node `chat` (`next == ("chat",)`), checkpoint sau node (`next == ()`).

**`fork`.** Thêm `checkpoint_id` vào config rồi `invoke` với message mới. LangGraph tạo checkpoint mới có
`parent_config` là checkpoint đó, và checkpoint mới nhất của thread (cái `get_state` trả khi không có `checkpoint_id`)
giờ là đầu nhánh mới. Nhánh cũ không bị xoá: đọc lại được bằng `checkpoint_id` cũ. Đây là "time travel" của
LangGraph: **replay** (`invoke(None, config_có_checkpoint_id)` chạy lại các node sau checkpoint đó) và **fork**
(`update_state` hoặc input mới từ một checkpoint cũ). Lưu ý replay **gọi lại LLM**: kết quả có thể khác lần đầu nếu
`temperature` khác 0.

**`forget`.** `checkpointer.delete_thread(thread_id)` xoá mọi checkpoint và write của thread trong cả hai bảng. State
hội thoại là **dữ liệu cá nhân** (module 19): bạn cần đường xoá được kiểm thử, và cần biết bản sao lưu của tệp SQLite
vẫn còn dữ liệu cũ.

## Kiểm thêm

Sau ba lượt, bảng `checkpoints` có 9 dòng, mỗi dòng một blob `msgpack` chứa **toàn bộ** state (không phải phần chênh),
nên dung lượng tăng theo bình phương số lượt với hội thoại dài. Mục 3 lý thuyết đo kích thước và độ trễ thêm của
SQLite so với bộ nhớ.
