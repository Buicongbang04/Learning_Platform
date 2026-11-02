---
title: Checkpoint và time travel - thread, cửa sổ message, SQLite, rẽ nhánh và xoá thread
level: basic
services: []
files:
  - path: starter/memory.py
    note: 6 TODO
  - path: tests/test_memory.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/17-langchain-langgraph/exercises/basic/03-checkpoint-time-travel -q
---

## Mục tiêu

Cho một đồ thị hội thoại "trí nhớ ngắn hạn" bằng checkpointer của LangGraph: mỗi người dùng một `thread_id`, state
sống qua lần khởi động lại nhờ SQLite, model chỉ thấy một cửa sổ message dù state giữ cả lịch sử, đọc dòng thời gian
các checkpoint, quay lại một điểm cũ để rẽ nhánh mà không mất nhánh cũ, và xoá sạch một thread khi người dùng yêu cầu.
Đây là phần "nhớ" mà module 16 tự viết bằng list message; ở đây framework lưu nó cho bạn, và bạn cần biết nó lưu gì.

## Đề bài

**Phần cứng:** CPU · ~50 phút

Trong `starter/memory.py` (`SYSTEM` đã có), viết 6 hàm theo docstring: `build_chat`, `open_saver`, `turn`, `timeline`,
`fork`, `forget`. Mục 3 lý thuyết có sơ đồ checkpoint của hai lượt hội thoại (mỗi lượt sinh 3 checkpoint: `input`, trước
node, sau node) và giải thích `parent_config`.

Tự kiểm sau khi test xanh: mở tệp SQLite bằng `sqlite3` và xem bảng `checkpoints`, `writes` có gì sau ba lượt; dữ liệu
người dùng nằm dạng nào trên đĩa?

## Tiêu chí đạt

- Mỗi thread có lịch sử riêng; lượt sau thấy lượt trước; system prompt luôn ở đầu.
- Cửa sổ `max_messages` cắt cái model thấy, bắt đầu bằng message người dùng; state vẫn đủ.
- Đóng kết nối SQLite rồi mở lại: hội thoại đi tiếp; saver dùng được từ thread khác.
- `timeline` của hai lượt có đúng 6 checkpoint với số bước, số message, `next` đúng; sau khi rẽ nhánh, `timeline` chỉ đi
  theo nhánh mới, chung gốc với nhánh cũ tới điểm rẽ, và nhánh cũ vẫn đọc lại được bằng `checkpoint_id`.
- `forget` xoá một thread, không đụng thread khác.

## Gợi ý

### Gợi ý 1

`trim_messages` của `langchain_core.messages` có `strategy`, `max_tokens`, `token_counter` (truyền `len` để đếm theo
số message) và `start_on`. Config của một lần chạy là `{"configurable": {"thread_id": ...}}`; thêm `checkpoint_id` vào
đó để đọc hoặc chạy tiếp từ một checkpoint cụ thể. `sqlite3.connect` mặc định chỉ cho thread đã mở nó dùng kết nối.

### Gợi ý 2

`app.get_state(config)` trả một `StateSnapshot` có `config`, `parent_config`, `metadata`, `values`, `next`.
`get_state_history` liệt kê **mọi** checkpoint của thread, kể cả các nhánh đã bỏ; để lấy riêng nhánh hiện tại, đi
ngược theo `parent_config` từ checkpoint mới nhất. Checkpointer có `delete_thread`.
