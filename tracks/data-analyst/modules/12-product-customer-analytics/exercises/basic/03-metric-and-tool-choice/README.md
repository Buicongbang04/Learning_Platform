---
title: Chọn công cụ product analytics, loại retention và đọc nhanh LTV/CAC
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Luyện các quyết định đầu tiên khi nhận câu hỏi product/customer: dùng công cụ nào (product analytics tool, GA4,
CDP, warehouse, spreadsheet), đếm theo đơn vị nào, chọn loại retention nào, và tính nhẩm LTV, payback từ một bảng
số trước khi mở notebook.

## Đề bài

Bài này không có code. Làm 12 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới):

- 5 câu **tình huống → công cụ**: Amplitude/Mixpanel, PostHog, GA4, Segment/RudderStack, warehouse + SQL/dbt.
- 3 câu **tình huống → định nghĩa**: đơn vị đếm của funnel, loại retention (bracket, unbounded, N-day).
- 2 câu **tính nhẩm** LTV đơn giản và CAC payback trên số liệu **ví dụ giả định** ghi trong câu.
- 2 câu **đọc kết quả** RFM và market basket.

Trước mỗi câu chọn công cụ, trả lời bốn câu hỏi ở phần 7 của lý thuyết: ai dùng (PM tự làm hay DA), con số có phải
là số chính thức không, cần nối với dữ liệu nào khác (đơn hàng, chi phí, CRM), dữ liệu được phép nằm ở đâu.

Nộp xong, đọc lời giải: mỗi câu giải thích vì sao đáp án đúng và vì sao các phương án còn lại không hợp.

## Tiêu chí đạt

- Trả lời đúng ít nhất 10/12 câu.
- Với mỗi câu sai, nói lại được tiêu chí quyết định của tình huống đó.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Product analytics tool cho câu hỏi nhanh của PM, warehouse cho con số chính thức; GA4 cho nguồn traffic của
website; CDP không phải công cụ phân tích mà là đường ống thu và phân phối sự kiện. Nhịp mua của sản phẩm quyết định
loại retention.

### Gợi ý 2

LTV đơn giản bằng AOV nhân số đơn mỗi năm nhân biên, chia cho (1 trừ retention năm). Payback là tháng đầu tiên lợi
nhuận gộp **luỹ kế** đạt CAC; cộng dồn từng tháng, đừng chia trung bình.
