# Lời giải: postmortem không đổ lỗi

`postmortem.md` cạnh tệp này là bản mẫu đã qua test. Cấu trúc do máy kiểm; chất lượng tự chấm theo các ý dưới.

## Ý chính

- **Vai trò, không phải tên.** "Kỹ sư nền tảng xoay vòng credential theo lịch" mô tả việc bình thường mà ai ở vị trí đó cũng làm.
  "Khải đổi khoá" biến postmortem thành phiên toà, và lần sau người ta giấu thông tin để không bị nêu tên.
- **Tác động có số, kể cả số không xấu.** 190 phút, 412 000 dự đoán, MAE +48%, 44% budget freshness (190/432). Ghi cả "SLO khả dụng
  xanh suốt sự cố": đó là phát hiện quan trọng nhất, SLO đang đo sai thứ người dùng thấy.
- **Nguyên nhân là cơ chế thiếu.** Danh sách secret ghi tay, job nuốt lỗi 403, không có SLI freshness, service không kiểm tuổi feature,
  MAE không có alert. Không có mắt xích nào là "người không cẩn thận"; mỗi mắt xích sửa được bằng một thay đổi hệ thống.
- **Ba loại hành động.** Ngăn chặn (sinh danh sách secret tự động, job fail khi 4xx), phát hiện (alert freshness, alert chất lượng),
  giảm thiệt hại (fallback khi feature quá cũ). Thiếu một loại là còn một hướng sự cố quay lại nguyên vẹn.
- **Hành động kiểm được.** "Cẩn thận hơn khi đổi khoá" không có chủ, hạn hay cách biết đã xong. "Test tích hợp với object store trả
  403 làm job fail" thì có.

## Tự chấm (20 điểm)

| Mục | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Tóm tắt | 3 | người ngoài hiểu chuyện gì, tác động, trạng thái hiện tại |
| Tác động | 4 | có số, có % budget đúng, nêu SLO khả dụng vẫn xanh |
| Dòng thời gian | 3 | đủ mốc, vai trò, đánh dấu bắt đầu và hết tác động |
| Nguyên nhân | 5 | chuỗi cơ chế; có cả "vì sao không phát hiện sớm hơn" |
| Hành động | 5 | đủ ba loại, chủ là vai trò hay đội, hạn và cách kiểm cụ thể |

Mức đạt: 14/20.
