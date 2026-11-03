---
title: Trắc nghiệm Kubernetes cho ML
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Kiểm nhanh các quyết định nền của module: phần nào kế thừa từ track DevOps, KServe ở RawDeployment làm gì với canary, bằng chứng nào cho thấy model đúng, GPU trên K8s, Argo Workflows và Argo CD, kind dùng vào đâu.

## Đề bài

Bài này không có code. Làm 6 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới). Với mỗi câu, tự hỏi trước: cơ chế nào của Kubernetes hay KServe quyết định câu trả lời, và phương án sai đúng trong điều kiện nào?

## Tiêu chí đạt

- Trả lời đúng ít nhất 5/6 câu.
- Với mỗi câu sai, nói lại được cơ chế quyết định.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Đọc lại mục 4 (KServe) và mục 6 (GPU) của lý thuyết module.

### Gợi ý 2

Câu canary: KServe chia traffic theo revision nhờ thành phần nào, và chế độ RawDeployment có thành phần đó không?
