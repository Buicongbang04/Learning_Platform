# Hướng làm: phát hành challenger an toàn

Bài Advanced không có một đáp án duy nhất. Dưới đây là hướng làm cho code, các quyết định thiết kế
cho tài liệu, và rubric chấm.

## Code

- **`shadow_report`**: lọc `label.notna()` trước khi tính AUC; nếu chỉ còn một lớp (hoặc không còn
  dòng nào) thì AUC là NaN chứ không ném lỗi, vì những ngày đầu shadow luôn chưa có nhãn. PSI giữa
  score hai model dùng score champion làm reference. `flip_rate` tính trên **mọi** request, không
  cần nhãn: đây là chỉ số có sớm nhất.
- **`promotion_decision`**: thứ tự quy tắc là một phần của thiết kế. Thiếu dữ liệu xét trước, vì
  mọi so sánh khác vô nghĩa khi chưa đủ nhãn. Latency là ràng buộc cứng: model tốt hơn mà vi phạm SLA
  vẫn không được promote. `flip_rate` cao không có nghĩa là xấu, nhưng nghĩa là hành vi đổi nhiều
  (danh sách khách được liên hệ khác hẳn): cần một người quyết, không để tự động. So sánh
  `not gain >= min_auc_gain` để AUC NaN rơi vào `keep`.
- **Alias**: promote là ba thao tác (đặt `previous_champion`, chuyển `champion`, xoá `challenger`).
  Service nạp `models:/bad-review@champion`, nên không phải deploy lại code. Rollback chỉ đi lùi
  một bước và xoá `previous_champion`, để không vô tình nhảy qua lại giữa hai version.

## Quyết định cho RELEASE.md

**Thời điểm dự đoán.** Cả champion và challenger phải chấm tại cùng thời điểm (đơn vừa giao xong) và
chỉ dùng thông tin có tại lúc đó. Một challenger dùng thêm feature từ review (độ dài bình luận…) sẽ
có AUC offline rất cao và vô dụng ở production: đó là leakage, không phải cải tiến.

**Thời lượng shadow.** Với khoảng 1 259 đơn giao xong mỗi tuần (trung vị 06/2017 tới 07/2018) và
review về sau khi giao với trung vị khoảng 2 ngày (90% trong vòng 5.3 ngày), `min_labeled = 500` đạt sau chưa tới một
tuần. Nhưng 500 nhãn với tỉ lệ review xấu 12.8% chỉ có khoảng 64 đơn xấu: sai số của AUC lớn hơn
nhiều so với ngưỡng `min_auc_gain = 0.005`. Một kế hoạch tốt nêu rõ điều này và chọn một trong
các cách: chạy shadow 3 tới 4 tuần (trọn tuần, tránh mùa vụ), dùng bootstrap CI cho chênh lệch AUC
thay vì ngưỡng điểm, hoặc dựa nhiều hơn vào so sánh offline trên tập test lớn.

**Canary.** Sau shadow, challenger thật sự quyết định cho 10% đơn (random theo `customer_unique_id`
để một khách không bị hai model đối xử khác nhau). Đây là chỗ đo **tác động kinh doanh** (tỉ lệ
review xấu sau khi được liên hệ, chi phí CSKH), thứ shadow không đo được vì ở shadow challenger
không hành động. Thiết kế phần này như một A/B test (module 03).

**Rollback.** Đổi alias là tức thì; quyết định đã gửi (khách đã được gọi) thì không lấy lại được.
Điều kiện rollback viết trước: tỉ lệ lỗi service, p95 latency, PSI score vượt ngưỡng so với tuần
shadow, hoặc khiếu nại CSKH tăng.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Code đúng | 20 | Test pass; xử lý đúng nhãn thiếu và thứ tự quy tắc |
| Model card | 15 | Thời điểm dự đoán, dữ liệu, metric, nhóm yếu, cách dùng bị cấm; số liệu thật |
| So sánh offline | 10 | Cùng tập test theo thời gian, có khoảng tin cậy hoặc nhận xét về nhiễu |
| Lộ trình shadow → canary → toàn bộ | 20 | Thời lượng tính từ traffic và độ trễ nhãn; điều kiện chuyển bước và dừng |
| Ngưỡng promote có lý do | 10 | Mỗi ngưỡng gắn với SLA hoặc giá trị kinh doanh, nhận ra giới hạn power của 500 nhãn |
| Monitoring sau phát hành | 15 | Chỉ số, cửa sổ, ngưỡng, người nhận; tín hiệu sớm khi nhãn chưa về |
| Rollback | 10 | Khi nào, ai quyết, bao lâu, cái gì không đảo ngược được |

Từ 70 điểm: đủ để mang ra buổi review phát hành.
