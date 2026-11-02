---
title: MCP server và client với SDK mcp - tool, resource, cầu nối vào agent
level: intermediate
services: []
files:
  - path: starter/server.py
    note: build_server TODO (3 tool, 2 resource)
  - path: starter/bridge.py
    note: to_openai_tool, to_observation, MCPToolbox TODO
  - path: tests/test_mcp.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/16-ai-agents/exercises/intermediate/01-mcp-server-client -q
  - uv run python tracks/ai-engineer/modules/16-ai-agents/exercises/intermediate/01-mcp-server-client/starter/server.py
---

## Mục tiêu

Đóng gói tool của hiệu sách thành một **MCP server** bằng SDK `mcp` (bản 2.x, giao thức 2026-07-28), rồi viết phía
client: đổi tool MCP sang spec mà vòng ReAct của bạn hiểu, đổi kết quả MCP thành `Observation`, và một client đồng bộ
`MCPToolbox` dùng **thay** `ToolRegistry` trong `run_react`. Chạy được cả trong tiến trình (test nhanh) lẫn qua stdio
(server là tiến trình con, đúng cách Claude Desktop, VS Code hay Cursor gọi server MCP).

## Đề bài

**Phần cứng:** CPU · ~90 phút

1. `starter/server.py`: `build_server()` tạo một `MCPServer("hieu-sach")` **mới** (tồn kho riêng mỗi lần gọi) với
   tool `search_books`, `get_book`, `place_order` và resource `catalog://categories`, template `book://{book_id}`
   đúng như docstring. Ràng buộc `limit` và `quantity` trong khoảng 1..10 phải nằm **trong schema** (để model thấy và
   SDK tự kiểm), không chỉ trong thân hàm. Lỗi nghiệp vụ dùng `ToolError` với thông điệp giúp model tự sửa.
2. `starter/bridge.py`:
   - `to_openai_tool(tool)`: `mcp.types.Tool` thành spec OpenAI (bỏ `title` ngoài cùng của `input_schema`).
   - `to_observation(result)`: `CallToolResult` thành `Observation` (lỗi có tiền tố `ERROR: `; `structured_content`
     dạng `{"result": x}` thì lấy `x`; JSON dạng chữ thì dump lại gọn).
   - `MCPToolbox`: context manager đồng bộ bọc `mcp.Client` qua `anyio.from_thread.start_blocking_portal`;
     `specs()`, `call(name, args)` (không bao giờ ném lỗi tool, kể cả lỗi mức giao thức `MCPError`),
     `read_resource(uri)`.
3. Chạy server bằng lệnh thứ hai ở trên: nó chờ JSON-RPC trên stdin (thoát bằng Ctrl+C). Thử thêm bằng MCP Inspector
   nếu có Node: `npx @modelcontextprotocol/inspector uv run python <đường dẫn server.py>`.

Mục 4 lý thuyết giải thích host/client/server, tool/resource/prompt, transport, những gì đổi ở bản đặc tả
2026-07-28, và vì sao một MCP server là một bề mặt tấn công.

## Tiêu chí đạt

- Client trong tiến trình thấy đúng 3 tool có description, `required` và giới hạn `minimum`/`maximum` đúng.
- `search_books` không phân biệt hoa thường, đúng thứ tự, đúng `limit`; query rỗng, mã sách sai, hết hàng,
  `quantity` 11 đều là lỗi tool (`is_error`), không phải exception; `place_order` trừ tồn kho trong cùng server, mã
  đơn tăng dần, server mới có tồn kho mới, `BOOKS` gốc không đổi.
- Resource tĩnh và template được liệt kê đúng, đọc ra JSON đúng.
- `to_openai_tool`, `to_observation` đúng trên 8 trường hợp dựng sẵn.
- `MCPToolbox` chạy được cả với `MCPServer` trong tiến trình lẫn `StdioServerParameters` (tiến trình con Python),
  chấp nhận tham số dạng chuỗi JSON, chặn tham số không phải object, đổi `MCPError` thành `Observation(False, ...)`.

## Gợi ý

### Gợi ý 1

`@server.tool()` đọc type hint và docstring giống `tool_spec` của bài Basic 01. Ràng buộc số dùng
`Annotated[int, Field(ge=1, le=10)]` (pydantic): SDK chuyển nó thành `minimum`/`maximum` trong `inputSchema` và tự
trả lỗi tool khi model vi phạm. Định nghĩa các hàm tool **bên trong** `build_server` để chúng dùng tồn kho của đúng
server đó. Test nhanh bằng `async with Client(build_server()) as c: await c.list_tools()` trong `asyncio.run`.

### Gợi ý 2

`start_blocking_portal()` là context manager trả về một portal chạy event loop ở thread khác. Giữ cả portal lẫn
context manager của client làm thuộc tính để `__exit__` đóng theo thứ tự ngược lại.
`portal.wrap_async_context_manager(Client(server))` trả một context manager **đồng bộ**; `portal.call(fn, *args)` chạy
một coroutine function và chờ kết quả. Không phải mọi lỗi đều là `is_error`: lỗi mức giao thức (JSON-RPC error) ném
`MCPError` ở phía client.
