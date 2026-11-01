# Lời giải: quản lý context

## `truncate_middle`

Tìm kiếm nhị phân trên `k` (số ký tự giữ ở mỗi đầu) trong `0..len(text)//2`: độ dài kết quả tăng theo `k` (thêm 2 ký
tự, dấu cắt ngắn đi tối đa một chữ số), nên điều kiện "vừa ngân sách" đơn điệu và `k` lớn nhất tìm được trong
$$O(\log n)$$ lần đếm. Suy `k` bằng phép chia (`max_tokens * 3.5 / 2`) chỉ đúng với một bộ đếm cụ thể; tìm kiếm thì đúng
với mọi bộ đếm, kể cả tokenizer thật.

Giữ **đầu và đuôi** vì observation dài thường có thông tin ở hai đầu: tiêu đề và bản ghi đầu ở đầu, tổng kết hay lỗi
cuối cùng ở cuối (log pytest: dòng `N passed, M failed` nằm cuối). Dấu cắt ghi số ký tự bị bỏ để model biết có thứ đã
mất và có thể gọi tool lấy phần đó (phân trang) thay vì đoán.

## `compact_history`

Observation cũ đã được model "tiêu hoá" thành Thought và Action sau đó; giữ nguyên văn chỉ tốn token. Thay chúng bằng
một dòng ngắn có độ dài gốc là kỹ thuật Anthropic gọi là *tool result clearing* (mục 3 lý thuyết). Giữ `keep_last`
observation cuối vì model thường cần kết quả vừa có. Observation ngắn không đáng rút gọn: rút gọn mà dài hơn bản gốc
là phản tác dụng.

## `fit_messages`

Thử đoạn đuôi dài nhất trước rồi ngắn dần, dừng ở lựa chọn đầu tiên vừa: $$O(n^2)$$ lần đếm trong trường hợp xấu
nhất, đủ nhanh với vài chục message; với hàng nghìn message thì cộng dồn từ cuối lên cho $$O(n)$$. Hai điều quan trọng
hơn thuật toán:

- **Ghim system và task.** Ollama khi prompt vượt `num_ctx` bỏ message cũ nhất nhưng giữ system và message cuối
  (mục 3 lý thuyết đo được): task của người dùng là message cũ nhất sau system nên bị bỏ **đầu tiên**, agent còn lại
  một chuỗi observation mà không biết để làm gì.
- **Ghi chú đã lược bỏ** cũng là token, phải tính vào ngân sách, và nói cho model biết lịch sử không đầy đủ.

Khi `keep_last` message cuối cũng không vừa, ném lỗi thay vì cắt tiếp: lúc đó vấn đề là một observation quá to, cách
sửa là `truncate_middle` observation đó trước, không phải bỏ thêm lịch sử.

## Bẫy thường gặp

- Cắt observation theo **ký tự** khi ngân sách tính theo **token**: tiếng Việt khoảng 3.5 ký tự một token với Qwen2.5,
  tiếng Anh khoảng 4, mã nguồn và JSON khác nữa.
- Quên `MSG_OVERHEAD`: mỗi message còn tốn thẻ vai của chat template (module 11 mục 2).
- Bỏ message ở giữa một cặp assistant/observation: lịch sử còn observation mà mất action sinh ra nó. Bản đơn giản ở đây
  giữ một đoạn đuôi liên tục nên ít gặp, nhưng với API native (message `tool` gắn `tool_call_id`) bỏ lệch cặp là lỗi
  HTTP 400.
