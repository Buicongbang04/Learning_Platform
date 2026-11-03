# Hướng làm và rubric: design doc ML realtime

Bài Advanced không có đáp án duy nhất. `DESIGN.md` cạnh tệp này là một bản mẫu cho đề fraud đã qua test; dùng để so cách lập luận,
không để chép.

## Hướng làm chung

1. **Yêu cầu trước kiến trúc.** Lưu lượng trung bình và đỉnh, ngân sách độ trễ (của riêng model, không phải cả luồng), tỉ lệ sự kiện
   hiếm, độ trễ nhãn, độ tươi feature cần, mục tiêu nghiệp vụ có số. "Ngoài phạm vi" chặn review trôi sang chuyện khác.
2. **SLO đo ở chỗ người dùng thấy** (bài sự cố Intermediate 03): khả dụng và độ trễ ở phía gọi, freshness theo tuổi feature của từng yêu
   cầu, chất lượng theo nhãn với cửa sổ khớp độ trễ nhãn (bài Intermediate 01).
3. **Ít nhất ba phương án**, gồm phương án đơn giản nhất và hiện trạng; nói vì sao bị loại bằng chi phí, độ trễ, chất lượng có số hoặc
   ước lượng. Một phương án được chọn.
4. **Ước tính back-of-envelope**: số replica ở đỉnh có dư cho mất một zone, kích thước online store, lưu lượng stream, log để join nhãn.
5. **Chế độ hỏng và fallback** cho từng thành phần trên đường nóng; fallback được test định kỳ.
6. **Rollout**: shadow, canary theo đơn vị nhất quán (tài khoản, thành phố), tiêu chí lên tầng viết trước, rollback không cần build.

## Điểm riêng của đề fraud

- Nhãn về rất trễ và **thiên lệch do chính model** (giao dịch bị chặn không bao giờ có nhãn chargeback): cần nhóm holdout hay khám phá có
  kiểm soát, và proxy sớm (OTP thất bại, khiếu nại, báo cáo 3 ngày).
- Chi phí bất đối xứng: chặn nhầm mất khách, lọt mất tiền; ngưỡng quyết định là quyết định nghiệp vụ có chủ.
- Luật cứng giữ quyền phủ quyết; thanh toán không bao giờ dừng vì hệ thống chống gian lận hỏng (fail-open có kiểm soát hoặc fallback luật).
- Feature cửa sổ ngắn theo event time, có watermark; tấn công diễn ra trong vài phút nên feature theo giờ là không đủ.

## Điểm riêng của đề eta

- Nhãn về nhanh (10-60 phút) nên SLO chất lượng có thể chặt hơn fraud; đo MAE theo thành phố và khung giờ, không chỉ trung bình.
- Feature tốc độ theo đoạn đường là dữ liệu streaming; freshness và việc xử lý đoạn không có xe (thiếu dữ liệu ban đêm) là trung tâm.
- Mưa và giờ cao điểm là slice có sai số gấp đôi: SLO hay ít nhất dashboard theo slice; cân nhắc feature thời tiết và retrain theo ngày.
- Thêm thành phố thứ tư: cold start (dữ liệu ít), model chung có feature thành phố hay model riêng, cách rollout theo thành phố.
- Fallback: ETA theo khoảng cách và tốc độ trung bình lịch sử khi model hay feature lỗi; app luôn có một con số.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Yêu cầu có số và ngoài phạm vi | 10 | Đủ lưu lượng đỉnh, độ trễ, độ trễ nhãn, độ tươi, mục tiêu nghiệp vụ; ngoài phạm vi rõ |
| SLO | 15 | Đo ở phía gọi; có chất lượng với cửa sổ hợp độ trễ nhãn; có freshness; mục tiêu có lý do |
| Kiến trúc | 15 | Tách đường online và offline; log quyết định để join nhãn; feature streaming và batch đúng chỗ; sơ đồ khớp lời |
| Phương án và đánh đổi | 15 | Có hiện trạng và phương án đơn giản; lý do loại bằng số; nêu được cái giá của phương án chọn |
| Ước tính | 10 | Replica ở đỉnh có dư, kích thước store, stream, log; số truy về yêu cầu |
| Chế độ hỏng | 15 | Mỗi thành phần trên đường nóng có phát hiện và giảm thiểu; fallback không chặn luồng nghiệp vụ; có feedback loop (fraud) hoặc slice thời tiết (eta) |
| Rollout | 10 | Shadow, canary theo đơn vị nhất quán, tiêu chí viết trước, rollback nhanh |
| Câu hỏi review | 10 | Câu hỏi thật sự mở (ngưỡng, ai trực, giải thích, chi phí), không phải câu hỏi tu từ |

Trừ điểm: SLO chỉ đo ở hàm model hoặc dùng CPU (-10); không có fallback trên đường nóng (-10); "dùng deep learning cho chính xác" không
có số so với baseline (-5). Dưới 70 thường vì thiếu phần 5 hay phần 6: doc đẹp nhưng không chịu được câu hỏi "ở đỉnh thì sao" và "nó chết
thì sao".
