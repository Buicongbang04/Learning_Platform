---
title: Thiết kế nền tảng ML cho 5 đội - golden path, quyền, chi phí, chuỗi cung ứng model
level: advanced
services: []
files:
  - path: starter/PLATFORM.md
    note: Khung tài liệu thiết kế, điền từng phần
run: []
---

## Mục tiêu

Viết tài liệu thiết kế nền tảng ML cho một công ty có 5 đội model, ở mức mà một trưởng nhóm nền tảng mang ra design review: ai được làm
gì, đường đi chuẩn của một model từ ý tưởng tới production, ai trả tiền cho cái gì, và làm sao biết model đang chạy đúng là model đã duyệt.
Bài này ghép mọi bài trước của module thành một bức tranh, và luyện phần khó nhất của nền tảng: nói "không" có lý do và có lối thoát.

## Đề bài

Công ty gọi xe và giao hàng, 5 đội có model ở production:

| Đội | Model | Lưu lượng, nhịp | Đặc điểm |
| --- | --- | --- | --- |
| `eta` | ETA chuyến đi | 3 000 RPS đỉnh, p99 80 ms | LightGBM, retrain mỗi ngày, đội lâu đời, tự viết script deploy |
| `pricing` | giá động, gợi ý tiền tip | 800 RPS | sklearn, model lưu bằng pickle từ 2021 |
| `fraud` | gian lận thẻ | 400 RPS, p99 50 ms | feature streaming cửa sổ 1 phút, dữ liệu thẻ thuộc phạm vi PCI DSS |
| `search` | xếp hạng nhà hàng | 1 200 RPS | model PyTorch, huấn luyện GPU 6 giờ mỗi tuần, tải model gốc từ Hugging Face |
| `ads` | CTR quảng cáo | 2 000 RPS | đội mới 3 người, chưa có MLOps, muốn "tự làm cho nhanh" |

Hiện trạng: cụm Kubernetes dùng chung 40 node CPU và 8 GPU, chạy trung bình 30% công suất; MLflow registry chung nhưng mỗi đội đặt tên
một kiểu; không ai biết đội nào tốn bao nhiêu; năm ngoái có một sự cố model pickle lấy từ một notebook cá nhân lên production. Đội nền tảng
có 3 kỹ sư. Ban lãnh đạo muốn: giảm 25% chi phí hạ tầng ML trong 2 quý, thời gian từ "model mới" tới production dưới 2 tuần cho đội mới,
và vượt qua đợt audit bảo mật chuỗi cung ứng phần mềm cuối năm.

Điền `starter/PLATFORM.md` (tối đa 6 trang), mỗi quyết định có lý do và phương án đã loại. Không có test tự động: tự chấm bằng rubric trong
`SOLUTION.md`, tốt nhất nhờ một người đóng vai người review và hỏi các câu "đào sâu" ở đó.

## Tiêu chí đạt

- Đạt ít nhất 70/100 điểm rubric.
- Có lộ trình theo quý, mỗi bước có chỉ số đo được (không chỉ "triển khai X").
- Có ít nhất một chỗ nói rõ đội nào được **ngoại lệ** khỏi golden path, ngoại lệ có hạn và có điều kiện thoát.
- Có phần "giới hạn": chỗ nào là giả định, chỗ nào cần dữ liệu hay kinh nghiệm vận hành mà bạn chưa có.

## Gợi ý

### Gợi ý 1

Bắt đầu từ ba câu hỏi, không từ công cụ: ai được đăng ký và deploy model nào (quyền), model nào được phép chạy (chuỗi cung ứng), ai trả
tiền (FinOps). Golden path là cách làm cho câu trả lời đúng trở thành đường dễ nhất.

### Gợi ý 2

Với 3 kỹ sư nền tảng, mọi thứ bạn tự xây là thứ bạn phải trực. Đánh dấu rõ phần nào mua hay dùng dịch vụ có sẵn (bài Advanced 02), phần
nào là "lớp mỏng" của riêng công ty (quy ước, cổng, template).
