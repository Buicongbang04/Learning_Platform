---
title: Kiểm lại một bản phân tích interpretability
level: advanced
services: []
files:
  - path: starter/broken_analysis.ipynb
    note: Pipeline có lỗi im lặng, không nói ở đâu
  - path: starter/BUGS.md
    note: Ghi lại từng bug
  - path: tests/test_broken_analysis.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py iwslt15-en-vi
  - uv run jupyter lab tracks/ai-engineer/modules/08-interpretability/exercises/advanced/02-debug-interpretability/starter/broken_analysis.ipynb
  - uv run pytest tracks/ai-engineer/modules/08-interpretability/exercises/advanced/02-debug-interpretability -q
---

## Mục tiêu

Luyện vai người review một kết quả interpretability: notebook chạy hết, con số trông hợp lý, kết luận viết sẵn nghe có lý, nhưng
pipeline có lỗi im lặng. Bạn phải kiểm từng kết luận bằng phép thử có đáp án biết trước (sanity check) thay vì đọc code đoán mò. Làm
xong bạn có một checklist dùng lại cho mọi phân tích interpretability, của mình hay của người khác.

## Đề bài

**Phần cứng:** CPU · ~150 phút

Thời gian trên là thời gian điều tra; cả notebook chạy khoảng 1 phút (65 giây) trên CPU 4 luồng (đo trên PC dùng chung), lần đầu cần tải
GPT-2 small. `starter/broken_analysis.ipynb` là bản phân tích GPT-2 small của một đồng nghiệp: năm hàm (cache residual stream, logit
lens, probe có control task, activation patching, đánh giá SAE), bốn thí nghiệm và bốn kết luận đã viết vào báo cáo. Trong các hàm
có **4 bug im lặng** cố ý. Đề không nói chúng nằm ở đâu, và không phải hàm nào cũng có bug.

1. Với mỗi kết luận, nghĩ ra một phép thử mà bạn **biết trước** kết quả đúng phải là gì, chạy nó trong một cell `explore` mới, và dùng
   kết quả để khoanh vùng. Sửa bug ngay trong các cell hàm; không đổi tên, chữ ký, docstring.
2. Chạy lại bốn thí nghiệm sau khi sửa. Viết lại kết luận nào cần viết lại.
3. Ghi `starter/BUGS.md`: mỗi bug một mục `## Bug N: <tên ngắn>` với triệu chứng (con số), phép thử khoanh vùng (kết quả mong đợi và
   kết quả thật), sửa (dòng trước và sau), kết luận đúng sau khi sửa. Cuối cùng là checklist của bạn.
4. Làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Mọi test pass: chữ ký không đổi, mỗi hàm cho đúng kết quả trên các phép thử có đáp án biết trước của test.
- `BUGS.md` không còn TODO, ít nhất 4 mục `## Bug N`, ít nhất 300 từ.
- Nội dung chấm theo rubric trong `SOLUTION.md`: đủ 4 bug, mỗi bug có phép thử và con số, kết luận được viết lại đúng.

## Gợi ý

### Gợi ý 1

Mỗi phương pháp của module có ít nhất một điểm mà kết quả đúng được biết chính xác, không cần tin ai: một đại lượng ở tầng cuối phải
trùng với output của model, một phép can thiệp ở chỗ hai input giống hệt nhau phải không đổi gì, một phép thay ở chỗ chúng khác nhau
duy nhất phải khôi phục hoàn toàn, một baseline tầm thường phải cho đúng giá trị định nghĩa của thước đo. Liệt kê các điểm đó trước
khi đọc code.

### Gợi ý 2

Dữ liệu nhỏ do bạn dựng mà đáp án tính được bằng tay (vài token, một model tí hon khởi tạo ngẫu nhiên, đặc trưng là one-hot của token
id) bắt lỗi nhanh hơn chạy lại trên GPT-2. Khi một con số "quá đẹp" hoặc "quá tệ" so với các bài Intermediate, đó là chỗ đầu tiên
cần nghi.
