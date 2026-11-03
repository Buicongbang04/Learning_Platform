# Lời giải: Kueue chia quota GPU cho hai đội

Lời giải ở `queues.yaml`. Điểm chính của mỗi ClusterQueue:

```yaml
spec:
  cohortName: ml-__RUN__
  namespaceSelector: {}
  queueingStrategy: BestEffortFIFO
  preemption:
    reclaimWithinCohort: Any
    withinClusterQueue: Never
  resourceGroups:
    - coveredResources: [cpu, memory, __GPU__]
      flavors:
        - name: pool-__RUN__
          resources:
            - {name: __GPU__, nominalQuota: 2, borrowingLimit: 1}
```

- **Bước 3, mượn**: team-a dùng 2 (a1) = hết quota danh nghĩa. Cùng cohort, team-b mới dùng 1 trên 2, nên team-a mượn 1. Thiếu `cohortName` thì a2 nằm chờ.
- **Bước 4, hạn mức**: team-a đã mượn 1 = `borrowingLimit`. Cohort còn 0 (b1 1 + a1 2 + a2 1 = 4). a3 chờ, message của `QuotaReserved` nói thiếu quota. Không có `borrowingLimit` thì kết quả bước 4 vẫn giống (cohort đầy), nhưng ở tình huống cohort còn chỗ, team-a sẽ mượn hết phần của team-b: test chấm `borrowingLimit` bằng hợp đồng trong manifest.
- **Bước 5, đòi lại**: b2 cần 1, nằm trong quota danh nghĩa của team-b (b1 1 + b2 1 = 2), nhưng phần đó đang bị team-a mượn. `reclaimWithinCohort: Any` cho phép Kueue đẩy workload của ClusterQueue đang vượt danh nghĩa ra, bất kể ưu tiên. Kueue chọn ứng viên ít ảnh hưởng nhất (ưu tiên thấp hơn trước, rồi workload admit gần nhất), thường là a2. Workload bị đẩy có condition `Evicted` (reason `Preempted`), Job bị suspend lại, pod bị xoá, workload xếp hàng lại. Với `Never` (mặc định), b2 phải chờ a2 chạy xong.
- **Bước 6**: b2 chạy xong sau ~5 s, cohort trống 1 GPU, team-a được mượn lại; a3 (xếp hàng trước a2 vì a2 vào lại hàng đợi lúc bị đẩy) được admit.
- **Công bị mất**: job bị đẩy ra chạy lại từ đầu trừ khi nó checkpoint (module 15). Chính sách thực tế: chỉ cho mượn với job checkpoint được, hoặc đặt `WorkloadPriorityClass` để job quan trọng không bị chọn.

`namespaceSelector: {}` cho mọi namespace; ngoài đời nên chọn theo nhãn (`team: a`) để đội khác không gửi nhầm vào hàng của mình. LocalQueue ở namespace của đội, RBAC cho đội tạo Job/LocalQueue nhưng không sửa ClusterQueue.
