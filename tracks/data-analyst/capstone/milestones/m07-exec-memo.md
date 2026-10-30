# M07: Memo và thuyết trình cho ban điều hành

## Mục tiêu

Gói sáu milestone thành thứ ban điều hành dùng được trong một cuộc họp 15 phút: **một trang memo** và
**5 slide**, trả lời ba câu hỏi xuyên suốt của capstone (doanh thu đến từ đâu, khách hàng nào tạo ra nó,
marketing có hiệu quả không), mỗi khuyến nghị có số, có người làm, có cách đo, và nêu rõ điều chưa biết.
Kèm README portfolio hoàn chỉnh để nhà tuyển dụng đọc trong năm phút.

Kiến thức: module 15 (`15-stakeholder-storytelling-interview`, các chủ đề Scoping, Storytelling, Memo,
AI-assisted Analysis, Case Interview, Portfolio). Đã gặp ở các module trước:
`modules/01-analyst-mindset/exercises/advanced/01-vague-request-analysis-plan` (đóng khung câu hỏi),
`modules/03-sql-for-analysts/exercises/advanced/01-ceo-three-questions` (memo ngắn từ SQL),
`modules/12-product-customer-analytics/exercises/advanced/01-segment-winback-memo` (memo từ phân khúc).

**Kỳ vọng trung thực.** Capstone này có nhiều phát hiện "không như mong đợi": tăng trưởng đầu kỳ là do
nạp panel, repeat vs one-time vô nghĩa, cohort phẳng, 801 hộ có nhân khẩu học tiêu nhiều gấp ba hộ còn
lại, và campaign không cho kết luận nhân quả. Memo tốt **nói thẳng** những điều này bằng một câu mỗi điều
và biến chúng thành hành động (sửa định nghĩa metric, thu thêm dữ liệu, chạy holdout), thay vì giấu đi.

## Việc cần làm

1. **`reports/NUMBERS.md`**: bảng nguồn mọi con số sẽ dùng: giá trị, đơn vị, định nghĩa (link
   `METRICS.md`), milestone và tệp SQL/notebook tạo ra nó. Memo và slide chỉ dùng số trong bảng này.
   Tối thiểu: quy mô doanh thu và cơ cấu ngành (M02), mức tập trung cửa hàng (M02), phân khúc RFM và số
   hộ win-back (M05), cặp cross-sell (M05), chênh lệch hộ được/không được gán campaign và kết quả DiD hai
   thang đo (M06).
2. **Chọn câu chuyện** trước khi viết: một câu "điều quan trọng nhất ban điều hành cần biết", rồi 3 ý đỡ
   cho nó (dạng pyramid: kết luận trước, bằng chứng sau). Ghi trong đầu `MEMO.md` dưới dạng tóm tắt một dòng.
3. **`reports/MEMO.md`** (400–700 từ) gửi Giám đốc kinh doanh và trưởng nhóm marketing:
   - "Khuyến nghị" ở đầu: 2–3 hành động, mỗi hành động có ai làm, khi nào, chi phí hoặc nguồn lực, metric đo.
     Ít nhất một hành động là **thí nghiệm có holdout** cho campaign kế tiếp (từ M06).
   - "Điều đã biết": 3–5 phát hiện có số.
   - "Điều chưa biết và cách biết": tác động thật của campaign, tính đại diện của nhóm có nhân khẩu học,
     dữ liệu ngoài panel thẻ khách hàng.
   - "Giả định và giới hạn": `DAY` không phải ngày lịch, panel 2 500 hộ, định nghĩa doanh thu đã kiểm trên
     dữ liệu nhưng chưa có tài liệu chính thức.
   - Không dùng thuật ngữ thống kê không giải thích (p-value, lift, DiD) trong phần khuyến nghị; nếu cần, nói
     bằng lời ("trong 100 giỏ có mì Ý, khoảng 46 giỏ có sốt mì Ý").
4. **5 slide** (`reports/slides.pdf` hoặc `.pptx`/Google Slides xuất PDF): (1) câu trả lời một dòng,
   (2) doanh thu đến từ đâu, (3) khách hàng nào, (4) marketing: điều thấy được và điều chưa chứng minh,
   (5) đề xuất và việc cần duyệt. Mỗi slide có tiêu đề là một câu kết luận (action title), tối đa một biểu
   đồ chính, nguồn số ở chân slide.
5. **Chuẩn bị hỏi đáp**: viết sẵn câu trả lời 2–3 câu cho ít nhất 5 câu hỏi khó trong
   `reports/QA_PREP.md`, ví dụ "Vậy campaign có hiệu quả hay không?", "Sao không nhắm luôn nhóm thu nhập
   cao?", "Doanh thu tăng gấp 7 lần trong năm tháng đầu là tin tốt chứ?", "Cửa hàng 367 có phải cửa hàng
   tốt nhất?", "Bao lâu thì có kết quả thí nghiệm?".
6. **Dùng AI có kiểm soát** (chủ đề AI-assisted Analysis của module 15): nếu dùng LLM để viết nháp memo
   hoặc gợi ý câu hỏi khó, ghi lại trong `QA_PREP.md` bạn dùng vào việc gì và đã kiểm mọi con số đối với
   `NUMBERS.md` ra sao.
7. **README portfolio** (`project/README.md`): khuyến nghị cuối ở đầu trang, ảnh dashboard, bảng con số
   chính có link, quyết định quan trọng (định nghĩa doanh thu, lọc xăng, ngưỡng cửa hàng, cách đọc
   campaign), giới hạn, cách chạy lại từ đầu.
8. **Trình bày thử** 5 phút (tuỳ chọn ghi hình) cho một người không biết dữ liệu; ghi lại câu hỏi họ hỏi
   mà bạn chưa chuẩn bị và sửa memo.

## Kết quả nộp

- `project/reports/NUMBERS.md`, `project/reports/MEMO.md`, `project/reports/QA_PREP.md`.
- `project/reports/slides.pdf` (5 slide).
- `project/README.md` hoàn chỉnh.

## Tiêu chí đạt

- [ ] Mọi số trong memo và slide có trong `NUMBERS.md`, truy được về SQL/notebook chạy lại được.
- [ ] Memo mở đầu bằng khuyến nghị có người làm, thời hạn, metric; dài 400–700 từ.
- [ ] Phần campaign nói rõ không kết luận nhân quả và đề xuất thí nghiệm có holdout.
- [ ] Các phát hiện "không như mong đợi" (nạp panel, cohort phẳng, chênh lệch nhóm có nhân khẩu học) được nêu bằng lời dễ hiểu.
- [ ] 5 slide có action title, một biểu đồ chính mỗi slide, nguồn số.
- [ ] Có ít nhất 5 câu hỏi khó và câu trả lời chuẩn bị sẵn.
- [ ] README portfolio cho người lạ chạy lại dự án từ đầu.
