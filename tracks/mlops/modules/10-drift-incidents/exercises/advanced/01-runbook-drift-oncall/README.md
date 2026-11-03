---
title: Viết runbook cho cảnh báo drift của model ETA
level: advanced
services: []
files: []
run: []
---

## Mục tiêu

Biến khung detect, verify, impact, decide thành một runbook mà người trực lúc 3 giờ sáng, chưa từng thấy hệ thống này, làm theo được mà không đoán và không phản xạ "retrain".

## Đề bài

Bối cảnh: model ETA (dự đoán thời lượng chuyến) phục vụ qua API, phiên bản hiện tại và phiên bản trước đều lưu trong registry; nhãn (thời lượng thật) về sau 1 ngày; giám sát hằng ngày đo PSI từng feature,
tỉ lệ thiếu, phân phối dự đoán so với baseline cùng thứ, tỉ lệ fallback; MAE tính khi nhãn về. Cảnh báo `FeatureDriftHigh` bắn khi một feature có PSI từ 0.25 trở lên.

Viết `runbook-feature-drift.md` (tối đa 2 trang) gồm:

1. **Điều kiện kích hoạt và mức nghiêm trọng**: cảnh báo nào, ngưỡng nào, ai nhận, phải xác nhận trong bao lâu.
2. **Detect**: xác nhận tín hiệu không phải do chính giám sát (ngưỡng, mẫu nhỏ, baseline sai thứ).
3. **Verify**: danh sách kiểm có thứ tự để loại trừ lỗi dữ liệu và pipeline trước khi đụng tới model: thay đổi gần đây (deploy, nguồn, schema), tỉ lệ thiếu, khoảng giá trị, thứ tự thời gian, số cột bị chạm.
4. **Impact**: cách ước lượng chất lượng khi nhãn chưa về (proxy) và khi đã về (MAE theo lát cắt), kèm ngưỡng "xấu đi" có con số.
5. **Decide**: bảng quyết định cho `keep`, `rollback`, `retrain` (điều kiện, ai duyệt, cách thực hiện, cách kiểm sau đó). Nêu rõ khi nào **không** làm gì.
6. **Giao tiếp và leo thang**: mẫu cập nhật trạng thái, khi nào kéo thêm ai, khi nào khai báo sự cố.
7. **Sau sự cố**: việc phải làm trong 48 giờ (ticket, cập nhật ngưỡng, postmortem nếu đạt điều kiện).

Không có đáp án duy nhất. Tự chấm bằng rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Đủ bảy mục, mỗi mục có ít nhất một quyết định cụ thể (con số, tên vai trò, tên lệnh hoặc dashboard), không chỉ lời chung chung.
- Bước verify đứng **trước** bước quyết định hành động và có ít nhất bốn kiểm tra loại trừ lỗi dữ liệu.
- Có tình huống rõ ràng nói "giữ nguyên" và điều kiện để đổi ý.
- Có hành động cho trường hợp nhãn chưa về (chỉ có proxy) và hành động đó không phải "chờ".

## Gợi ý

### Gợi ý 1

Viết cho người đọc lúc nửa đêm: mỗi bước có một câu hỏi có/không và một hành động tiếp theo cho mỗi câu trả lời.

### Gợi ý 2

Mỗi ngưỡng trong runbook nên truy được về một con số đo trên dữ liệu bình thường (vd. bốn tuần gần nhất), không phải con số tròn tự nghĩ ra.
