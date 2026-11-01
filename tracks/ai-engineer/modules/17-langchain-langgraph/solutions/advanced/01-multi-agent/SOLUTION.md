# Lời giải: một agent, supervisor, swarm

Bài này không có một đáp án duy nhất. Phần dưới là hướng làm, các quyết định cần cân nhắc, kết quả của bản tham chiếu
(chạy ngoài repo), và rubric chấm.

## Hướng làm

**`make_handoff_tool`.** Một tool không có tham số cho model, nhận `state: Annotated[dict, InjectedState]` và
`tool_call_id: Annotated[str, InjectedToolCallId]`, trả

```text
Command(goto=agent_name, graph=Command.PARENT,
        update={"messages": [*state["messages"], ToolMessage("Đã chuyển cho <agent>.", name=..., tool_call_id=...)],
                "active_agent": agent_name})
```

`InjectedState` và `InjectedToolCallId` làm hai tham số đó biến khỏi schema mà model thấy. Phải gửi **toàn bộ** message
của agent hiện tại lên đồ thị cha: subgraph có state riêng trong lúc chạy, và nếu chỉ gửi `ToolMessage` thì đồ thị cha
thiếu `AIMessage` chứa lời gọi handoff (ToolMessage mồ côi). `add_messages` ở đồ thị cha bỏ trùng theo `id`, nên gửi lại
các message cũ không nhân đôi chúng.

**Ba kiến trúc** (bản tham chiếu, `qwen2.5:3b`, `temperature` 0, `seed` 0):

- **Một agent**: `build_agent` của bài Intermediate 01 với 6 tool (5 tool nhà sách + `search_law`), tối đa 8 lượt.
- **Supervisor (agent làm tool)**: điều phối viên là `build_agent` với hai tool `ask_bookstore(request)`,
  `ask_legal(request)`, tối đa 5 lượt; mỗi tool chạy một agent con (`build_agent` nhà sách tối đa 6 lượt, pháp luật tối
  đa 4 lượt) và trả câu trả lời cuối của nó. Tool nhận `config: RunnableConfig` để truyền `callbacks` xuống agent con,
  nếu không lượt LLM của agent con không được đếm.
- **Swarm**: hai subgraph (model + `ToolNode`), mỗi agent có tool của mình cộng tool handoff sang agent kia, giới hạn số
  lượt mỗi agent; đồ thị cha có `active_agent`, cạnh từ `START` đi tới agent đang giữ quyền (mặc định nhà sách),
  `destinations` khi `add_node`.

`search_law(query)` trả 3 điều (mã, tiêu đề, 600 ký tự đầu) và ghi lại uid đã trả; task pháp luật đúng khi có câu trả lời
và điều đúng nằm trong các uid đó.

**Quyết định cần cân nhắc.**

- **Agent con thấy gì.** Agent làm tool chỉ thấy yêu cầu được giao (context gọn, nhưng mất chi tiết nếu điều phối viên
  tóm sai); swarm cho agent nhận việc thấy cả lịch sử (đủ ngữ cảnh, nhưng prompt dài hơn).
- **Ngân sách cho từng agent và cho cả hệ.** Một supervisor 5 lượt gọi agent con 6 lượt có thể thành 30+ lượt LLM.
- **Ai trả lời cuối cùng.** Supervisor tổng hợp (thêm một lượt, có thể làm méo số liệu của agent con) hay trả nguyên văn
  câu trả lời của agent con.

PLACEHOLDER_A01_RESULTS

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt khi |
| --- | --- | --- |
| `make_handoff_tool` | 10 | Test xanh |
| Ba kiến trúc chạy đúng | 20 | Cùng model, cùng tool, có ngân sách bước cho từng agent; swarm chuyển quyền bằng handoff thật (không phải router viết sẵn) |
| Bộ task và bộ chấm | 15 | Đúng 52 task đã ghim, chấm không dùng LLM, kết quả lưu ra tệp |
| Đo chi phí đầy đủ | 15 | Lượt LLM và token của agent con tính vào task; giây mỗi task |
| Bảng có khoảng tin cậy, so theo cặp | 15 | Wilson 95%, theo nhóm, số task lệch nhau theo cặp |
| Phân tích lỗi từ trace | 15 | Ít nhất 5 trace, có phân loại và đếm (giao sai, không chuyển giao, mất thông tin, tự trả lời thay agent con...) |
| Kết luận | 10 | Gắn với số; nói rõ khi nào multi-agent đáng cho capstone |

Trừ điểm nặng: báo token mà không đếm lời gọi của agent con; so các kiến trúc trên các bộ task khác nhau.
