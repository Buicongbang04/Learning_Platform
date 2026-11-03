# Lời giải: chính sách promotion cho ETA

Bài Advanced không có một đáp án duy nhất; `decisions.yaml` có đáp án quyết định (kiểm bằng máy), `POLICY.md` là một bản mẫu
đã chạy qua test. Rubric dưới đây chấm lập luận.

## Các ca trong `decisions.yaml`

| Ca | Quyết định | Vì sao |
| --- | --- | --- |
| S1 | promote | Qua cả bốn cổng. Latency 1.1x trong trần 1.2x. |
| S2 | reject | MAE tổng giảm 10% nhưng airport xấu đi 18%. Ca kinh điển: trung bình tốt che chỗ yếu. |
| S3 | reject | Chỉ cải thiện 0.75% (dưới 1%). Nhanh hơn không được tính vào MAE; nếu đội muốn thưởng latency thì phải viết thành điều kiện khác (vd. "latency giảm 20% thì chấp nhận MAE không tệ đi"), không nới ngầm. |
| S4 | reject | `git_dirty = true`. Metric đẹp nhưng không tái lập được. |
| S5 | reject | long_haul +16.7% trên 400 chuyến, đủ lớn để tin. |
| S6 | reject | Latency 1.3x. Ensemble tốn thêm tài nguyên; nếu SLO còn dư thì đổi trần, đừng bỏ qua trần. |
| S7 | reject | Thiếu slice `night`. Báo cáo thiếu là trượt, nếu không thì xoá slice khỏi báo cáo là cách qua cổng. |
| S8 | promote | Cùng số đo với S5 nhưng long_haul chỉ có 150 chuyến: dưới `min_slice_n`, bị bỏ qua. Đây là chỗ chính sách yếu: nó cho qua đúng khi tập đánh giá nhỏ. Khắc phục là bắt tập đánh giá có tối thiểu n cho mọi slice bảo vệ (đánh giá lại với tập lớn hơn), không phải hạ ngưỡng. |

S3 và S8 là hai ca gây tranh cãi; điểm là người làm chính sách nhìn thấy kẽ hở và nói ra.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Quyết định đúng và lý do đúng chỗ | 25 | 8 ca đúng; lý do nêu số (18%, 1.3x), không chỉ "không đạt" |
| Chọn slice bảo vệ có lý do kinh doanh | 20 | Mỗi slice gắn với một hậu quả cụ thể (chuyến bay, an toàn, doanh thu), dung sai có lý do |
| Phát hiện kẽ hở của chính sách | 15 | Nêu ít nhất hai: slice nhỏ bị bỏ qua (S8), thưởng latency (S3), slice bị xoá khỏi báo cáo (S7), nhiều lần thử cho tới khi qua cổng |
| Quy trình và người duyệt | 15 | Cái gì tự động, cái gì cần người, ai ký ngoại lệ, ngoại lệ có hạn |
| Rollback và hậu kiểm | 15 | Rollback một lệnh không cần duyệt; hậu kiểm có chỉ số và thời hạn; xử lý nhãn về muộn |
| Rõ ràng và đọc được bởi PM | 10 | Mỗi phần ngắn, có sơ đồ đúng, không thuật ngữ trần |

Dưới 70: thường vì lý do chung chung ("model xấu hơn") hoặc chọn slice vì "nghe quan trọng" mà không gắn hậu quả.
