---
title: Thiết kế nền tảng K8s multi-tenant cho 3 đội dùng chung GPU
level: advanced
services: []
files:
  - path: starter/DESIGN.md
    note: Khung thiết kế của bạn
run: []
---

## Mục tiêu

Thiết kế cách ba đội ML dùng chung một cluster có GPU đắt tiền như một kỹ sư platform trình cho các trưởng nhóm: ai được dùng bao nhiêu, ai chờ ai, ai đẩy được ai, ai thấy được ai, và đo thế nào để biết chính sách công bằng.

## Đề bài

Cluster: 4 node GPU, mỗi node 8 card A100 80GB (MIG được), cộng 6 node CPU 32 nhân. Ba đội:

- **Search ranking**: 6 model online, SLO p95 50 ms, traffic theo giờ (đỉnh tối gấp 4 lần đêm), retrain hằng đêm trên 8 GPU khoảng 3 giờ.
- **Recommendation**: 1 model online lớn chạy GPU (đỉnh 2 000 req/s), fine-tune hằng tuần trên 16 GPU khoảng 20 giờ, checkpoint mỗi 30 phút.
- **Research**: notebook tương tác (10–15 người), thử nghiệm ngắn 1–4 GPU, không có SLO, deadline hội nghị 2 lần/năm thì cần gấp đôi.

Viết `starter/DESIGN.md` theo khung có sẵn:

1. **Ranh giới tenant**: namespace (tách serving, training, notebook), node pool, taint/toleration; vì sao không cluster riêng mỗi đội.
2. **Quota và hàng đợi**: ResourceQuota/LimitRange theo namespace; Kueue (ResourceFlavor cho A100 nguyên card và cho MIG nếu dùng, ClusterQueue mỗi đội, cohort, `nominalQuota`, `borrowingLimit`, `lendingLimit`); bảng số GPU từng đội, lý do.
3. **Ưu tiên và preemption**: PriorityClass cho pod, WorkloadPriorityClass cho Kueue; ai đẩy được ai; job bị đẩy ra mất bao nhiêu công (checkpoint).
4. **Chia GPU**: chỗ nào dùng card nguyên, MIG, time-slicing (notebook?), chỗ nào không; rủi ro cô lập.
5. **Serving**: autoscale theo tín hiệu gì; có scale về 0 model nào không; giữ capacity GPU cho đỉnh tối thế nào khi training cũng cần.
6. **Bảo vệ và quan sát**: RBAC (ai sửa ClusterQueue), NetworkPolicy giữa tenant; metric để biết chính sách có công bằng (GPU utilization theo đội, thời gian chờ admission, số lần bị preempt, GPU giữ mà không dùng).
7. **Mùa deadline**: chính sách tạm thời khi research cần gấp đôi, ai quyết, quay lại thế nào.

## Tiêu chí đạt

- Mỗi quyết định có lý do và một đánh đổi; có ít nhất một sơ đồ và một bảng số GPU cộng lại khớp 32 card.
- Có đường đi rõ cho ba tình huống: tối thứ sáu (đỉnh serving + fine-tune đang chạy), research nộp 40 job nhỏ cùng lúc, một node GPU chết.
- Tự chấm theo rubric trong `SOLUTION.md`, đạt từ 14/20.

## Gợi ý

### Gợi ý 1

Bắt đầu từ tài nguyên khan hiếm nhất và SLO chặt nhất: serving GPU của recommendation vào giờ đỉnh. Mọi thứ khác xếp quanh nó.

### Gợi ý 2

Mượn quota (cohort) chỉ an toàn khi bên mượn chịu được bị lấy lại. Đội nào chịu được, đội nào không?
