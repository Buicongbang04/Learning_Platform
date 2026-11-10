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

## Kết quả của bản tham chiếu

PC của track, 2026-11-01, `qwen2.5:3b`, `temperature` 0, `seed` 0, GPU dùng chung; ba kiến trúc chạy tổng cộng khoảng 16
phút. Log `.superpowers/scratch/logs/a01_{single,supervisor,swarm}.json`, `a01_run.log`, tổng hợp `a01_summary.log`.

| Kiến trúc | Đúng / 52 | Wilson 95% | Nhà sách / 24 | Pháp luật / 20 | Câu ghép / 8 | Lượt LLM TB | Token prompt TB | Giây trung vị |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Một agent (6 tool) | 27 | [0.39, 0.65] | 9 | 15 | 3 | 2.04 | 1 903 | 6.1 |
| Supervisor (agent làm tool) | 26 | [0.37, 0.63] | 8 | 15 | 3 | 4.75 | 2 588 | 6.9 |
| Swarm (handoff) | 8 | [0.08, 0.28] | 8 | 0 | 0 | 1.77 | 1 278 | 2.4 |

So theo cặp: một agent và supervisor lệch nhau 7 task (4 chỉ một agent đúng, 3 chỉ supervisor đúng); swarm thua một agent ở
19 task và không thắng task nào.

## Đọc kết quả

- **Supervisor không hơn một agent, và tốn gấp 2.3 lần lượt LLM** (token prompt nhiều hơn 36%). Với chỉ 6 tool và hai miền
  tách bạch, một agent đã chọn đúng tool; tầng điều phối chỉ thêm một chỗ hỏng: ở các task nhà sách sai, agent con trả lời
  "không tìm thấy" hoặc điều phối viên tóm câu trả lời của agent con sai đi (một câu trả lời bắt đầu "Ccâu hỏi của bạn vượt
  quá khả năng..."). Ở phần pháp luật hai cách bằng nhau (15/20).
- **Swarm sập ở mọi câu có phần pháp luật** vì handoff gần như không xảy ra. Phân loại cả 28 task có phần pháp luật
  (agent nhà sách là nơi mọi lượt bắt đầu; log `a01_summary.log`): 2 lần gọi handoff thật (L15, M1; quyền chuyển sang
  agent pháp luật nhưng cả hai task vẫn sai); 11 lần **viết** lời gọi ra thành chữ (`" transfer_to_legal()"`,
  `".transfer_to_legal{}"`) thay vì phát một tool call; 5 lần trả về chuỗi rỗng; 2 lần nói "tôi sẽ chuyển" rồi dừng; 8 lần
  tự trả lời mà không chuyển (2 câu luật trả lời "không tìm thấy trong dữ liệu", 6 câu ghép trả lời phần sách rồi bỏ qua
  hoặc tự nói qua phần luật mà không tra cứu). Giả thuyết, **chưa đo**: tool không tham số là trường hợp model 3B này phát tool call kém nhất; muốn
  kiểm thì thêm một tham số bắt buộc cho tool handoff và chạy lại cùng bảng. Cơ chế handoff tự nó đúng (test của
  `make_handoff_tool` xanh, 2 lần chuyển thật đến đúng agent); thứ hỏng là model không dùng được nó.
- **Câu ghép là chỗ khó nhất cho cả ba**: 3/8 là tốt nhất; một agent làm đúng phần sách ở 6 câu nhưng chỉ tra trúng phần
  luật ở 4.
- **Kết luận cho capstone với model nhỏ**: một agent có ít tool, mô tả tool rõ, là lựa chọn mặc định. Nếu cần tách
  (nhiều miền, nhiều tool), dùng router bằng structured output hẹp hoặc code (như bước `plan` của bài Intermediate 03) thay
  cho handoff do model tự quyết; nếu dùng handoff, thử cho tool handoff một tham số bắt buộc (ví dụ `reason: str`) và đo
  lại xem giả thuyết ở trên có đúng không. Chạy lại cùng bảng với `qwen2.5:7b` trên PC để biết phần nào là do
  model.

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
