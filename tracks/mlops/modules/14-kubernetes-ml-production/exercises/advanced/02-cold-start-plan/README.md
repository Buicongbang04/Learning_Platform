---
title: Kế hoạch giảm cold start cho model scale-to-zero
level: advanced
services: []
files:
  - path: starter/PLAN.md
    note: Khung kế hoạch của bạn
run: []
---

## Mục tiêu

Biến một con số cold start khó chịu thành kế hoạch giảm có thứ tự, dựa trên số đo từng thành phần, có chi phí và có tiêu chí dừng: việc của một kỹ sư senior khi product hỏi "sao request đầu buổi sáng mất 70 giây?".

## Đề bài

Một nền tảng có 40 model ít dùng (mỗi model vài trăm request/ngày, theo đợt), chạy trên K8s với KEDA scale-to-zero theo hàng đợi, mỗi model một Deployment. Đo một model điển hình (image 4,2 GB, model 1,8 GB tải từ S3 lúc khởi động, node GPU T4):

| Thành phần | p50 | p95 |
| --- | --- | --- |
| Chờ KEDA phát hiện (`pollingInterval: 30`) | 15 s | 29 s |
| Xếp pod (node GPU còn chỗ) | 1 s | 3 s |
| Node GPU chưa có (cluster autoscaler thêm node) | 0 (đa số) | 180 s |
| Kéo image (node chưa có image) | 35 s | 60 s |
| Tải model từ S3 | 12 s | 25 s |
| Nạp lên GPU + warm-up | 8 s | 10 s |

Product muốn request đầu tiên (sau thời gian không dùng) có kết quả trong **15 giây ở p95**; ngân sách thêm tối đa **2 000 USD/tháng**. Một node T4 rảnh khoảng 380 USD/tháng.

Viết `starter/PLAN.md`:

1. **Phân rã**: tổng p50/p95 hiện tại theo từng đường (node có sẵn image hay không, có sẵn node hay không); thành phần nào chi phối p95.
2. **Các phương án**: ít nhất 6 (vd. giảm `pollingInterval`/proxy giữ request, pre-pull image bằng DaemonSet, image nhỏ hơn/lazy loading, cache model trên node hoặc PVC, giữ một node GPU ấm, `minReplicaCount: 1` cho model nóng, gộp nhiều model vào một server kiểu Triton/multi-model serving), mỗi cái: phần giảm ước tính, chi phí, rủi ro.
3. **Thứ tự làm** theo giảm/chi phí; con số kỳ vọng sau mỗi bước.
4. **Có cần scale-to-zero không**: với 40 model, so chi phí "về 0 + tối ưu cold start" với "gộp vào ít server luôn chạy".
5. **Đo và dừng**: đo cold start ở đâu (như queue của bài trung cấp 01), SLO cho nó, khi nào dừng tối ưu.

## Tiêu chí đạt

- Mọi con số giảm đều quy về một dòng trong bảng đo; tổng sau kế hoạch đạt hoặc nói rõ vì sao không đạt 15 s p95.
- Có so sánh chi phí bằng tiền, trong ngân sách.
- Tự chấm theo rubric trong `SOLUTION.md`, đạt từ 14/20.

## Gợi ý

### Gợi ý 1

p95 bị chi phối bởi đường hiếm nhưng dài (thêm node, kéo image). Tối ưu p50 trước là tối ưu sai chỗ.

### Gợi ý 2

40 model × vài trăm request/ngày: tổng traffic có thể vừa một hai server luôn chạy. Đôi khi câu trả lời đúng là không scale về 0.
