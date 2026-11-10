# Lời giải: nền tảng feature cho 3 model

Bài Advanced không có đáp án duy nhất. `DESIGN.md` cạnh tệp này là một bản mẫu đã chạy qua test; chấm theo chất lượng lập luận.

## Các quyết định cốt lõi

- **Một nơi tính, nhiều nơi đọc.** Skew sinh ra khi cùng feature có hai bản cài đặt; thiết kế tốt có một job tính, offline store là
  nguồn sự thật, online store chỉ là bản sao qua materialize. Ba đội đọc cùng định nghĩa.
- **Chỉ đưa lên online cái cần online.** Feature của model gian lận (theo lô) ở lại offline; giảm kích thước Redis và số thứ phải
  giám sát.
- **Trung thực về feature 5 phút.** Job theo giờ không đáp ứng; câu trả lời có thể là streaming, hoặc tính ở dịch vụ, hoặc nới độ
  tươi. Bản tốt nêu lựa chọn và điều kiện chuyển, bản yếu giả vờ lô theo giờ giải được.
- **Parity là kiểm tra chạy được, không là mong muốn.** Mẫu thực thể mỗi đêm, so online với offline, chặn promotion.
- **TTL và backfill có lý do.** TTL tính theo chu kỳ cập nhật; backfill thực hiện offline trước rồi materialize, và tập train ghi
  phiên bản feature để tái lập.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Bám sát yêu cầu đề | 20 | Mỗi quyết định truy về độ tươi, đội 2 người, lô theo giờ, hạ tầng sẵn có |
| Kiến trúc một nguồn tính | 15 | Không có đường ghi online riêng; registry trong Git, thay đổi qua CI |
| Danh mục feature | 15 | Mỗi feature có nguồn, độ tươi và lý do online/offline hợp lý |
| Chống skew | 20 | Point-in-time có test, parity đo được với ngưỡng, default khai báo một chỗ, phiên bản feature |
| Vận hành | 15 | Lịch materialize, TTL có công thức, backfill, Redis (persistence, bộ nhớ), staging |
| Rủi ro và điều kiện thoát | 15 | Redis chết, feature 5 phút, ngưỡng đo được để chuyển sang Tecton/Hopsworks hay streaming |

Lỗi hay gặp: đưa mọi feature lên online; quên rằng online store là điểm sự cố mới của dịch vụ; materialize không có cảnh báo trễ.
