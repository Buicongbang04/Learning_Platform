---
title: Trắc nghiệm - chọn công cụ GitOps và quản lý secret
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn đúng công cụ cho từng tình huống: GitOps kiểu pull hay CI đẩy thẳng, ArgoCD hay Flux, SOPS, Sealed Secrets, External Secrets hay
Vault; và đoán đúng hành vi của sync policy, hook, recipient, token TTL trước khi gặp chúng lúc sự cố.

## Đề bài

Bài này không có code. Làm 14 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 12 câu chọn một đáp án, 2 câu chọn mọi đáp án
đúng. Đọc mục 1 tới 6 của module trước khi làm.

Với mỗi câu, tự hỏi:

1. **Ai giữ credential** để thay đổi cluster hay đọc secret: CI, agent trong cluster, controller, hay con người?
2. **Nguồn sự thật** nằm ở đâu: Git, cluster, hay secret manager bên ngoài? Thứ gì xảy ra khi hai bên lệch nhau?
3. Khi một khoá hay token lộ, **phạm vi thiệt hại** là gì và mất bao lâu để thu hồi?

## Tiêu chí đạt

- Đúng ít nhất 11/14 câu.
- Với mỗi câu sai, nói lại được vì sao đáp án đúng đúng, và trong tình huống nào phương án bạn chọn mới hợp.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

`automated`, `prune`, `selfHeal` là ba công tắc riêng. Hook `PreSync` chạy trước mọi resource thường của lần sync đó. KV v2 của Vault đọc
qua `data/`, liệt kê qua `metadata/`.

### Gợi ý 2

Sealed Secrets gắn với khoá của một controller; SOPS gắn với danh sách recipient trong `.sops.yaml`; External Secrets không mã hoá gì cả, nó
đồng bộ từ secret manager. Gỡ một recipient không làm bản mã hoá cũ trong lịch sử Git hết đọc được.
