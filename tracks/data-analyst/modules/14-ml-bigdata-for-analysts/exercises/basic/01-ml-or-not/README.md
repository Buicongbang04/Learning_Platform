---
title: DA có nên làm ML không? Chọn cách tiếp cận và công cụ theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Nhận một yêu cầu "làm AI/ML" và quyết định như DA senior: bài toán thuộc loại nào (supervised, unsupervised,
reinforcement), quy tắc hay bảng SQL có đủ không, thuật toán nào hợp để dùng và giải thích, khi nào Deep Learning đáng
công, và dữ liệu có thật sự cần Spark không.

## Đề bài

Bài này không có code. Đọc các tình huống dưới (số liệu Telco lấy từ phần 2–4 lý thuyết, tính trên dữ liệu thật), rồi
làm 10 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới).

**Số liệu tham khảo, Telco Customer Churn** (7 043 khách, 26.5% rời bỏ; model đo trên tập test 1 761 khách):

| Cách chọn khách để gọi giữ chân | Khách được gọi | Tỉ lệ rời trong số được gọi | Tỉ trọng khách rời được gọi |
| --- | --- | --- | --- |
| Quy tắc: month-to-month và gắn bó tối đa 12 tháng | 28.3% | 51.4% | 54.8% |
| Logistic regression, 30% khách điểm cao nhất | 30% | 58.4% | 66.2% |
| Logistic regression, 10% khách điểm cao nhất | 10% | 73.4% | 27.8% |
| Gọi ngẫu nhiên | bất kỳ | 26.5% | bằng tỉ lệ khách được gọi |

Các tình huống trong câu hỏi là ví dụ giả định về yêu cầu stakeholder thường gặp.

## Tiêu chí đạt

- Trả lời đúng ít nhất 8/10 câu.
- Với mỗi câu sai, chỉ ra được phần nào của lý thuyết (phần 2 khi nào làm ML, phần 3 thuật toán, phần 4 đánh giá, phần 6
  Deep Learning, phần 7 Big Data) cho đáp án đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Trước khi nghĩ tới thuật toán, hỏi: kết quả sẽ thay đổi quyết định nào, ai dùng, bao lâu một lần? Câu hỏi "vì sao" và
"nếu làm X thì sao" không phải bài toán dự đoán.

### Gợi ý 2

Với Big Data, đổi dữ liệu ra con số trước: bao nhiêu dòng, bao nhiêu GB, định dạng gì, đang nằm ở đâu. Laptop với DuckDB
đọc được hàng trăm triệu dòng Parquet; warehouse của công ty thường là nơi tính tốt nhất.
