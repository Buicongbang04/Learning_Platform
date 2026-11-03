# Lời giải: alert theo triệu chứng, kiểm bằng promtool

## Ý chính

- **Tỉ lệ, không phải số tuyệt đối.** 50 lỗi/phút là thảm hoạ lúc 100 yêu cầu/phút và là nhiễu lúc 100 000. Chia lỗi cho tổng
  cho một ngưỡng có nghĩa cho người dùng.
- **Không traffic thì không alert lỗi.** Khi mẫu số bằng 0 phép chia cho ra `NaN`, và `NaN > 0.05` là sai nên alert im lặng. Đó
  là hành vi đúng: "không có yêu cầu" không phải "100% lỗi". Hai cách sai hay gặp: thêm `or vector(0)` cho "có số" (biến "không có dữ liệu" thành 0 mà không ai hỏi vì sao), hoặc đổi sang số lỗi tuyệt đối.
- **Không traffic là vấn đề của alert khác.** Service chết thì mất cả tử lẫn mẫu: đó là việc của `absent()` (hoặc `up == 0`).
  Mỗi mode hỏng cần một alert phụ trách, đừng cố nhét tất cả vào một biểu thức.
- **`for` loại nhiễu.** 5 phút nghĩa là một đợt lỗi thoáng qua không đánh thức ai. Đánh đổi: `for` dài thì phát hiện chậm, nên
  alert "cháy nhanh" thực tế dùng hai cửa sổ (bài Advanced 01).
- **Mỗi alert có `runbook_url` và `severity`.** Người bị đánh thức lúc 3 giờ sáng cần biết ngay làm gì; `severity` quyết định
  alert đi đâu (bài Intermediate 02).
- **Test chạy trong CI.** `promtool test rules` biến một rule YAML thành thứ có thể hồi quy: rule đổi ngưỡng hay selector mà
  làm hỏng một kịch bản thì CI báo ngay.

## Lỗi hay gặp

- Lọc `status="500"` thay vì `status=~"5.."`: bỏ lọt 502, 503, 504.
- `rate` với cửa sổ nhỏ hơn 4 lần khoảng scrape (15 giây thì ít nhất `1m`) cho kết quả nhảy.
- `sum(rate(...)) by (route)` ở cả tử và mẫu rồi so sánh: nhiều alert con thay vì một alert tổng; chọn có chủ ý.
