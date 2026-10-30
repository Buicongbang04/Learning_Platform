# Tracking plan: khối "Thường mua kèm" trên trang sản phẩm

Gửi: PM, team web, team data. Dữ liệu tham chiếu: luật mua kèm của bài Intermediate 02, phân khúc RFM của bài
Intermediate 01. 250-900 từ. Xoá mọi dòng TODO khi viết xong.

## Câu hỏi và metric

TODO: tính năng thành công nghĩa là gì: metric chính (một), metric phụ, guardrail. Mỗi metric có công thức từ sự kiện
trong `tracking_plan.yaml` (tử số, mẫu số, cửa sổ, đơn vị đếm).

## Sự kiện

TODO: bảng ngắn: sự kiện, trigger, gửi từ client hay server, vì sao cần. Giải thích các quyết định khó (impression
tính khi nào, thêm giỏ từ gợi ý được nhận diện thế nào, đơn hàng nối với gợi ý ra sao).

## Phân tích phân khúc

TODO: sau khi ra mắt, bạn sẽ tách kết quả theo phân khúc nào (RFM, khách mới/cũ, thiết bị, nhóm sản phẩm) và vì sao;
thuộc tính nào trong plan cho phép tách như vậy. Nêu một kết quả phân khúc có thể làm đổi quyết định.

## QA trước khi ra mắt

TODO: kiểm log staging bằng `validate_events.py` thế nào, ngưỡng nào thì chặn ra mắt, ai sửa, kiểm lại khi nào.

## Rủi ro và quyền riêng tư

TODO: dữ liệu cá nhân, bot, sự kiện trùng, đổi định nghĩa sau ra mắt (version), chi phí lượng sự kiện.
