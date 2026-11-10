# Hướng làm và rubric: build vs buy cho nền tảng ML

Không có đáp án duy nhất; giá thay đổi, và cùng dữ kiện hai đội giỏi có thể chọn khác nhau. Rubric chấm cách lập luận.

## Hướng làm mẫu (tóm tắt)

**Ràng buộc cứng trước.** PCI DSS và dữ liệu theo vùng loại phương án nào không đáp ứng được (cả ba nền tảng managed lớn đều có vùng và
chứng nhận PCI DSS cho dịch vụ lõi; kiểm từng dịch vụ cụ thể, không mặc định). Đội ads cần bắt đầu trong tháng: phương án nào cần dựng
thêm nhiều tháng thì phải có đường tạm cho ads.

**Ma trận tiêu chí** (ví dụ trọng số): TCO 3 năm 30%, phù hợp ràng buộc và bảo mật 20%, thời gian tới giá trị 15%, năng lực đội để vận hành
15%, lock-in và khả năng rời đi 10%, độ phù hợp với stack dữ liệu 10%.

**TCO, cách tính.** Mỗi phương án = compute (theo mức dùng dự kiến, kể cả phí cộng thêm của managed trên giờ instance) + lưu trữ và egress +
giấy phép hay phí nền tảng + **người** (số FTE để vận hành, trực, nâng cấp, nhân lương) + chi phí di chuyển một lần + rủi ro (chi phí kỳ
vọng của sự cố, của rời đi). Ví dụ lập luận: phương án A giữ 3 FTE nền tảng bận vận hành (khoảng 45 000 USD/tháng chỉ riêng người, gần bằng
hoá đơn hạ tầng), nhưng compute rẻ nhất nếu đưa được mức dùng lên; phương án B, C giảm phần vận hành (có thể còn 1-1.5 FTE cho lớp riêng),
nhưng compute đắt hơn vài chục phần trăm trên mỗi giờ và có chi phí di chuyển; khi cụm chỉ chạy 30%, autoscale theo yêu cầu của managed có
thể bù phần phí cộng thêm. Kết luận phụ thuộc số thật, nên bài phải ghi giả định và làm phân tích độ nhạy (mức dùng 30% hay 60%, phí cộng
thêm 20% hay 40%).

**Một quyết định hợp lý thường là lai (D).** Huấn luyện theo đợt và notebook trên dịch vụ managed (GPU theo giờ cho search, không giữ node;
đội ads bắt đầu ngay); nếu đội dữ liệu chọn Databricks thì dùng luôn Unity Catalog cho quyền dữ liệu và model. Serving giữ trên Kubernetes
(đã có, độ trễ thấp, container chuẩn). Lớp riêng của công ty giữ nguyên: template, quy ước, cổng quét và ký, báo cáo chi phí, vì đó là
thứ không nhà cung cấp nào làm thay theo đúng quy ước của công ty.

**Giảm lock-in.** Model ở định dạng mở (safetensors, ONNX, định dạng gốc của LightGBM) với metadata riêng; serving là container chuẩn;
pipeline gọi SDK của hãng qua lớp mỏng nội bộ; dữ liệu ở định dạng mở (Parquet, Delta, Iceberg) trên object storage của mình; đo chi phí rời
đi mỗi năm.

**Điều kiện xem lại.** Mức dùng GPU vượt khoảng 60% liên tục (tự giữ GPU rẻ hơn thuê theo giờ); phí managed tăng quá một ngưỡng; đội nền
tảng tăng lên 6 người; một yêu cầu pháp lý mới (dữ liệu không được rời on-prem); nhà cung cấp bỏ một dịch vụ đang dùng.

## Rubric (100 điểm)

| Mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Ràng buộc cứng | 10 | PCI DSS, dữ liệu theo vùng và thời hạn của đội ads loại hoặc định hình phương án trước khi so điểm |
| Phương án | 10 | Đủ bốn phương án, mỗi phương án mô tả đủ cụ thể (dịch vụ nào cho lớp nào) |
| Ma trận có trọng số | 15 | Tiêu chí và trọng số có lý do; điểm từng ô có giải thích, không chỉ con số |
| TCO 3 năm | 25 | Có compute, lưu trữ, phí nền tảng, **người**, di chuyển; ghi giả định và ngày tra giá; có phân tích độ nhạy cho ít nhất một giả định lớn |
| Lock-in | 10 | Biện pháp cụ thể cho định dạng model, serving, dữ liệu, code pipeline; ước tính chi phí rời đi |
| Quyết định và di chuyển | 15 | Quyết định rõ (kể cả lai), thứ tự di chuyển theo lớp, đường tạm cho đội ads, rủi ro chuyển đổi |
| Điều kiện xem lại | 10 | Ít nhất ba điều kiện có số hoặc sự kiện cụ thể |
| Giới hạn | 5 | Nói rõ chỗ nào là giả định và cần dữ liệu thật (báo giá, đo mức dùng) |

Mức đạt 70. Trừ điểm: TCO chỉ có hoá đơn cloud, không có chi phí người (-15); chọn theo sở thích công cụ, không có tiêu chí (-10); không có
đường cho đội ads trong tháng này (-5).

## Câu đào sâu

- Nếu ban lãnh đạo hỏi "vậy tự xây thì tiết kiệm được bao nhiêu", câu trả lời của bạn có tính lương ba kỹ sư không?
- Databricks làm cả dữ liệu và ML: lợi ích tích hợp lớn tới mức nào thì đáng đổi lấy phụ thuộc sâu hơn?
- Hai năm sau giá tăng 30%: kế hoạch rời đi của bạn mất bao lâu, và phần nào khó rời nhất?
- Phương án lai có hai nơi để vận hành. Khi có sự cố serving lúc nửa đêm, ai trực phần nào?
