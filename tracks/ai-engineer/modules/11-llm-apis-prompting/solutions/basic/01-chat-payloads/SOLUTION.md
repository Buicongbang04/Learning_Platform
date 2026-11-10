# Lời giải: một hội thoại, ba phương ngữ Chat API

## Cách làm

- Hàm phụ `_arguments(raw)` nhận chuỗi JSON hoặc dict, trả dict, ném `ValueError` khi chuỗi hỏng hoặc JSON không phải
  object. Mọi chỗ đọc arguments đi qua nó, nên lỗi JSON của model lộ ra ngay ở lớp chuyển đổi.
- `to_anthropic` duyệt message một lượt: gom `system` vào một list rồi nối; `user` giữ chuỗi; `assistant` thành danh
  sách khối (`text` nếu có chữ, rồi `tool_use`); `tool` thành `tool_result`, nối vào message user trước đó nếu message
  đó đang là danh sách khối, ngược lại mở message user mới. Một tập `known_ids` kiểm `tool_call_id`.
- `parse_anthropic` dùng bảng `{"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length", "tool_use":
  "tool_calls"}`; `parse_ollama` đặt `finish_reason` là `tool_calls` khi có tool call, `length` khi `done_reason` là
  `length`, còn lại `stop`, và sinh `call_<i>` khi tool call không có `id`.

## Vì sao các lựa chọn này

- **Dạng chuẩn kiểu OpenAI**: gần như mọi server (vLLM, llama.cpp server, Ollama `/v1`, Gemini qua endpoint
  tương thích, OmniRoute) nói được phương ngữ này, nên đặt nó làm dạng nội bộ thì chỉ phải viết bộ chuyển cho số
  ít API khác. `llmkit.OpenAICompatClient` của track là ví dụ thu nhỏ.
- **Gom kết quả tool song song vào một message user**: Messages API yêu cầu mỗi `tool_use` của lượt trước có
  `tool_result` tương ứng ở message user ngay sau; tài liệu Anthropic còn nói tách chúng ra nhiều message làm model
  dần ngừng gọi song song. Chat Completions thì ngược lại: mỗi kết quả là một message `tool` riêng.
- **`arguments` là chuỗi ở OpenAI, object ở Anthropic và Ollama**: chuỗi JSON nghĩa là model có thể sinh JSON hỏng
  và API vẫn trả 200. Parse ở biên, ném lỗi rõ ràng, để vòng gọi tool (bài Intermediate 01) quyết định gửi lỗi lại
  cho model hay dừng.
- **Ollama không có `finish_reason: tool_calls`**: code chỉ nhìn `done_reason` sẽ tưởng model đã trả lời xong và
  trả cho người dùng một câu rỗng. Đây là lỗi thật hay gặp khi đổi từ OpenAI sang Ollama.

## Bẫy thường gặp

- Đưa `system` vào `messages` của Anthropic (API trả 400: role phải là `user` hoặc `assistant`).
- Để khối `text` rỗng trong content của assistant khi `content` là `None` (API từ chối khối text rỗng).
- Mỗi `tool_result` một message user riêng.
- `json.loads(arguments)` mà không kiểm kết quả là dict: `'["facility"]'` là JSON hợp lệ nhưng không gọi `**kwargs` được.
- Chỉ lấy khối text đầu tiên của Anthropic: response có thể có nhiều khối text xen với `tool_use`.
- Sửa thẳng `messages` đầu vào (ví dụ `pop` system) làm hỏng lịch sử hội thoại của người gọi.
