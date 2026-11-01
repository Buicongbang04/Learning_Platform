# Lời giải: trích đáp số và reward kiểm được

## Cách làm

**Một dạng chuẩn cho mỗi giá trị.** `normalize_number` dọn chuỗi (bỏ `$`, `\$`, `%`, đổi `−` thành `-`, bỏ phẩy hàng
nghìn, bỏ dấu chấm cuối) rồi chỉ nhận chuỗi khớp **toàn bộ** mẫu `[+-]?\d+(\.\d+)?(/\d+)?`. Phần còn lại giao cho
`Fraction`: `Fraction("2.50")`, `Fraction("5/2")`, `Fraction("10/4")` đều là `5/2`, nên `str()` cho cùng một chuỗi và
so bằng `==` là so **giá trị chính xác**, không qua `float`. Hai lợi ích: `0.1 + 0.2` không thành vấn đề, và đáp số dùng
được làm khoá `dict` cho bỏ phiếu ở bài 02.

Phẩy hàng nghìn bỏ bằng `(?<=\d),(?=\d{3}(?!\d))`: chỉ phẩy có chữ số trước và **đúng ba** chữ số sau. `1,2` (danh sách,
hoặc phẩy thập phân kiểu châu Âu) và `1,0000` giữ nguyên phẩy nên bị từ chối thay vì âm thầm thành 12 hay 10000.

**Trích theo thứ tự ưu tiên.** Mỗi bước là "tìm đoạn, lấy một số trong đoạn": thẻ `<answer>` cuối, `\boxed{}` cuối
(số cuối trong đó), `####` cuối, cụm `answer is`/`answer:` cuối (số đầu sau đó), cuối cùng là số cuối của cả câu trả lời.
Một bước chỉ "thắng" khi đoạn của nó có số; `<answer>forty-two</answer>` rơi xuống các bước sau. Hàm phụ `_numbers`
dùng regex số trong văn bản tự do với lookbehind `(?<![\w.])`: dấu `-` sau chữ số là dấu trừ của một khoảng (`3-4
hours`), không phải số âm.

**Hai reward, hai mức nghiêm.** `extract_answer` cố đọc được càng nhiều càng tốt, vì nó dùng để **đo**. Reward thì dùng
để **dạy**, nên phải chặt: `correctness_reward` chỉ cho điểm khi nội dung thẻ `<answer>` cuối là **đúng một số**.
Nếu dùng cách dễ dãi "đáp án nằm trong các số của thẻ", model sẽ học viết `<answer>17 or 18</answer>` (liệt kê nhiều
đáp án) và reward tăng mà khả năng giải toán không đổi: reward hacking ở dạng đơn giản nhất. `format_reward` dùng
`re.fullmatch` cho cả chuỗi với tempered token `(?:(?!</?think>|</?answer>).)*` để chặn chữ thừa, thẻ lặp, thẻ lồng.

## Vì sao từng chi tiết quan trọng (số đo trên GSM8K)

- 93 trong 8 792 đáp án gold (79 train, 14 test) có phẩy hàng nghìn (`1,600`); 5 đáp án âm. So chuỗi thô với câu trả
  lời "1600" thì sai đúng những câu này.
- Bộ trích này đọc đúng đáp số từ lời giải mẫu của cả 1 319 câu test (test cuối): một kiểm tra rẻ rằng nó không làm mất
  điểm của câu trả lời đúng định dạng.
- Mục 1 lý thuyết có bảng đo trên Qwen2.5-0.5B: đổi từ "số cuối cùng" sang bộ trích có ưu tiên, và từ trích dễ dãi sang
  bắt đúng khung, thay đổi độ chính xác báo cáo bao nhiêu. Báo cáo accuracy mà không nói bộ trích nào là báo cáo thiếu.

## Bẫy thường gặp

- `float(a) == float(b)`: `0.1 + 0.2 != 0.3`; và `"18.0"` với `"18"` khác nhau nếu so chuỗi thô.
- Bỏ **mọi** dấu phẩy: `1,2` thành 12.
- Lấy số **đầu tiên** của câu trả lời: model hay nhắc lại dữ kiện đề bài trước khi giải.
- Lấy số đầu tiên trong thẻ `<answer>9 * 2 = 18</answer>` thay vì số cuối.
- Regex số không có lookbehind: `pages 3-4` ra -4.
- Reward chấm bằng chính bộ trích dễ dãi dùng để đo: model học khai thác chỗ dễ dãi đó (mục 4 lý thuyết).
