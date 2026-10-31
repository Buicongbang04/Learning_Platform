# Hướng làm: context length thật của qwen2.5:3b

Bài không có code lời giải chạy được: lưới thí nghiệm và báo cáo là của bạn. Dưới đây là các quyết định cần cân nhắc,
kết quả của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Filler | bài Wikipedia tiếng Việt dài 400 tới 3 000 ký tự, bỏ bài có chữ "mã số", đọc `train-00002` theo lô 5 000 bài tới khi đủ 200 (ra 235 bài; cùng cách trên `train-00001` ra 380 vì lô cuối lấy được nhiều bài dài hơn) | đủ khác nhau để haystack không lặp; bài ngắn hơn phần lớn là trang sơ khai một hai câu; bỏ bài có thể chứa một "mã số" khác làm nhiễu |
| Đếm token | tokenizer `Qwen/Qwen2.5-0.5B-Instruct`, đếm **từng** đoạn | cùng tokenizer với 3B; đếm từng đoạn để `build_haystack` tuyến tính, không đếm lại cả văn bản mỗi lần thêm đoạn |
| Needle | "Mã số bí mật của dự án Sen Vàng là NNNN.", mã ngẫu nhiên 4 chữ số khác nhau mỗi ô (rng seed 0) | mỗi ô một đáp án, model không thể "nhớ" đáp án ô trước; tên dự án không có trong Wikipedia |
| Haystack | xoay điểm bắt đầu trong danh sách filler cho mỗi ô | mỗi ô một văn bản khác, tránh kết luận dựa trên một đoạn filler đặc biệt |
| Câu hỏi | ở cuối prompt, "Chỉ trả lời con số." | câu hỏi cuối là cách dùng thật (tài liệu rồi câu hỏi); và nó quyết định phần nào sống sót khi runtime cắt prompt |
| Chấm | `needle_found`: số nguyên vẹn, chấp nhận phân cách nghìn | "7.429" là đúng; "17429" hay "123456" là sai |
| Kiểm cắt | so `prompt_eval_count` với số token đếm được | đây là bằng chứng duy nhất của việc cắt; Ollama không báo lỗi |
| Server dùng chung | cache từng ô ra JSON, `keep_alive` 0 khi xong | `num_ctx` 16 384 giữ KV cache lớn; đổi `num_ctx` nạp lại model |

Lỗi hay gặp: dùng một mã dễ đoán (1234) cho mọi ô, nên không phân biệt được trả đúng thật với đoán bừa; đếm token bằng số ký tự chia 3.5 (sai tới 30% với văn bản nhiều số
và tên riêng); kết luận "lost in the middle" từ các ô mà prompt đã bị cắt; đặt câu hỏi ở đầu prompt rồi ngạc nhiên vì
model không trả lời được ở `num_ctx` mặc định.

## Kết quả tham chiếu

PC của track, Ollama 0.13.5, `qwen2.5:3b` Q4_K_M hết trên RTX 3060, `temperature` 0, `seed` 0, `num_predict` 16, ngày
2026-11-01. Lưới 40 ô chạy khoảng 1.5 phút.

| `num_ctx` | Độ dài filler (token) | depth 0 | 0.25 | 0.5 | 0.75 | 1 |
| --- | --- | --- | --- | --- | --- | --- |
| mặc định (4 096) | 1 000 | đúng | đúng | đúng | đúng | đúng |
| mặc định | 3 000 | đúng | đúng | đúng | đúng | đúng |
| mặc định | 6 000 | sai | sai | sai | đúng | đúng |
| mặc định | 12 000 | sai | sai | sai | sai | đúng |
| 16 384 | 1 000, 3 000, 6 000, 12 000 | đúng | đúng | đúng | đúng | đúng |
| 32 768 (mở rộng, PC) | 24 000 | đúng | đúng | đúng | đúng | đúng |

| Số token đếm được (prompt) | `prompt_eval_count` ở `num_ctx` mặc định | ở 16 384 |
| --- | --- | --- |
| khoảng 1 100 tới 1 600 | đếm được + 29 | đếm được + 29 |
| khoảng 3 100 tới 4 000 | đếm được + 29 | đếm được + 29 |
| khoảng 6 100 tới 6 800 | **4 096** | đếm được + 29 |
| khoảng 12 100 tới 12 900 | **4 096** | đếm được + 29 |

29 token chênh là chat template (system mặc định của Qwen cùng các thẻ `<|im_start|>`, `<|im_end|>`). Log server
(`journalctl -u ollama`) ghi cho mỗi prompt bị cắt một dòng `msg="truncating input prompt" limit=4096 prompt=... keep=4
new=4096`: giữ 4 token đầu và 4 092 token cuối. Con số `prompt=` trong log chỉ lớn hơn số token đếm được 8 thay vì 29,
nên khi cắt, Ollama còn bỏ khối system mặc định trước đó. Lưới chạy hai lần cho đúng cùng bảng và cùng câu trả lời
(filler, mã số và `seed` ghim).

Bảy ô sai, tất cả ở `num_ctx` mặc định. "Vị trí trong cửa sổ" là số token từ đầu phần được giữ tới needle (âm nghĩa là
needle đã bị cắt):

| Ô (độ dài, depth) | Vị trí needle / token prompt | Vị trí trong cửa sổ 4 096 | Trả lời | Mã đúng |
| --- | --- | --- | --- | --- |
| 6 000, 0 | 0 / 6 422 | âm | `8884` | 3496 |
| 6 000, 0.25 | 1 406 / 6 148 | âm | `72019` | 7037 |
| 6 000, 0.5 | 3 001 / 6 149 | khoảng 950 | `4102` | 4547 |
| 12 000, 0 | 0 / 12 454 | âm | `409` | 8619 |
| 12 000, 0.25 | 2 761 / 12 273 | âm | `456` | 1803 |
| 12 000, 0.5 | 5 479 / 12 574 | âm | `643` | 1198 |
| 12 000, 0.75 | 9 147 / 12 154 | khoảng 1 090 | `123456` | 1723 |

Các ô đúng ở `num_ctx` mặc định có needle ở khoảng 2 310 (6 000, depth 0.75) và khoảng 4 055 (depth 1) trong cửa sổ.

Đọc kết quả:

- **Gốc của mọi ô sai là runtime cắt prompt.** Ở `num_ctx` 16 384 cùng các độ dài đó đúng 20/20, nên model đọc được cả
  12 000 token khi được đọc hết. Năm ô sai có needle nằm ngoài phần được giữ: dữ kiện đơn giản là không còn.
- **Hai ô còn lại rất có thể là context shift.** Prompt sau khi cắt lấp đầy đúng 4 096 vị trí của cache. Token đầu tiên
  của câu trả lời được sinh khi cache vẫn nguyên; để sinh token thứ hai, runner phải dời context, bỏ khoảng
  $$(4096 - 4) / 2 \approx 2\,046$$ token ngay sau 4 token giữ lại. Needle ở vị trí khoảng 950 và 1 090 rơi đúng vào
  khúc bị bỏ, needle ở khoảng 2 310 thì không. Ba manh mối khớp với cơ chế này: chữ số đầu của cả hai câu trả lời đều
  đúng (`4`102 cho 4547, `1`23456 cho 1723: Qwen2.5 tách số thành từng chữ số, và chữ số đầu được sinh trước khi dời);
  gửi lại hai prompt đó với `num_predict` 1 thì nhận đúng `4` và `1`; gửi với `"shift": false` thì Ollama dừng sau
  **một** token với `done_reason` `"length"`, tức là cache đã đầy ngay sau prompt. Chưa xác nhận trực tiếp bằng log
  debug (`OLLAMA_DEBUG=1` cần khởi động lại service dùng chung của máy). Ô đối chứng 6 000, depth 0.75 (needle ở khoảng
  2 310 trong cửa sổ) chạy lại cùng hai cách cho kết quả cùng kiểu: `num_predict` 1 trả `5` (chữ số đầu của 5988),
  `"shift": false` cũng dừng sau một token với `done_reason` `"length"`. Prompt của nó cũng lấp đầy cache, nhưng khúc
  bị bỏ khi dời không chứa needle, nên ở lần chạy thường câu trả lời vẫn đúng. Hệ quả thực tế: prompt vừa khít `num_ctx` vẫn
  hỏng; quy tắc đúng là số token prompt cộng `num_predict` không vượt `num_ctx`.
- **Model trả lời sai bằng giọng tự tin**: không ô nào trả "không tìm thấy". `456` có trong filler (số gần câu hỏi);
  `8884`, `72019`, `4102`, `409`, `643` không có trong prompt; `123456` là bịa hẳn. Không HTTP lỗi, `done_reason` bình
  thường. Đây là kiểu lỗi nguy hiểm nhất cho hỏi đáp tài liệu.
- **Ở `num_ctx` đủ lớn không thấy "lost in the middle"**: 20/20 tới 12 000 token, và phần mở rộng trên PC (`num_ctx`
  32 768, khoảng 24 400 token, 11 tới 19 giây mỗi lần) đúng 5/5. Không có nghĩa model dùng tốt mọi thông tin ở giữa
  context dài: một needle, câu hỏi gần chép lại câu needle, là bài khớp chuỗi dễ nhất. RULER thêm nhiều needle, needle
  gây nhiễu, câu hỏi phải suy luận, và ở đó model nhỏ tụt nhanh hơn nhiều.
- **Cái giá của `num_ctx` lớn**: prompt 12 000 token mất khoảng 4 giây thay vì 1.5 giây (đọc hết thay vì 4 096 token),
  KV cache khoảng 0.56 GiB ở 16 384 token, và đổi `num_ctx` làm nạp lại model.

Khuyến nghị của bản tham chiếu: với `qwen2.5:3b` qua Ollama, đặt `num_ctx` sao cho số token prompt cộng `num_predict`
không vượt nó, **luôn** kiểm `prompt_eval_count` so với số token đếm được và báo lỗi khi bằng đúng `num_ctx` (hoặc gửi
`"shift": false` để Ollama dừng thay vì âm thầm bỏ context); với tài liệu dài hơn vài nghìn token và câu hỏi cần nhiều đoạn, chunk và retrieve (module 13) thay vì tin vào context dài của một model 3B.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Thiết lập | 15 | Lưới đủ 40 ô, mã khác nhau mỗi ô, filler không lặp, đếm token bằng tokenizer thật, cache, giải phóng model khi xong |
| Phát hiện cắt prompt | 25 | Có bảng `prompt_eval_count` so với số token đếm được; nhận ra mọi ô sai ở `num_ctx` mặc định là do cắt; tính vị trí needle trong cửa sổ được giữ cho từng ô sai; giải thích (hoặc ít nhất nêu) các ô needle còn trong cửa sổ mà vẫn sai, dùng manh mối chữ số đầu đúng hoặc thí nghiệm `num_predict` 1 / `"shift": false` |
| Diễn giải trung thực | 20 | Không kết luận "lost in the middle" từ ô bị cắt; nói rõ bài needle đơn là bài dễ, không chứng minh hiểu cả tài liệu |
| Khuyến nghị | 15 | Cấu hình cụ thể (`num_ctx`, kiểm `prompt_eval_count`, khi nào chuyển sang RAG), có cái giá (thời gian, bộ nhớ) |
| Báo cáo | 10 | Tóm tắt có số ở đầu, thiết lập tái lập được (phiên bản Ollama, phần cứng), giới hạn |

Đạt từ 70 điểm. Báo cáo kết luận model "chỉ dùng được 3 000 token" hay "kém ở giữa context" mà không xem
`prompt_eval_count` không quá 50 điểm.
