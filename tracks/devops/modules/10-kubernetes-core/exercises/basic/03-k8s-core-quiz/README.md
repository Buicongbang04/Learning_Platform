---
title: Trắc nghiệm - kiến trúc, workload, probe, Service, storage, etcd, chọn bản Kubernetes
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Trả lời được các câu hỏi tình huống mà người vận hành Kubernetes gặp hằng tuần: thành phần nào làm gì khi một thứ hỏng, probe nào
gây sự cố dây chuyền, rollout mất capacity ở đâu, vì sao Service không có endpoint, và chọn bản Kubernetes theo ràng buộc.

## Đề bài

Bài này không có code. Làm 14 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 12 câu chọn một đáp án, 2 câu chọn mọi
đáp án đúng. Đọc mục 1 tới 6 của module trước khi làm.

Với mỗi câu, tự hỏi:

1. Thành phần nào của control plane hay node **sở hữu** việc này, và nó còn làm được không khi thành phần khác chết?
2. Probe, strategy hay selector này được **đánh giá** bởi ai, lúc nào, và hậu quả khi nó sai là gì?
3. Dữ liệu này **sống** ở đâu: trong etcd, trong PV, hay chỉ trong container?

## Tiêu chí đạt

- Đúng ít nhất 11/14 câu.
- Với mỗi câu sai, nói lại được vì sao đáp án đúng đúng và khi nào phương án bạn chọn mới đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Control plane quyết định (API server lưu, scheduler chọn node, controller sửa lệch), node thực thi (kubelet, container runtime,
kube-proxy). Một thứ đã chạy trên node không cần control plane để tiếp tục chạy.

### Gợi ý 2

Readiness quyết định pod có nhận traffic qua Service không; liveness quyết định container có bị restart không; startup hoãn hai
cái kia. QoS do requests và limits quyết định, và quyết định luôn thứ tự bị evict.
