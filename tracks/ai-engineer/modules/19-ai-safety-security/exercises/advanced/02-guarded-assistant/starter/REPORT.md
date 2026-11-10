# Trợ lý CSKH Sao Mai có guardrail: báo cáo vận hành

TODO: viết theo khung trong README của bài (ít nhất 500 từ). Người đọc là trưởng nhóm vận hành và người phụ trách bảo
vệ dữ liệu: họ cần biết hệ thống chặn gì, chặn oan ai, để lọt gì, dữ liệu cá nhân đi tới đâu, và tốn bao nhiêu độ trễ.

## Tóm tắt

TODO: bảng loại tin nhắn x trạng thái thu gọn và ba con số: chặn oan, tấn công lọt qua, giá trị PII thô tới model.

## Thiết lập

TODO: các lớp theo thứ tự, model và prompt của moderator (tóm tắt chính sách), ngưỡng classifier, tham số rate limit và
cấm, allowlist link, phần cứng.

## Kết quả theo loại tin nhắn

TODO: bảng `traffic_report` đầy đủ và đọc bảng.

## Phân tích từng lỗi

TODO: mỗi tin bị xử lý sai một dòng: tin nhắn, trạng thái mong đợi, trạng thái thật, lớp quyết định, nguyên nhân, cách sửa.

## Dữ liệu cá nhân

TODO: số giá trị PII trong lưu lượng, số giá trị thô tới model, token có được model giữ nguyên và khôi phục đúng không
(ví dụ thật).

## Độ trễ

TODO: bảng `stage_latency` và đề xuất tối ưu.

## Quyết định vận hành và giới hạn

TODO: fail open hay fail closed từng lớp, ngưỡng cấm, log ghi gì, giới hạn của lần đo này.
