# Lời giải: PriorityClass và preemption

Lời giải ở `priorityclasses.yaml`: serving 100 000 (`PreemptLowerPriority`), research 5 000 (`preemptionPolicy: Never`), training 1 000; cả ba `globalDefault: false`.

- **Bước 2**: research có ưu tiên cao hơn training nên được xếp **trước** trong hàng chờ của scheduler, nhưng `Never` nghĩa là scheduler không xoá pod nào để lấy chỗ cho nó. Hết GPU thì nó chờ. Nó sẽ chạy khi có GPU trống (một pod training xong hoặc bị xoá) và không còn pod ưu tiên cao hơn đang chờ. Đây là chính sách hợp cho notebook: không giết job training 20 giờ chỉ để mở notebook.
- **Bước 3**: serving `PreemptLowerPriority` nên scheduler chọn nạn nhân trên node: pod ưu tiên thấp nhất đủ để giải phóng 1 GPU, ít nạn nhân nhất. Pod training bị đánh dấu `DisruptionTarget` (reason `PreemptionByScheduler`), xoá với `terminationGracePeriodSeconds`. Pod serving được "nominate" vào node đó, nên pod research không chen vào chỗ vừa trống.
- **globalDefault**: class mặc định áp cho mọi pod mới **không** khai `priorityClassName` ở mọi namespace. Trên cluster dùng chung, đặt nhầm là đổi thứ tự lập lịch của mọi người.
- Giá trị từ 1 tỉ trở lên dành cho `system-cluster-critical`, `system-node-critical`.

Hạn chế của preemption ở mức pod: nó không biết "job" (đẩy 1 trong 4 worker ra làm cả job distributed hỏng), không có quota theo đội. Với job batch, dùng Kueue (bài trung cấp 02) với WorkloadPriorityClass: đẩy cả workload, có hàng đợi.
