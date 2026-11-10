# Lời giải: RAG có trích dẫn và cổng từ chối

## Cách làm

**`build_messages`.** System prompt là khung ở mục 5 lý thuyết, chèn đúng hằng `REFUSAL` (không gõ lại câu, để code
so khớp được). Message user dựng từ các khối `f"[{i}] {law}, {p.title}\n{p.text}"` với `i` từ 1 và `law =
p.uid.rsplit("+", 1)[0]`, nối bằng dòng trống, rồi `Câu hỏi: ...` ở cuối. Số hiệu văn bản trong dòng đầu giúp model (và
người đọc) biết nguồn thuộc văn bản nào; model vẫn chỉ cần viết `[2]`, còn code tự map ngược về điều luật.

**`parse_citations`.** `re.finditer(r"\[(\d+)\]", answer)` theo thứ tự xuất hiện, giữ số trong `1..n`, bỏ số đã gặp.
Chỉ nhận đúng dạng `[i]` mà prompt yêu cầu: `[1][3]` đọc được, còn `[1, 3]` hay "nguồn số 1" thì không. Muốn nhận
thêm dạng khác thì phải ghi vào prompt và test cùng lúc, nếu không bộ đếm "có trích dẫn" sẽ thay đổi âm thầm.

**`answer`.** Thứ tự các bước là thiết kế:

1. `hits = retrieve(question)`; không có hit hoặc `max(score) < min_score` thì trả `RagAnswer(REFUSAL, [], True)`
   ngay. Lớp 1 này rẻ (không gọi LLM) và tài liệu trong prompt không thể lách nó.
2. Gọi LLM **một** lần với mọi hit. Cổng chỉ xét điểm cao nhất; lọc từng hit theo ngưỡng là quyết định của tầng
   retrieval (số nguồn `k`), không trộn vào đây.
3. `citations`: `passages[i - 1].uid` cho mỗi `i` hợp lệ, bỏ uid trùng (nguồn là khoản, hai khoản cùng điều có cùng
   uid). `refused` dò chuỗi "Không tìm thấy căn cứ": model có thể nói câu từ chối rồi viết thêm, nên không so bằng
   `==`.

## Kết quả thật

Laptop của track (RTX 3050 4GB, Ollama `qwen2.5:3b` và `bge-m3`, `temperature = 0`). Cả notebook chạy khoảng 3 phút.

**Thí nghiệm của mục 5 lý thuyết** (câu "Công an xã xử phạt lỗi không mang bằng lái xe có đúng không?", cả điều cắt ở
1 500 ký tự): cả hai trường hợp đều trả đúng câu từ chối (5.7 s với 3 nguồn, 0.5 s với 2 nguồn về đê), khớp lý thuyết.

**20 câu đầu tập ghim**, retrieve hai tầng: dense `bge-m3` lấy 5 điều trên toàn corpus, tách theo khoản, giữ 5 khoản
cosine cao nhất. So với bảng ở mục 5 lý thuyết (top-5 hybrid trên lát cắt, cả điều cắt ở 1 500 ký tự):

| | Lý thuyết: cả điều cắt 1 500 ký tự | Bài này: 5 khoản |
| --- | --- | --- |
| Độ trễ trung vị (sinh câu trả lời) | 2.2 s | 3.1 tới 3.6 s (hai lần chạy) |
| Điều đúng có trong 5 nguồn | 18 / 20 | 15 / 20 |
| Có ít nhất một trích dẫn `[i]` | 8 / 20 | 11 / 20 |
| Trích đúng điều đáp án | 6 (trong 18) | 10 (trong 15) |
| Từ chối | 7 (6 dù có điều đúng) | 5 (2 dù có điều đúng) |
| 5 câu ngoài phạm vi bị từ chối | 5 / 5 (đều do LLM) | 5 / 5 (4 do cổng, 1 do LLM) |

Điểm khoản cao nhất của 20 câu thật thấp nhất 0.624; của 5 câu ngoài phạm vi từ 0.388 tới 0.518.

## Đọc kết quả

- **Đổi đơn vị nguồn sửa phần lớn lỗi từ chối sai**: từ 6 xuống 2 câu từ chối dù có điều đúng, và số câu trích đúng
  điều đáp án tăng từ 6 lên 10 dù retrieval ở đây khó hơn (toàn corpus, dense một nhánh: 15 thay vì 18 câu có điều đúng
  trong nguồn). Khoản ngắn (vài trăm ký tự) nên phần trả lời không còn nằm sau chỗ cắt; đó đúng là chẩn đoán ở mục 5.
- **Model vẫn viết số ngoài khoảng**: với câu "đỗ xe ô tô ngược với chiều lưu thông", `qwen2.5:3b` viết "[1] và [7]"
  khi chỉ có 5 nguồn. `parse_citations` bỏ `[7]`, chỉ giữ `[1]`. Trong 40 câu ở phần lý thuyết model không làm vậy lần
  nào; ở đây 1/20. Đây là lý do code phải kiểm, không tin model.
- **Trích dẫn tự do vẫn còn**: nhiều câu trả lời đúng nội dung nhưng viết "Theo Điều 19 của Nghị quyết số
  05/2021/NĐ-CP" thay cho `[i]` (và gọi nhầm nghị định thành nghị quyết). Code không đếm những câu này là có trích dẫn;
  đó là lỗi định dạng của model nhỏ, sửa bằng ví dụ mẫu trong prompt hoặc structured output (JSON có trường
  `citations`), không phải bằng regex lỏng hơn.
- **Retrieval hỏng thì generation không cứu được**: 5 câu không có điều đúng trong nguồn. 3 câu model từ chối (đúng
  hành vi), 2 câu model vẫn trả lời từ điều khác: một câu dựa vào một điều của Nghị định 38/2021 cho hành vi "làm sai lệch
  biển báo" (nhãn là Nghị định 100/2019). Theo cây debug ở mục 6, các câu này sửa ở retrieval (hybrid, rerank, nhiều
  điều hơn trước khi chọn khoản), không phải ở prompt.
- **Cổng điểm**: ngưỡng 0.5 lấy từ phân phối cosine **mức điều** của phần lý thuyết vẫn tách được hai phân phối **mức
  khoản** ở đây (câu thật thấp nhất 0.624), nhưng câu "Giá vàng SJC hôm nay bao nhiêu?" đạt 0.518 và lọt qua; lớp 2 (chỉ
  thị trong prompt) bắt được nó. Nâng ngưỡng lên khoảng 0.55 sẽ chặn cả 5 mà vẫn cách câu thật thấp nhất 0.07, nhưng chọn
  ngưỡng từ 25 câu là quá ít: đo trên vài trăm câu, gồm cả câu "gần phạm vi", trước khi chốt.
- Câu trả lời của LLM có thể lệch đôi chút giữa các máy, phiên bản Ollama và bản lượng tử hoá; trên laptop của track, hai
  lần chạy cho đúng cùng câu trả lời và cùng số đếm; số liệu retrieval (15/20, điểm cosine) thì tái lập ở mọi máy.
