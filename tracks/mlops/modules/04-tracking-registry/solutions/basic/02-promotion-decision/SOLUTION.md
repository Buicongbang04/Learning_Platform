# Lời giải: decide_promotion

Mã nằm trong `promotion.py` cạnh tệp này.

## Vì sao ba cổng, không phải một con số

MAE tổng là trung bình có trọng số theo lượng chuyến. Với taxi, chuyến ngắn trong thành phố chiếm đa số, nên một model có
thể giỏi hơn ở 80% chuyến dễ và tệ hơn ở sân bay (ít chuyến, nhưng giá trị cao và khách phàn nàn nhiều nhất) mà MAE tổng
vẫn giảm. Cổng slice bắt đúng ca đó. Cổng latency tồn tại vì model nặng hơn 3 lần có thể đúng hơn 0.5% nhưng làm hỏng SLO.

## Các quyết định

- **`min_slice_n`.** Slice 50 chuyến cho MAE dao động tới mức "xấu đi 100%" chỉ do nhiễu. Bỏ qua slice nhỏ để cổng không
  chặn oan; đổi lại, slice hiếm nhưng quan trọng (vd. chuyến liên bang) cần được gộp lại thành slice đủ lớn ở bước đánh giá.
- **Slice thiếu là trượt.** Im lặng bỏ qua khiến người train "tránh" cổng bằng cách xoá slice khỏi báo cáo.
- **Dung sai tương đối, không tuyệt đối.** 5% của slice MAE 90 s (4.5 s) và của slice MAE 400 s (20 s) là hai mức ý nghĩa
  khác nhau về tuyệt đối nhưng cùng mức về trải nghiệm.
- **Epsilon ở ca biên.** `0.05000000000000004 > 0.05` làm ca "đúng bằng dung sai" bị từ chối sai. Policy nói "đúng bằng
  thì qua" thì code phải đúng như vậy.
- **Không bao giờ promote khi dữ liệu không hợp lệ.** `nan > 5` là `False`; một cổng viết kiểu "trượt nếu x > ngưỡng"
  cho NaN đi qua. Kiểm `isfinite` trước.
- **Trả `reasons` cho mọi cổng trượt.** Người đọc quyết định (hoặc log CI) cần biết hết việc phải sửa, không phải vá từng lỗi
  một sau mỗi lần chạy lại. Bài trung cấp 03 ghi chính `reasons` này vào registry.

## Lỗi hay gặp

- So `challenger_mae < champion_mae` rồi gọi là xong: mọi cải thiện 0.01% do nhiễu đều thành "promote", registry đầy version
  vô nghĩa.
- Dùng cải thiện tuyệt đối với metric đổi thang đo giữa các phiên bản dữ liệu.
- Chỉ kiểm slice của challenger: slice quan trọng của champion mà challenger không báo cáo thì không bao giờ bị phát hiện.
