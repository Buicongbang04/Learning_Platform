---
title: Đánh giá khoảng cách vận hành cho dự án ShipFast ETA
level: advanced
services: []
files:
  - path: starter/ASSESSMENT.md
    note: Khung đánh giá, điền mọi TODO
  - path: tests/fixtures/project-brief.md
    note: Mô tả dự án, đọc trước
  - path: tests/test_assessment.py
    note: Không sửa; kiểm khung và vài ràng buộc cơ học
run:
  - uv run pytest tracks/mlops/modules/00-introduction/exercises/advanced/01-ops-gap-assessment -q
---

## Mục tiêu

Nhìn một dự án ML đang chạy "tạm được" và viết bản đánh giá khoảng cách vận hành mà người ra quyết định đọc xong biết
nên làm gì trước, cố ý chưa làm gì, và vì sao.

## Đề bài

Đọc `tests/fixtures/project-brief.md` (đội 6 người, model ETA đang chạy, một sự cố mất 5 ngày). Điền `starter/ASSESSMENT.md`:

1. **Tóm tắt và mức trưởng thành**: mức theo Google (test kiểm bạn kết luận hệ thống này đang ở mức 0, viết dạng "mức 0" hoặc "level 0"), điều quyết định mức đó, rủi ro lớn nhất.
2. **Bảng khoảng cách**: ít nhất 7 dòng, phủ ít nhất 6 khu vực (`data, training, versioning, serving, monitoring, ci-cd,
   security, rollback`). Mỗi dòng có hiện trạng kèm bằng chứng lấy từ đề, rủi ro, ưu tiên P0/P1/P2, việc đầu tiên, công cụ.
   Chỉ **1 tới 3** dòng được là P0.
3. **Cố ý chưa làm**: ít nhất hai thứ "chuẩn MLOps" bạn không đề xuất bây giờ, mỗi thứ kèm lý do với ngân sách 300 USD/tháng.
4. **Lộ trình 30/60/90 ngày**: mỗi mốc có việc cụ thể và tiêu chí hoàn thành quan sát được.
5. **Giả định và rủi ro của kế hoạch**: ít nhất hai.

Test chỉ kiểm cấu trúc; chất lượng lập luận chấm bằng rubric trong `solutions/.../SOLUTION.md` (xem sau khi tự chấm).

## Tiêu chí đạt

- `uv run pytest` xanh: đủ năm phần, đủ cột, ưu tiên hợp lệ, mốc 30/60/90.
- Tự chấm theo rubric đạt từ 14/20.
- Một người chưa biết dự án đọc phần 1 và 2 hiểu được thứ tự ưu tiên trong ba phút.

## Gợi ý

### Gợi ý 1

Bắt đầu từ sự cố trong đề: điều gì khiến nó kéo dài 5 ngày? Hai nguyên nhân đó thường là P0, vì chúng giảm thiệt hại ngay
mà không cần dựng pipeline.

### Gợi ý 2

Hỏi cho từng khoảng cách: rủi ro xảy ra thế nào, xác suất và thiệt hại, việc nhỏ nhất làm được trong vài ngày để giảm nó.
Tự động hoá training thường đẹp nhưng không giảm rủi ro nào ở đây trước phát hiện và quay lui.
