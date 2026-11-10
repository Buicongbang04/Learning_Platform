# Lời giải: đánh giá agent

## Cách làm

**`numbers_in`** là một regex hai nhánh, nhánh "nhóm 3 chữ số" thử trước: `\d{1,3}(?:[., ]\d{3})+(?!\d)` bắt `165.000`,
`165,000`, `1 000 000`; nhánh sau bắt số có tối đa một dấu thập phân (`5,31`, `2.84`). Lookahead `(?!\d)` làm `5.3150`
không bị đọc thành nhóm nghìn (sau `315` còn chữ số) nên rơi về nhánh thập phân. Đơn vị `triệu`, `nghìn`, `ngàn` bắt
bằng một nhóm tuỳ chọn phía sau. Quy ước này có chỗ mơ hồ không tránh được: `5.315` là 5 315 (giá tiền Việt) chứ không
phải 5,315; với tiền đô la thì sai. Chọn quy ước theo miền dữ liệu và **ghi ra**, thay vì để mỗi người chấm hiểu một kiểu.

**`check_answer`** so số với sai lệch tuyệt đối 0.01 (đủ cho đáp án làm tròn 2 chữ số như 5,31 USD) và chuỗi sau NFC,
không phân biệt hoa thường. Mọi phần tử phải đạt: "đơn của ai **và** tổng bao nhiêu" cần cả hai.

**`wilson_interval`** theo công thức trong notebook, kẹp vào `[0, 1]`. Wilson thay cho xấp xỉ chuẩn
$$\hat p \pm z\sqrt{\hat p(1-\hat p)/n}$$ vì xấp xỉ chuẩn cho khoảng độ rộng 0 khi $$k = 0$$ hoặc $$k = n$$ và vượt
khỏi `[0, 1]` với $$n$$ nhỏ; đúng những chỗ một bộ 24 task hay rơi vào. Độ rộng tỉ lệ với $$1/\sqrt{n}$$: muốn hẹp
một nửa cần gấp bốn số task.

**`classify_failure`** duyệt các bước theo thứ tự với danh sách số "đã thấy": tham số của mỗi action được kiểm **trước**
khi thêm observation của chính bước đó. Bản đầu tiên của lời giải này chỉ kiểm số trong câu trả lời và gắn nhãn
`hallucinated_number` cho 1 trong 7 task ReAct sai; đọc trace thì thấy phần lớn các task sai đều có giá tự nghĩ ra đi
vào `calculator` rồi đi ra như một observation hợp lệ. Kiểm cả tham số thì cả 7 task được gắn đúng nhãn. Bài học chung:
một bộ phân loại lỗi tự động phải được kiểm bằng cách đọc trace, giống judge ở module 13.

## Kết quả (notebook lời giải, PC của track, `qwen2.5:3b`, `temperature` 0, `seed` 0)

| Cách | Đúng | Khoảng tin cậy 95% | Bước TB | Lỗi tool | Không trả lời | Giây trung vị / task | Token prompt TB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ReAct văn bản | 17/24 | [0.51, 0.85] | 3.0 | 8 | 0 | 3.7 | 861 |
| Native | 10/24 | [0.24, 0.61] | 2.2 | 6 | 0 | 1.4 | 687 |
| ReAct JSON | 14/24 | [0.39, 0.76] | 4.5 | 26 | 5 | 11.5 | 1 041 |

So theo cặp: 7 task chỉ ReAct đúng, **không** task nào chỉ native đúng; giữa ReAct và ReAct JSON là 4 và 1. Ba lần chạy
lại ReAct và native với `temperature` 0.7 (mục 2 lý thuyết) cho số task chỉ native đúng là 0, 0, 2 và số task chỉ ReAct
đúng là 7, 9, 6: qua bốn lần chạy, chiều lệch luôn nghiêng hẳn về ReAct, còn con số chính xác dao động vài task. Phân loại lỗi:

| Nhãn | ReAct | Native | ReAct JSON |
| --- | --- | --- | --- |
| `hallucinated_number` | 7 | 4 | 5 |
| `no_answer` | 0 | 0 | 5 |
| `no_tool` | 0 | 2 | 0 |
| `tool_error` | 0 | 2 | 0 |
| `wrong_other` | 0 | 6 | 0 |

- **ReAct JSON chậm nhất**, khoảng 3 lần ReAct văn bản theo trung vị: nhiều bước hơn (4.5 so với 3.0), 26 lỗi tool (model
  viết khoá như `"book_id: "` có dấu hai chấm thừa trong tên khoá, schema chặn, model thử lại y hệt), 5 task hết 8 bước.
  Constrained decoding bảo đảm JSON hợp lệ, không bảo đảm tham số đúng. Câu trả lời còn lẫn tiếng Trung ở 5 task;
  `check_answer` vẫn chấm đúng 3 trong số đó vì con số hoặc tên riêng vẫn khớp.
- **Native** dừng sớm: 6 task `wrong_other` là các câu hỏi lại người dùng hoặc trả lời dở dang sau một lời gọi tool.
- **Cell mở rộng** (25 tool, 20 tool nhiễu): 15/24 đúng, 5 lần gọi tool nhiễu, token prompt lượt dài nhất trung bình
  2 077 (so với 861 với 5 tool). Chênh 17 xuống 15 nằm trong nhiễu; chi phí token gấp khoảng 2.4 lần thì không.
- Cả notebook chạy khoảng 10 phút trên PC của track (ReAct JSON chiếm gần một nửa).

## Bẫy thường gặp

- `float("165.000")` cho 165.0: đọc số tiền Việt bằng `float` là sai từ đầu.
- Khoảng tin cậy kiểu Wald (xấp xỉ chuẩn) cho `[1, 1]` khi 24/24 đúng.
- So hai tỉ lệ đúng mà không nhìn các task lệch nhau: 17 và 14 trông khác nhau, nhưng chỉ có 5 task lệch (4 và 1).
- Tin bộ phân loại lỗi tự động mà không đọc trace (phần `classify_failure` ở trên).
