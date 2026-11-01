# Lời giải: MCP server và client

## Server

`build_server()` dựng một `MCPServer` mới mỗi lần gọi, với bản sao sâu của `BOOKS` và danh sách đơn **bên trong**
closure: các hàm tool định nghĩa trong `build_server` dùng đúng trạng thái của server đó. Test dựng nhiều server liên
tiếp; trạng thái toàn cục làm đơn của test này rơi sang test khác.

Ba lựa chọn đáng nói:

- **Ràng buộc trong schema** (`Annotated[int, Field(ge=1, le=10)]`): SDK đưa `minimum`/`maximum` vào `inputSchema`
  (model nhìn thấy giới hạn trước khi gọi) và tự trả lỗi tool khi bị vi phạm. Kiểm trong thân hàm thì model chỉ biết
  sau một lượt hỏng.
- **`ToolError` cho lỗi nghiệp vụ**: SDK chuyển nó thành kết quả `is_error: true` có nguyên thông điệp ("không đủ
  hàng: B24 còn 0 cuốn, yêu cầu 1"). Exception khác cũng thành `is_error` nhưng SDK giấu thông điệp ("Error executing
  tool ...") để không lộ chi tiết nội bộ: model không có gì để sửa.
- **`place_order` có tác dụng phụ**: description nói rõ; trong ứng dụng thật nó cần xác nhận của người dùng ở phía
  host, và `user_id` phải lấy từ phiên đăng nhập chứ không phải tham số do model điền (mục 4 lý thuyết).

Resource là dữ liệu chỉ đọc mà **host** (ứng dụng) chọn đưa vào context, khác tool là thứ **model** chọn gọi. Template
`book://{book_id}` cho phép đọc một bản ghi theo URI; resource không có thì ném lỗi, client nhận `MCPError`.

## Bridge

- `to_openai_tool` bỏ `title` ngoài cùng (`"get_bookArguments"`, do pydantic sinh): vô nghĩa với model, tốn token.
  `title` bên trong từng thuộc tính giữ nguyên cho đơn giản; bỏ luôn cũng được.
- `to_observation`: SDK bọc giá trị không phải object trong `{"result": ...}` ở `structured_content`; mở ra để model
  thấy đúng thứ hàm trả. Với hàm trả `dict` không có schema, SDK chỉ gửi text JSON có thụt lề; dump lại gọn tiết kiệm
  token (đo trên 10 bản ghi sách của server: JSON thụt lề 2 dấu cách dài hơn bản gọn 11.5% số ký tự).
- `MCPToolbox`: SDK là async, vòng ReAct của bạn là đồng bộ. `start_blocking_portal()` chạy event loop ở một thread
  riêng; `wrap_async_context_manager` mở/đóng `Client` **trong** event loop đó (task group của anyio phải vào và ra
  trong cùng một task, nên không thể gọi `__aenter__`/`__aexit__` rời rạc từ ngoài). Đóng theo thứ tự ngược lại: client
  rồi portal. `specs()` lấy một lần lúc mở: danh sách tool của giao thức 2026-07-28 có thể cache (`ttlMs`), và gọi
  `list_tools` mỗi bước của agent là lãng phí.

## Số đo

Trên PC của track (mcp 2.3.0, giao thức 2026-07-28): mở kết nối trong tiến trình mất 0.02 giây, mỗi lời gọi
`get_book` 0.7 ms; qua stdio (khởi động tiến trình Python con) mở kết nối 0.77 giây, mỗi lời gọi 2.4 ms. Cả hai nhỏ hơn
hàng nghìn lần một lượt LLM (vài giây): chi phí của MCP nằm ở **token mô tả tool** trong mỗi request, không ở giao thức.

## Bẫy thường gặp

- Dùng `from mcp.server.fastmcp import FastMCP` theo hướng dẫn cũ: SDK 2.x đã đổi tên thành `MCPServer` và báo lỗi
  kèm link hướng dẫn chuyển đổi.
- In log ra **stdout** trong server stdio: stdout là kênh JSON-RPC, một dòng `print` làm hỏng giao thức. Log ra stderr.
- Coi mọi lỗi là `is_error`: lỗi mức giao thức (JSON-RPC error, ví dụ server báo hết hạn mức) là exception `MCPError`
  phía client, phải bắt riêng.
- Gọi `asyncio.run` cho mỗi lời gọi tool: mỗi lần mở lại kết nối (với stdio là khởi động lại tiến trình, gần 1 giây).
