# Hướng làm: dựng lại RAG bằng LangChain và so với SDK trực tiếp

Bài không có code lời giải: `build_chain` có nhiều cách ghép đúng, và `COMPARE.md` là đánh giá của bạn. Dưới đây là các
quyết định cần cân nhắc, kết quả của một bản tham chiếu để bạn so, và rubric chấm.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Chọn framework | LangChain (`langchain-core` + `langchain-ollama`) | LCEL ghép từng bước rõ, có `FakeListChatModel` để test, module 17 dạy tiếp LangGraph; LlamaIndex mạnh về loader và index, phần pipeline này lại tự viết |
| Prompt | dựng bằng `build_messages` của bản SDK, đổi thành list `(role, content)` | cùng prompt từng ký tự thì so được; `ChatPromptTemplate` dễ làm lệch khoảng trắng và dấu `{}` trong văn bản luật |
| Cổng từ chối | `RunnableBranch((passes_gate, generate), refuse)` đặt **trước** bước dựng prompt | nhánh từ chối không chạm model; cổng sau model thì vẫn tốn một lượt gọi |
| Dữ liệu giữa các bước | dict `{"question", "docs"}`, `RunnablePassthrough.assign(text=...)` thêm câu trả lời | bước cuối cần cả `docs` (map `[i]` về uid) lẫn `text` |
| Nguồn | `Document(page_content=khoản, metadata={uid, title, score})` | đúng kiểu retriever của LangChain trả; điểm nằm trong metadata để cổng đọc được |
| Retriever thật | `BaseRetriever` con, embed bằng `OllamaEmbeddings` trên cùng ma trận cache | không dựng lại vector store: so pipeline, không so thư viện vector |

Những lỗi hay gặp:

- Gọi `answer(...)` của bản SDK trong một `RunnableLambda`: test vẫn có thể pass nhưng không còn gì để so; README cấm.
- `ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ...])`: văn bản có `{` `}` bị hiểu là biến, lỗi
  `KeyError` lúc chạy với điều luật có dấu ngoặc nhọn; truyền message đã dựng sẵn thì không gặp.
- Gán `"docs": retriever` rồi lại gọi retriever lần nữa trong cổng: retriever chạy hai lần (test đếm).
- Dùng `RunnableBranch` với điều kiện `lambda x: max(...) >= min_score` mà quên trường hợp `docs` rỗng: `max()` của
  chuỗi rỗng ném `ValueError`.
- `FakeListChatModel` trả theo vòng: chain gọi model hai lần (một lần thừa) vẫn ra kết quả đúng, chỉ callback
  `on_chat_model_start` mới bắt được; test dùng callback vì vậy.

## Kết quả tham chiếu

Laptop của track (RTX 3050 4GB, Ollama `qwen2.5:3b` + `bge-m3`, `temperature = 0`), `langchain-core 1.7.3`,
`langchain-ollama 1.1.0`. 50 câu đầu tập ghim, retrieve hai tầng (5 điều dense, giữ 5 khoản), cùng nguồn cho hai bản.

Lần chạy tham chiếu diễn ra khi GPU **bị chương trình khác chiếm một phần** (Ollama chia `qwen2.5:3b` khoảng 25% CPU,
75% GPU, hàng đợi có cả yêu cầu của tiến trình khác), nên độ trễ tuyệt đối cao bất thường; so sánh tương đối vẫn dùng
được vì hai bản xen kẽ nhau.

| | SDK (`llmkit`) | LangChain (`ChatOllama`) |
| --- | --- | --- |
| Độ trễ trung vị phần sinh (GPU bị chia) | 22.3 s | 25.5 s |
| Có trích dẫn `[i]` | 25 / 50 | 26 / 50 |
| Trích đúng điều đáp án | 22 | 24 |
| Từ chối | 11 | 13 |
| Retriever LangChain trả cùng nguồn với bản SDK | | 10 / 10 |

Điều đúng có trong 5 khoản nguồn ở 41/50 câu. Chỉ **22/50** câu trả lời giống hệt từng ký tự giữa hai bản, dù prompt,
model, `temperature = 0` và tham số gửi đi như nhau (`ChatOllama` gửi `options: {temperature: 0}`, chỉ khác là bật
streaming). Phần lớn câu khác nhau chung phần đầu rồi rẽ ở giữa. Kiểm thêm: gọi cùng một prompt hai lần liền nhau cho
10/10 câu giống hệt, nhưng so với câu trả lời sinh vài giờ trước (khi model được chia CPU/GPU kiểu khác) chỉ 2/10 giống.
Kết luận: lệch đến từ trạng thái nạp model của Ollama (chia GPU/CPU, batch), không phải từ framework; chênh lệch 1 tới
2 câu ở các dòng chất lượng là nhiễu. Đây là lý do notebook có cell gọi lại bản SDK.

Số dòng code (bỏ dòng trống, comment, docstring):

| Phần | SDK | LangChain |
| --- | --- | --- |
| Pipeline (cổng, gọi model, map trích dẫn) | `answer`: 13 dòng | `build_chain` + `to_documents`: 18 dòng |
| Dùng chung | `build_messages` + `parse_citations`: 15 dòng | như bên SDK |
| Gói phụ thuộc thêm vào | 0 | 11 gói (`langchain-core`, `langchain-ollama`, `langsmith`, `ollama`, `tenacity`, `zstandard`...) |
| Chi phí riêng mỗi lần gọi (LLM giả) | khoảng 0.015 ms | khoảng 3 tới 6 ms |

Đọc kết quả, đây là phần quan trọng của `COMPARE.md`:

- **Chi phí của framework không đáng kể so với model**: 3 tới 6 ms so với vài giây sinh câu trả lời, nhỏ hơn hàng trăm
  lần. Chênh lệch 3 giây ở độ trễ trung vị trong bảng là dao động của Ollama khi GPU bị chia, không phải chi phí
  LangChain; "LangChain chậm" không phải lý do để bỏ nó ở pipeline này.
- **Số dòng gần bằng nhau**, vì phần khó (prompt, đọc trích dẫn) là của bạn ở cả hai bản. LCEL ngắn hơn khi pipeline
  là một chuỗi thẳng, dài hơn khi có rẽ nhánh (cổng) và cần mang nhiều trường qua các bước.
- **Cái giá thật là gián tiếp**: 11 gói phụ thuộc, kiểu dữ liệu riêng (`Document`, `BaseMessage`), lỗi xảy ra sâu
  trong `RunnableSequence` với traceback dài, API đổi giữa các phiên bản lớn. Cái được cũng gián tiếp: callback,
  `set_debug`, streaming, tracing LangSmith, và đổi model hay vector store bằng một dòng.
- Khuyến nghị hợp lý cho **pipeline một bước này**: giữ SDK trực tiếp (ít phụ thuộc, dễ debug), cân nhắc framework khi
  thêm tool, agent nhiều bước, streaming ra UI, hoặc cần tracing chuẩn (module 16, 17, 20).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Chain đúng và thành ngữ | 20 | Dựng bằng LCEL, cổng trước model, không gọi lại `answer`, prompt bằng hệt bản SDK; retriever LangChain trả cùng nguồn với bản SDK |
| So sánh công bằng | 20 | Cùng nguồn, cùng prompt, cùng model và `temperature`, xen kẽ thứ tự gọi; nói rõ điều đó trong `COMPARE.md` |
| Số liệu | 20 | Bảng có số dòng (tách phần riêng và phần chung), độ trễ trung vị, chi phí framework đo bằng LLM giả, số câu trả lời giống hệt, chất lượng (trích dẫn, trích đúng, từ chối), số gói phụ thuộc |
| Diễn giải | 15 | Tách chi phí framework khỏi thời gian model; nhận ra chênh lệch nào là nhiễu; giải thích câu trả lời khác nhau nếu có |
| Khuyến nghị | 10 | Có điều kiện (khi nào đổi lựa chọn), kể một lỗi thật gặp khi viết chain và cách lần ra |

Đạt từ 70 điểm. `COMPARE.md` kết luận "LangChain chậm hơn" hay "nhanh hơn" chỉ từ độ trễ end-to-end mà không tách thời
gian model, hoặc so hai bản với nguồn hay prompt khác nhau, không quá 50 điểm.
