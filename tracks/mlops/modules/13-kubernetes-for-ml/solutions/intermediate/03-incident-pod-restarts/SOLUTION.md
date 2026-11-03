# Lời giải: pod model bị kill lặp lại ngay sau deploy

## Chẩn đoán

```bash
kubectl --context kind-mlops -n <ns> get pods                      # RESTARTS tăng, CrashLoopBackOff
kubectl --context kind-mlops -n <ns> describe pod <pod>            # Last State: Terminated, Reason: OOMKilled, Exit Code: 137
kubectl --context kind-mlops -n <ns> logs <pod> --previous         # chỉ "loading model from ..."
```

`Exit Code 137` = 128 + 9 (SIGKILL); `Reason: OOMKilled` nghĩa là cgroup của container vượt `limits.memory` và kernel giết tiến trình. Không có traceback vì tiến trình không kịp làm gì. Probe không liên quan: pod chết trước cả khi liveness bắt đầu.

## Nguyên nhân

`limits.memory: 256Mi` thấp hơn mức bộ nhớ **lúc nạp model** v3. Bundle v3 lớn (kèm mẫu tham chiếu 6 triệu dòng, ~144 MB). Service đọc cả tệp vào bộ nhớ rồi giải tuần tự (giống tải từ object storage vào RAM), nên lúc nạp cùng lúc có bytes của tệp và object đã giải; đo được đỉnh khoảng 330-400 MiB. Sau khi nạp, service chỉ giữ thống kê của mẫu tham chiếu, bộ nhớ ổn định chỉ ~90 MiB. Ai đặt limit theo số `kubectl top` của pod đang chạy ổn (bản v1/v2) sẽ thấy 256Mi là dư gấp đôi, nhưng con số đó chưa bao giờ nhìn thấy đỉnh lúc khởi động.

## Sửa

```yaml
resources:
  requests: {cpu: 100m, memory: 512Mi}
  limits: {cpu: "1", memory: 640Mi}
```

- Limit lấy từ **đỉnh đo được** cộng dư (~1,6 lần): chạy pod với limit rộng ở staging, đọc `container_memory_working_set_bytes` (cAdvisor/Prometheus) hoặc `memory.peak` của cgroup, không đọc `kubectl top` lúc ổn định.
- Requests nâng theo: node cần có chỗ cho đỉnh lúc nạp; requests quá thấp làm scheduler xếp nhiều pod vào một node rồi cùng nạp model lúc rollout.
- Cách sửa gốc rễ hơn (ngoài phạm vi test): nạp kiểu stream thay vì đọc cả tệp vào RAM, và không đóng dữ liệu tham chiếu vào bundle serving (lưu thống kê đã tính sẵn).

## Bài học vận hành

- Model mới = profile tài nguyên mới. Đưa "đỉnh bộ nhớ lúc khởi động" vào checklist release của model, như latency và accuracy.
- Alert theo `kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}` và tốc độ tăng `restartCount`, không chỉ theo pod Ready.
