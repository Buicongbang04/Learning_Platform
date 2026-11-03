---
title: Trắc nghiệm K8s cho ML production
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Kiểm nhanh các quyết định của module: chọn tín hiệu autoscale, điều kiện để scale về 0, đo tải đúng cách, Triton batching, GPU là extended resource, Kueue admission và borrowing, quota và preemption.

## Đề bài

Bài này không có code. Làm 8 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới). Với mỗi câu, tự hỏi trước: cơ chế nào quyết định câu trả lời, và phương án sai đúng trong điều kiện nào?

## Tiêu chí đạt

- Trả lời đúng ít nhất 6/8 câu.
- Với mỗi câu sai, nói lại được cơ chế quyết định.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Đọc lại mục 1 (autoscale, cold start), mục 2 (đo tải, Triton), mục 3 (GPU), mục 4 (Kueue) và mục 5 (quota, priority) của lý thuyết.

### Gợi ý 2

Câu scale-to-zero: khi Deployment đang 0 replica, ai còn sống để báo rằng đã có tải?
