---
title: Viết postmortem không đổ lỗi theo mẫu
level: basic
services: []
files:
  - path: starter/postmortem.md
    note: Mẫu postmortem, điền mọi TODO
  - path: tests/fixtures/postmortem.bad.md
    note: Ví dụ postmortem đổ lỗi, test dùng để kiểm bộ kiểm tra
  - path: tests/test_postmortem.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/basic/03-blameless-postmortem -q
---

## Mục tiêu

Chuyển một câu chuyện sự cố lộn xộn (có tên người, có lời trách) thành postmortem không đổ lỗi: dòng thời gian bằng vai trò,
tác động có số, nguyên nhân là chỗ hệ thống thiếu, và hành động có chủ, có hạn, có cách kiểm.

## Đề bài

Ghi chép thô của buổi chiều 2026-10-21 (giữ nguyên lời người kể):

- 13:58: Khải (đội nền tảng) xoay vòng credential của object store theo lịch quý, theo danh sách secret trên wiki. Secret của job
  materialize feature `trip_stats` không có trong danh sách.
- 14:05: job materialize `trip_stats` nhận 403, retry 3 lần, đánh dấu `skipped` rồi thoát mã 0. Orchestrator hiện xanh. Service ETA
  tiếp tục đọc giá trị cuối cùng trong online store, không kiểm tuổi feature.
- 15:30: dashboard MAE (nhãn về trễ 1 giờ) bắt đầu đi lên. Không có alert trên MAE.
- 16:40: ticket hỗ trợ "tài xế báo ETA sai ở Manhattan". Quyên (on-call) nhận. "Khải đáng lẽ phải kiểm job trước khi đổi khoá."
- 16:52: Quyên thấy log 403, tuyên bố sự cố SEV3, tự nhận incident commander; Thịnh nhận việc cập nhật kênh sự cố.
- 17:05: Khải cập nhật secret cho job, job chạy lại. 17:15: `trip_stats` tươi trở lại. 18:30: MAE trên nhãn mới về trở lại 3.1 phút.

Số liệu: 412 000 dự đoán dùng feature cũ; MAE tăng từ 3.1 lên 4.6 phút; SLO freshness là 99% thời gian feature không cũ hơn 15 phút
trong 30 ngày. SLO khả dụng và độ trễ xanh suốt sự cố.

Điền `starter/postmortem.md`, giữ các heading `## 1.` tới `## 6.`, không còn chữ `TODO`. Luật mà test kiểm:

| Phần | Yêu cầu |
| --- | --- |
| Toàn văn | Không có tên `Khải`, `Quyên`, `Thịnh` (dùng vai trò); không có các cụm `lỗi của`, `cẩu thả`, `bất cẩn`, `đáng lẽ`, `cẩn thận hơn`, `chú ý hơn`, `theo dõi sát hơn` (không hoa thường) |
| 1. Tóm tắt | Ít nhất 150 ký tự (không tính bảng) |
| 2. Tác động | Ít nhất 3 con số, trong đó có phần trăm error budget freshness 30 ngày đã tiêu (dạng `NN%`, tự tính; test nhận 43-45%). Thời gian tính vào budget là từ mốc bắt đầu tác động tới mốc hết tác động trong dòng thời gian (14:05 tới 17:15), không trừ khoảng 15 phút đầu khi feature chưa vượt ngưỡng |
| 3. Dòng thời gian | Bảng có cột `Thời điểm`, `Sự kiện`; ít nhất 6 mốc dạng `HH:MM`, theo thứ tự tăng dần, có mốc bắt đầu tác động `14:05` và mốc hết tác động `17:15`; mỗi mốc có mô tả |
| 4. Nguyên nhân gốc và yếu tố góp phần | Ít nhất 3 gạch đầu dòng |
| 5. Điều đã tốt, điều may mắn | Ít nhất 2 gạch đầu dòng |
| 6. Hành động | Bảng có cột `Hành động`, `Loại`, `Chủ sở hữu`, `Hạn`, `Cách kiểm`; ít nhất 4 dòng, không ô trống; `Loại` chỉ là `ngăn chặn`, `phát hiện` hoặc `giảm thiệt hại` và có đủ cả ba; `Hạn` dạng `YYYY-MM-DD` |

Test thứ hai đưa một postmortem đổ lỗi (`tests/fixtures/postmortem.bad.md`) vào cùng bộ kiểm tra và đòi nó bị bắt.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/18-senior-system-design/exercises/basic/03-blameless-postmortem -q` pass.
- Nguyên nhân gốc của bạn là một chỗ hệ thống thiếu cơ chế, không phải "người đổi khoá không kiểm".
- Mỗi hành động trả lời được: nếu sự cố giống hệt xảy ra lại, hành động này làm nó không xảy ra, được phát hiện sớm hơn, hay nhẹ hơn?

## Gợi ý

### Gợi ý 1

Budget freshness 30 ngày ở SLO 99% là `1% x 43 200 = 432` phút. Tác động kéo dài từ 14:05 tới 17:15.

### Gợi ý 2

Với mỗi câu có tên người, hỏi "hệ thống nào đã để việc này xảy ra mà không ai biết?": danh sách secret ghi tay, job thoát mã 0 khi lỗi
quyền, không có SLI freshness, service không kiểm tuổi feature. Mỗi câu trả lời là một nguyên nhân và một hành động.
