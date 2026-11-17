# Lời giải: chấm quillo trên nhãn CUAD

## Hướng làm

1. `is_refusal`: chuẩn hoá đúng như quy tắc 2 (chữ thường, `’` → `'`, bỏ khoảng trắng), so khớp nguyên câu với tập
   `no/none/n/a` sau khi bỏ dấu câu cuối, rồi tìm cụm trong danh sách. Giữ hai nhánh tách nhau: "No cap applies" không
   phải từ chối dù bắt đầu bằng "No".
2. `correct(citation, item)`: so `contract` trước, rồi độ chồng `min(end) − max(start)` với từng khoảng gold, ngưỡng
   `min(độ dài gold, 50)`. Ngưỡng tương đối cho nhãn ngắn (ngày ký 15 ký tự phải nằm trọn trong đoạn) và tuyệt đối cho
   nhãn dài (điều khoản 700 ký tự chỉ cần đoạn trích chạm vào 50 ký tự của nó, vì quillo cắt đoạn ~1000 ký tự chồng 150).
3. Một vòng qua các câu: bỏ qua câu từ chối khi đếm trích dẫn, đếm trích dẫn đúng/tổng, đánh dấu câu tìm ra. Tỉ lệ từ
   chối tính riêng trên hai nhóm câu. Hàm `ratio` trả `None` khi mẫu số 0 để không chia cho 0 và không giả vờ có số liệu.

Mã: `eval_metrics.py` cạnh tệp này.

## Đọc kết quả trên fixture

| Chỉ số | Giá trị | Đọc thế nào |
| --- | --- | --- |
| `citation_precision` | 0,18 | Thấp chủ yếu vì quillo 1.0.0 trả **mọi** đoạn đã đưa vào prompt khi model không tự trích `[n]` (README sản phẩm, mục API). Đó là đặc điểm của sản phẩm, không phải của model: báo cho khách con số này kèm lý do, và đưa cho đội sản phẩm như một đề xuất |
| `clause_recall` | 0,62 | 13/21 câu có nhãn có ít nhất một trích dẫn chạm điều khoản đúng. Cả 8 câu trượt đều do truy hồi (top 3) không đưa đoạn chứa điều khoản vào prompt; ở một câu (trần trách nhiệm của Centrack) model còn trả "No". Ngược lại, `ability-agreement-date` được tính là tìm ra dù câu trả lời chỉ là `[1]`: trích dẫn đúng chỗ nhưng người dùng không nhận được câu trả lời nào, nên recall theo trích dẫn đánh giá cao hơn trải nghiệm thật |
| `correct_refusal_rate` | 0,17 | 2/12 câu không nhãn được trả "No"; 10 câu còn lại model 0.5B bịa hoặc dán nguyên đoạn văn. Đây là rủi ro lớn nhất cần nói với công ty luật |
| `false_refusal_rate` | 0,05 | 1/21: hỏi trần trách nhiệm ở hợp đồng Centrack, model trả "No" dù hợp đồng có điều khoản |

Ba điều rút ra khi trình bày với khách: (1) 33 câu là mẫu nhỏ, một câu đổi chỉ số 3–8 điểm phần trăm, nên nói khoảng tin cậy hoặc
ít nhất số câu, đừng nói "62%" trơn; (2) chỉ số trích dẫn và chỉ số "câu trả lời đúng" là hai thứ khác nhau: câu
`gulf-agreement-date` trả đúng "14th day of December, 1997" nhưng không đoạn trích nào chứa ngày đó, tức là người dùng
không kiểm chứng được câu trả lời từ trích dẫn; (3)
quy tắc từ chối bằng danh sách cụm từ là xấp xỉ: đọc tay các câu bị xếp sai trước khi tin vào một con số, và giữ danh
sách cụm từ cố định giữa các lần chạy để so được bản trước và bản sau.

## Phương án khác

- Đo theo vị trí ký tự như bài này chỉ làm được khi bạn biết đoạn trích nằm ở đâu trong văn bản gốc. Với tài liệu PDF,
  trích dẫn là văn bản đã trích xuất, nên so theo chuỗi (chuẩn hoá khoảng trắng, chuỗi con chung dài nhất ≥ ngưỡng).
- Thay danh sách cụm từ bằng LLM-judge cho câu hỏi "câu trả lời có khẳng định điều khoản không tồn tại không" (xem AE 20).
  Judge cần bộ câu đã gán nhãn tay để đo chính nó trước khi dùng; với khách on-prem, judge cũng phải chạy on-prem.
