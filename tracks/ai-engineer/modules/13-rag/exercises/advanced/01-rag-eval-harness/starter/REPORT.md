# Đánh giá RAG trên Zalo Legal: chọn cấu hình bằng số liệu

TODO: viết theo khung trong README của bài (ít nhất 500 từ). Người đọc là trưởng nhóm phải quyết định cấu hình đưa
lên production: họ cần biết bạn đo gì, tin được tới đâu, và bạn khuyên gì.

## Tóm tắt

TODO: 3–4 câu có số. Cấu hình bạn khuyên dùng, nó hơn các cấu hình khác ở cột nào và bao nhiêu, đổi lại mất gì (độ
trễ), và mức tin cậy của điểm judge.

## Thiết lập

TODO: tập câu hỏi (bao nhiêu câu, lấy từ đâu, vì sao cố định), 4 cấu hình (retrieval, đơn vị nguồn, k), model sinh,
model judge, prompt judge (tóm tắt), phần cứng, thời gian sinh và chấm.

## Kết quả

TODO: bảng `run_eval` (mọi cột), và đọc bảng: chênh lệch nào lớn hơn nhiễu của 50 câu, chênh lệch nào không.

## Judge có đáng tin không

TODO: thí nghiệm nguồn sai (trung bình nguồn đúng / nguồn sai, số câu nguồn sai vẫn được chấm cao), hiệu chỉnh 20 câu
bằng người chấm (tỉ lệ đồng ý, judge sai theo hướng nào), số lần judge trả `nan`. Kết luận: cột faithfulness dùng
được cho việc gì, không dùng được cho việc gì.

## Phân tích lỗi

TODO: đọc tận mắt ít nhất 5 câu điểm thấp hoặc từ chối, xếp từng câu theo cây debug ở mục 6 lý thuyết (retrieval hỏng,
đoạn đúng có mà model không dùng, model bịa thêm, nhãn qrels thiếu). Mỗi loại bao nhiêu câu.

## Khuyến nghị và giới hạn

TODO: cấu hình khuyên dùng và điều kiện (ngân sách độ trễ, phần cứng), việc nên làm tiếp (đổi gì trong pipeline, đo
thêm gì), và những gì bảng này không nói được.
