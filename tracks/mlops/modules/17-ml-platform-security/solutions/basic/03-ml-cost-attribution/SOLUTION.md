# Lời giải: cost attribution cho ML

`cost.py` cạnh tệp này là bản tham khảo; đáp án trắc nghiệm ở `quiz-answers.yaml`.

- **Đội lấy từ namespace, model lấy từ nhãn pod.** Thứ không map được không bị bỏ đi mà vào `unallocated` / `unlabelled`. Một báo cáo
  âm thầm bỏ 20% chi phí cho người đọc cảm giác sai rằng mọi thứ đã được giải thích; dòng `UNALLOCATED` to rõ trong báo cáo là động lực để
  gắn nhãn.
- **Idle theo từng tài nguyên.** CPU dùng vượt (trên request hay do burst) không bù được cho GPU nằm im. Cộng gộp trước rồi mới trừ sẽ giấu
  GPU idle, thứ đắt nhất.
- **Chia idle theo chi phí trực tiếp.** Đây là một chính sách, không phải chân lý. Các lựa chọn khác: chia theo request GPU (đội nào giữ
  chỗ thì trả), để idle thành chi phí của đội nền tảng (đội nền tảng có động lực bin-packing và autoscale), hoặc chỉ chia phần idle vượt
  một mức đệm hợp lý (vd. 20% headroom là chi phí chung). Điều quan trọng là tổng khớp hoá đơn (test bảo toàn) và mọi đội biết luật.
- **Tính theo request, không theo mức dùng thực tế.** Scheduler giữ chỗ theo request; một pod xin 4 GPU mà dùng 10% vẫn chặn người khác.
  Báo cáo theo request đặt động lực đúng: xin vừa đủ. Báo thêm tỉ lệ dùng thật trên request để đội biết cắt ở đâu.

**Showback trước, chargeback sau.** Khi nhãn còn thiếu nhiều, chargeback làm các đội tranh cãi con số thay vì sửa nhãn. Chạy showback vài
tháng, đưa `unallocated` xuống dưới khoảng 5%, rồi mới trừ ngân sách thật.

**Ở nơi làm việc.** Dữ liệu đến từ OpenCost hay Kubecost (chi phí theo pod, namespace, nhãn) cộng hoá đơn cloud cho phần ngoài cluster
(object storage, dịch vụ managed); nhãn bắt buộc được ép bằng admission policy (Kyverno, Gatekeeper) hoặc bằng template dự án (bài
Basic 01). Chỉ số đơn vị (chi phí trên 1 000 dự đoán, trên một lần retrain) quan trọng hơn tổng tiền vì nó so được giữa các model.
