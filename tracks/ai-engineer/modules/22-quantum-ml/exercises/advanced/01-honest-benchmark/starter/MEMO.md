# Memo: có nên đầu tư quantum machine learning cho bài toán phân loại?

TODO: viết cho CTO, người không đọc code (ít nhất 500 từ, có bảng). Mỗi khẳng định đi kèm một con số bạn đo
trong `benchmark.ipynb`, hoặc một trích dẫn. Nói rõ cái gì bạn đo được và cái gì bạn chỉ suy luận.

## Khuyến nghị

TODO: 3–5 câu đầu tiên, đủ để người đọc dừng ở đây vẫn biết quyết định: đầu tư / không / theo dõi, vì sao, chi phí của
việc chờ đợi.

## Bằng chứng

TODO: bảng benchmark (3 bộ dữ liệu x 4 model, mean ± std, thời gian) và khoảng tin cậy của chênh lệch; kết quả
barren plateau (phương sai gradient theo số qubit, độ dốc); dequantization (kernel angle tính bằng công thức đóng,
sai lệch và thời gian); nhiễu và shots (accuracy và độ tương phản kernel).

## Giới hạn của benchmark này

TODO: dữ liệu nhỏ, simulator không phải phần cứng, ít qubit, mô hình nhiễu đơn giản; điều gì bạn không thể kết
luận từ đây.

## Khi nào nên xem lại

TODO: tín hiệu cụ thể nào (phần cứng, thuật toán, bài toán có cấu trúc lượng tử) sẽ làm bạn đổi khuyến nghị, và
bạn đề xuất theo dõi bằng cách nào (ví dụ: chi phí một thí nghiệm nhỏ mỗi năm).
