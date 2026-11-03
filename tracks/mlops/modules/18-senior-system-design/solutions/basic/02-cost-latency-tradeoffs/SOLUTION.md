# Lời giải: đánh đổi chi phí, độ trễ, chất lượng

`tradeoffs.py` cạnh tệp này là lời giải chạy được.

## Ý chính

- **Cache giảm trung bình, không giảm đuôi.** Hit 80%: trung bình từ 42 ms xuống 10 ms, nhưng 20% yêu cầu vẫn đi qua model nên p99
  vẫn khoảng 182 ms. Chỉ khi miss dưới 1% thì p99 mới rơi vào phân phối của cache. SLO thường viết bằng p99, nên "thêm cache" là câu
  trả lời sai cho SLO đuôi nếu hit rate không rất cao. Hit 0% còn tệ hơn không có cache: thêm một bước tra và thêm tiền.
- **Batch trả tiền cho mọi thực thể, realtime trả tiền cho mọi câu hỏi.** 2 triệu user làm mới 4 lần mỗi ngày (80 USD) rẻ hơn
  realtime (246 USD, trong đó 96 USD là replica bật cả ngày); 50 triệu thực thể làm mới mỗi giờ thì ngược lại. Biến quyết định là tỉ lệ
  "số câu hỏi / số thực thể x số lần làm mới" và độ cũ chấp nhận được (`24 / refreshes` giờ).
- **Distillation là đầu tư.** 9 000 USD tiết kiệm 900 USD mỗi ngày hoà vốn sau 10 ngày; nếu model bị thay sau 1 tuần thì lỗ. Tính
  cả chi phí lặp lại: mỗi lần teacher đổi phải distill lại.
- **Chọn là bài toán có ràng buộc.** Ràng buộc cứng (p99, mức giảm chất lượng trong budget) loại phương án trước; trong số còn lại
  mới tối ưu tiền. Đổi ràng buộc một chút là đổi lựa chọn: đó là thứ cần đưa lên design review chứ không quyết một mình.

## Mô hình này sai ở đâu ngoài đời

- p99 của hỗn hợp cache và model không phải bước nhảy ở 1%: nó trượt dần; dùng số đo thật hay mô phỏng khi cần chính xác.
- Hit rate không cố định: phụ thuộc TTL, độ phân tán khoá, thời điểm (cold cache sau deploy).
- Batch còn chi phí lưu trữ và độ trễ của job; realtime còn chi phí feature store online.

## Đáp án trắc nghiệm

- `cache-tail` (b): 15% miss vẫn đi qua model, p99 vẫn khoảng 200 ms.
- `batch-vs-realtime` (c): 40 nghìn câu hỏi trên 3 triệu thực thể, feature phải tươi vài phút: batch vừa đắt (tính cho người không
  hỏi) vừa cũ.
- `distill-when` (a): quyết định là thời gian hoà vốn so với tuổi thọ model, và mức giảm có nằm trong budget chất lượng không.
- `levers` (a, b, c): cache, routing theo độ khó, batching và giới hạn token đều giảm GPU-giờ; temperature không đổi chi phí.
- `quality-budget` (d): error budget tồn tại để tiêu có chủ đích; thử có canary và điều kiện rollback, không đổi một lần cho tất cả.
- `precompute-staleness` (c): trước khi đổi model hay phần cứng, hỏi độ cũ 6 giờ có hợp với giờ cao điểm không.
