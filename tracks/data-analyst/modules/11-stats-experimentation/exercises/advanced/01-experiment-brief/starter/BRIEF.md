# TODO: tên thí nghiệm (ví dụ "Voucher 10% cho khách đang hoạt động, tháng 9/2011")

Gửi: Giám đốc kinh doanh, trưởng nhóm CRM. Từ: <tên bạn>. Dữ liệu: Online Retail II, giao dịch tới 09/12/2011.
Thí nghiệm là kịch bản giả định; mọi con số baseline lấy từ dữ liệu thật trong notebook. 400-1 000 từ. Xoá mọi
dòng TODO khi viết xong.

## Câu hỏi và quyết định

TODO: thí nghiệm giúp ra quyết định gì (gửi voucher cho mọi khách đang hoạt động hay không), ai quyết, giả thuyết
một câu (nếu ... thì ... vì ...).

## Đối tượng và chia nhóm

TODO: ai đủ điều kiện (định nghĩa "đang hoạt động", ngày bắt đầu), bao nhiêu khách, đơn vị chia nhóm, tỉ lệ chia,
cách chia (hash + salt), ai bị loại và vì sao.

## Metric chính và guardrail

TODO: một metric chính (định nghĩa chính xác: cửa sổ, cách xử lý đuôi dài, doanh thu gộp hay sau voucher), metric
phụ, guardrail có ngưỡng (biên lợi nhuận, huỷ đơn...). Baseline của từng metric.

## Sample size và thời lượng

TODO: baseline, MDE đạt được với số khách hiện có (cho cả metric tỉ lệ và metric doanh thu, có và không cắt đuôi),
so với mức hiệu ứng cần để hoà vốn; thời lượng (gửi một lần + cửa sổ đo) và ngày có kết quả.

## Kiểm tra trước khi đọc kết quả

TODO: những kiểm tra phải đạt trước khi ai được xem hiệu ứng: SRM (ngưỡng p), email gửi đủ, không peeking, A/A đã
chạy, dữ liệu đủ cửa sổ.

## Quy tắc quyết định

TODO: viết trước, theo khoảng tin cậy và MDE/ngưỡng hoà vốn: khi nào ship, không ship, chưa kết luận, điều tra.

## Readout chạy thử (A/A)

TODO: bảng readout chạy thử trên tháng 9/2011 thật (không ai nhận voucher) và điều nó cho thấy: tỉ lệ false
positive qua 200 lần A/A, chuyện gì xảy ra với doanh thu không cắt đuôi.

## Rủi ro và giới hạn

TODO: mùa vụ (tháng 9-11 là mùa cao điểm), lây nhiễm giữa nhóm (chia sẻ mã), hiệu ứng kéo cầu sớm (khách mua
sớm hơn chứ không mua thêm), giới hạn của dữ liệu.
