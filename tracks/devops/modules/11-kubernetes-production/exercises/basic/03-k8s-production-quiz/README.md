---
title: Trắc nghiệm - RBAC, Pod Security, NetworkPolicy, scheduling, quota, autoscaling, đóng gói, nâng cấp, nền tảng
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Trả lời được những câu hỏi tình huống mà người vận hành Kubernetes production gặp: quyền có hiệu lực ở đâu, vì sao pod bị chặn, vì sao
drain treo, vì sao HPA không scale, chọn Helm hay Kustomize, nâng cấp theo thứ tự nào, và chọn nền tảng nào.

## Đề bài

Bài này không có code. Làm 14 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 12 câu chọn một đáp án, 2 câu chọn mọi đáp án
đúng. Đọc mục 1 tới 7 của module trước khi làm.

Với mỗi câu, tự hỏi:

1. Quyết định này do **thành phần nào** đưa ra (authenticator, RBAC, admission plugin, scheduler, kubelet, controller), và nó dựa vào dữ
   liệu gì?
2. Cơ chế này có đi qua **Eviction API** hay **admission** không, tức là PDB, quota, Pod Security có được kiểm không?
3. Lựa chọn này **ai vận hành** sau khi bạn rời đi, và tốn gì khi nâng cấp?

## Tiêu chí đạt

- Đúng ít nhất 11/14 câu.
- Với mỗi câu sai, nói lại được vì sao đáp án đúng đúng và khi nào phương án bạn chọn mới đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

RoleBinding luôn giới hạn quyền trong namespace của nó, kể cả khi trỏ tới ClusterRole. NetworkPolicy chỉ có allow và cộng dồn. Pod Security
chặn pod chứ không chặn Deployment.

### Gợi ý 2

Drain đi qua Eviction API nên tôn trọng PDB; taint `NoExecute` và xoá pod thì không. HPA tính phần trăm CPU trên request; Cluster
Autoscaler nhìn pod Pending và tổng requests chứ không nhìn CPU thật.
