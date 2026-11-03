# Lời giải: Deployment, Service và ConfigMap

Xem `eta-api.yaml`. Những điểm chấm:

- **ConfigMap thay cho biến ghi cứng.** Đổi model (v1 sang v2) chỉ là sửa ConfigMap rồi `kubectl rollout restart deployment/eta-api`; manifest Deployment không đổi. Lưu ý: pod **không** tự đọc lại `envFrom` khi ConfigMap đổi, phải restart (hoặc dùng công cụ như Kustomize/Helm sinh tên ConfigMap theo hash nội dung để đổi ConfigMap kéo theo rollout).
- **readinessProbe** quyết định pod có nằm trong Endpoints của Service không. Không có nó, Service gửi request tới pod ngay khi tiến trình bắt đầu, kể cả lúc model còn đang nạp.
- **requests** là thứ scheduler dùng để xếp pod; **limits** là trần lúc chạy. Thiếu requests thì pod thuộc QoS `BestEffort`, bị đuổi đầu tiên khi node thiếu tài nguyên.
- **Service cổng 80 → `targetPort: http`**: client trong cluster gọi `http://eta-api`, không cần biết cổng của container.
- Test kiểm `model_version` qua HTTP vì "pod Ready" chỉ nói tiến trình trả lời probe, không nói nó phục vụ đúng model.
