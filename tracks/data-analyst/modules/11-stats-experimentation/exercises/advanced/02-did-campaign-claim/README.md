---
title: Kiểm tra claim "chiến dịch ở Đức tăng 68% khách" bằng difference-in-differences
level: advanced
services: []
files:
  - path: starter/did_claim.ipynb
    note: 3 hàm TODO + DiD, placebo, xu hướng trước trên dữ liệu thật
  - path: starter/MEMO.md
    note: Memo một trang cho Giám đốc marketing
  - path: tests/test_did_claim.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/11-stats-experimentation/exercises/advanced/02-did-campaign-claim/starter/did_claim.ipynb
  - uv run pytest tracks/data-analyst/modules/11-stats-experimentation/exercises/advanced/02-did-campaign-claim -q
---

## Mục tiêu

Khi không có A/B test, trả lời câu "chiến dịch có tác dụng không" một cách trung thực: dựng nhóm đối chứng,
ước lượng difference-in-differences có khoảng tin cậy, kiểm giả định xu hướng song song và chạy placebo để biết
phương pháp "nhiễu" cỡ nào, rồi viết memo nói rõ điều dữ liệu trả lời được và không trả lời được.

## Đề bài

Agency báo cáo: quảng cáo nhắm khách Đức từ 1/9/2011 làm số khách Đức mua hàng mỗi tuần tăng 68% (12 tuần sau so
với 27 tuần trước), đề nghị tăng gấp đôi ngân sách. Chiến dịch và agency là **kịch bản giả định**; dữ liệu
`online-retail-ii` là thật và không có chiến dịch nào được ghi lại. Mở `starter/did_claim.ipynb`:

1. `weekly_active(lines, groups, start, end)`: số khách khác nhau mỗi tuần của từng nhóm nước.
2. `did_table(weekly, treated, control, cutoff)`: DiD 2×2 trên thang log.
3. `did_regression(weekly, treated, control, cutoff, maxlags)`: hồi quy khoảng cách log theo giai đoạn, sai số
   chuẩn HAC.
4. Chạy các cell `explore`: tái tạo con số 68%, chart chỉ số hoá hai nhóm, DiD, chart khoảng cách log, placebo
   mốc giả 1/6/2011 và cùng mùa năm 2010, độ dốc xu hướng trước. Viết `starter/MEMO.md`.

## Tiêu chí đạt

- Các hàm đúng trên dữ liệu nhỏ: đếm khách khác nhau theo tuần thứ Hai-Chủ nhật, bỏ nước ngoài nhóm và dòng
  ngoài `[start, end)`, điền 0, giữ thứ tự nhóm; DiD trên log; hồi quy khớp statsmodels (HAC).
- Trên bộ thật: 39 tuần, 304 lượt khách-tuần ở Đức và 763 ở nhóm đối chứng; Đức +68.1%, đối chứng +56.5%, DiD
  2×2 **+7.4%**; hồi quy +10.5%, khoảng tin cậy 95% trên thang log [−0.065; +0.265], p = 0.24; placebo năm 2010
  cho DiD −13.6% dù không có chiến dịch.
- `MEMO.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Trước khi tính DiD, nhìn chart chỉ số hoá: nếu nhóm đối chứng cũng tăng gần như vậy cùng lúc, phần lớn "hiệu ứng"
là mùa vụ. Rồi hỏi: nếu áp đúng quy trình này vào nơi chắc chắn không có chiến dịch (mốc giả, năm trước), con số
ra lớn cỡ nào? Đó là thước đo nhiễu thực tế của phương pháp, thường trung thực hơn khoảng tin cậy.

### Gợi ý 2

"Không có ý nghĩa thống kê" ở đây không có nghĩa "chiến dịch vô dụng": với khoảng 6 khách Đức mỗi tuần, cách đo
này chỉ phát hiện được hiệu ứng rất lớn. Memo tốt nói rõ cả hai điều, và đề xuất cách để lần sau đo được (chọn
ngẫu nhiên vùng chạy quảng cáo, giữ holdout).
