# Lời giải: ước tính chi phí GPU

`cost.py` cạnh tệp này là lời giải chạy được; `quiz-answers.yaml` là đáp án trắc nghiệm.

## Ý chính

- **Giờ GPU phải trả là $$H_1 / e$$, không phụ thuộc số GPU nếu $$e$$ không đổi.** 8 GPU A100 với hiệu suất 0.8 cho job 800 giờ một card:
  125 giờ đồng hồ nhưng 1 000 giờ GPU (4 100 USD on-demand). Thêm GPU mua thời gian, không mua tiết kiệm; khi $$e$$ giảm (nhiều node,
  mạng chậm) thì vừa đắt hơn.
- **Spot rẻ hơn kể cả sau khi trả phần làm lại.** Cùng job trên A100 spot, 0.02 lần thu hồi mỗi giờ, checkpoint mỗi 2 giờ, khởi động lại
  15 phút: thêm 3.1 giờ (128.1 giờ), 1 640 USD. Điều kiện là job **resume được** (bài Basic 02); không có checkpoint thì mỗi lần thu hồi
  là làm lại từ đầu và công thức này sai hoàn toàn.
- **GPU đắt hơn theo giờ có thể rẻ hơn theo job.** H100 x8 spot (job 300 giờ một card vì nhanh hơn ~2.7 lần) xong trong 51.9 giờ, 1 017
  USD: rẻ nhất mà còn nhanh nhất trong các phương án spot. So theo giá giờ thì sẽ chọn sai.
- **Deadline đổi đáp án.** Deadline 51 giờ loại mọi phương án spot (phần làm lại đẩy H100 spot quá 51 giờ), còn H100 on-demand 2 792 USD.
  Deadline 10 giờ: không phương án nào, trả `None` để người gọi biết phải đổi yêu cầu chứ không âm thầm chọn phương án trễ.
- **Khoảng checkpoint có điểm tối ưu.** Young: $$\tau = \sqrt{2\delta/\lambda}$$; ghi 3 phút, 0.02 lần thu hồi mỗi giờ thì khoảng 2.2 giờ.
  Dày hơn tốn thời gian ghi, thưa hơn mất nhiều việc mỗi lần thu hồi.

## Mô hình này sai ở đâu ngoài đời

- Tỉ lệ thu hồi spot không cố định: theo vùng, loại GPU, giờ trong ngày; có lúc không thuê được spot nào (capacity), job chờ hàng giờ.
- Khi một node bị thu hồi, cả nhóm DDP dừng; với $$N$$ node, tỉ lệ thu hồi của job xấp xỉ $$N$$ lần tỉ lệ một node.
- Hiệu suất scale đo ở 8 GPU không dùng được cho 64 GPU; đo lại ở từng mức.
- Bỏ qua chi phí lưu trữ checkpoint, egress, và giờ GPU chết khi job hỏng giữa đêm không ai biết.

## Trắc nghiệm

- **fits-one-gpu (a)**: vừa một GPU thì DDP đơn giản và nhanh nhất; pipeline/tensor parallel chỉ thêm giao tiếp và bong bóng.
- **seven-b-memory (b)**: 16 byte mỗi tham số x 7 tỉ = 112 GB trạng thái model, chưa tính activation.
- **zero-stages (c)**: ZeRO-1 optimizer state, ZeRO-2 thêm gradient, ZeRO-3 thêm tham số.
- **fsdp-numel (c)**: `DTensor.numel()` là kích thước toàn cục (bài Intermediate 01).
- **elastic-meaning (b)**: elastic khởi động lại cả nhóm; không có checkpoint thì là chạy lại từ đầu.
- **asha-vs-search (d)**: ASHA là scheduler dừng sớm; chọn config là việc của search algorithm.
- **data-bound (a, b, c)**: đo trước, rồi thêm worker, rồi sửa định dạng dữ liệu; GPU nhanh hơn chỉ làm GPU chờ nhiều hơn.
- **tool-choice (b)**: đã có cụm Ray thì Ray Train và Tune dùng lại hạ tầng, Ray Data nối thẳng vào vòng huấn luyện.
