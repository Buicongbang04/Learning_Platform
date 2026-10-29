# Báo cáo: chọn solver cho hồi quy phí ship

Người đọc: tech lead của team ML, biết linear algebra cơ bản, cần một khuyến nghị dùng được ngay.
Tối đa hai trang. Xoá mọi dòng TODO khi viết xong.

## Tóm tắt

TODO: 3–5 câu: khi nào normal equation đủ dùng, khi nào phải đổi solver, khi nào phải sửa feature.

## Thí nghiệm có kiểm soát

TODO: Vandermonde (hoặc bài toán bạn tự dựng) với condition number tăng dần: sai số của normal
equation, QR, SVD. Bảng hoặc biểu đồ, kèm giải thích vì sao sai số normal equation tỉ lệ với κ².

## Olist: đơn vị đo và feature đa thức

TODO: condition number của [1, gram, cm³, gram², cm⁶, gram·cm³] trước và sau khi chuẩn hoá cột;
normal equation có thật sự sai không? Vì sao?

## Olist: thêm "peso cubado"

TODO: thêm cột khối lượng quy đổi (dài × rộng × cao / 6000) cạnh thể tích. Mỗi solver trả gì? Dự
đoán có đổi không? Hệ số có còn diễn giải được không? Bạn phát hiện việc này thế nào trong pipeline?

## Ridge

TODO: ridge làm gì với condition number và với hệ số; chọn lambda thế nào; đánh đổi.

## Khuyến nghị

TODO: quy tắc cho team (chuẩn hoá, solver mặc định, kiểm tra tự động trong pipeline).
