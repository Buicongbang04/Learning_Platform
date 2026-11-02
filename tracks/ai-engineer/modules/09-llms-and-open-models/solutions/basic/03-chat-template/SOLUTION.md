# Lời giải: chat template viết tay

## Cách làm

**`render_qwen`** tách message đầu nếu là system (in nó, không thì in system mặc định), rồi duyệt phần còn lại.
Message thường in thành `<|im_start|>{role}\n{content}<|im_end|>\n`. Message `tool` nhìn hai bên: mở
`<|im_start|>user` nếu message trước không phải tool, thêm `\n<tool_response>\n...\n</tool_response>`, đóng
`<|im_end|>\n` nếu message sau không phải tool. Cuối cùng thêm `<|im_start|>assistant\n` nếu cần generation prompt.

**`render_llama3`** thêm `<|begin_of_text|>` khi có message, mỗi message thành
`<|start_header_id|>{role}<|end_header_id|>\n\n{content.strip()}<|eot_id|>`.

**`parse_chatml`** là một regex `re.S` không tham. Khối generation prompt cuối chưa có `<|im_end|>` nên tự rơi ra.

**`fit_history`** tách system (nếu có) ra trước, trừ chi phí của nó khỏi ngân sách, đi ngược từ message mới nhất
và dừng ở message đầu tiên không vừa, đảo lại, bỏ message không phải user ở đầu đoạn.

## Vì sao quan trọng

- **Sai template là lỗi im lặng.** Model instruct vẫn sinh chữ khi nhận prompt sai định dạng, chỉ là kém hơn: bỏ
  qua system prompt, không dừng (thiếu `<|im_end|>` mà nó đã học để kết thúc lượt), hoặc tự viết tiếp lượt của
  user. Không có exception nào. Luôn dùng `tokenizer.apply_chat_template` (HF) hoặc để Ollama áp `TEMPLATE` trong
  Modelfile; tự viết như bài này chỉ để hiểu và để kiểm khi debug.
- **System mặc định của Qwen** chiếm 21 token mỗi request (đếm bằng tokenizer Qwen2.5) và đổi hành vi model
  ("You are Qwen..." làm model tự giới thiệu là Qwen). Muốn kiểm soát thì luôn gửi system của bạn.
- **Llama 3 strip nội dung, Qwen thì không**: cùng một hội thoại, đổi model là đổi chuỗi đầu vào theo những cách nhỏ
  như vậy. Đây là một lý do benchmark nhiều model qua cùng một API (Ollama, OpenAI-compatible) dễ hơn tự dựng prompt.
- **Tool result đóng vai user** trong Qwen2.5: model thấy kết quả tool như lời người dùng gửi vào. Đó là cửa cho
  prompt injection gián tiếp (module 19): nội dung trang web hay tài liệu mà tool trả về có cùng "quyền" với câu
  hỏi của người dùng.
- **Cắt lịch sử là quản lý context**: trừ system, chỉ giữ đoạn liên tục mới nhất, bắt đầu bằng câu hỏi của user.
  Thực tế còn có tóm tắt các lượt cũ thành một message system, hoặc giữ thêm vài lượt đầu; nhưng luôn có một
  ngân sách cứng là context của model cộng phần dành cho câu trả lời.
