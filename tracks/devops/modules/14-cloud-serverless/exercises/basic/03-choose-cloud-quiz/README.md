---
title: Trắc nghiệm - chọn nhà cung cấp cloud và nền tảng serverless
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn đúng nơi chạy cho từng tình huống: AWS, Azure, GCP, DigitalOcean, Alibaba Cloud, Hetzner, Contabo, Heroku, hay nền tảng serverless
như Lambda, Cloudflare Workers, Vercel, Netlify, Azure Functions, Cloud Run functions; và nhận ra trách nhiệm của mình trong shared
responsibility model, các cách giảm hoá đơn không làm hỏng hệ thống.

## Đề bài

Bài này không có code. Làm 14 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 12 câu chọn một đáp án, 2 câu chọn mọi đáp án
đúng. Đọc mục 1 tới 6 của module trước khi làm.

Với mỗi câu, tự hỏi:

1. **Người dùng ở đâu, dữ liệu phải nằm ở đâu?** Region gần nhất của từng nhà cung cấp, luật dữ liệu.
2. **Ai vận hành?** Team có người làm hạ tầng không, có trực đêm không?
3. **Tải trông thế nào?** Đều cả ngày, theo đợt, hay gần như không có; mỗi lần chạy bao lâu?
4. **Hệ sinh thái sẵn có?** Đăng nhập, dữ liệu, hợp đồng đang ở đâu.

## Tiêu chí đạt

- Đúng ít nhất 11/14 câu.
- Với mỗi câu sai, nói lại được vì sao đáp án đúng đúng, và trong tình huống nào phương án bạn chọn mới hợp.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Giới hạn cứng đáng nhớ: Lambda chạy tối đa 15 phút; API Gateway HTTP API không có usage plan hay API key; Cloudflare Workers chạy trên
isolate V8 chứ không phải container. Hetzner và DigitalOcean không có region ở Nam Mỹ.

### Gợi ý 2

Shared responsibility: càng "managed" thì nhà cung cấp lo càng nhiều tầng dưới, nhưng code, quyền IAM, cấu hình dữ liệu luôn là của bạn.
Chi phí: thứ tính tiền theo giờ dù không dùng (NAT, máy chạy cả đêm) và thứ giữ mãi (log, snapshot) là nơi tiền rò rỉ.
