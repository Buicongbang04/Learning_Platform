---
title: Win-back theo phân khúc RFM - kiểm phân khúc bằng 6 tháng sau đó và viết memo cho CRM
level: advanced
services: []
files:
  - path: starter/winback.ipynb
    note: 2 hàm TODO + phân tích tự do
  - path: starter/MEMO.md
    note: Memo 250-700 từ cho Head of CRM
  - path: tests/test_winback.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/12-product-customer-analytics/exercises/advanced/01-segment-winback-memo/starter/winback.ipynb
  - uv run pytest tracks/data-analyst/modules/12-product-customer-analytics/exercises/advanced/01-segment-winback-memo -q
---

## Mục tiêu

Biến một bảng phân khúc mô tả thành một quyết định chi ngân sách: chốt phân khúc ở một ngày trong quá khứ, đo mỗi
phân khúc thật sự làm gì sau đó, tách phân khúc theo giá trị, phát hiện con số bị một giao dịch quyết định, dựng bảng
kịch bản với giả định ghi rõ, và đề xuất thử nghiệm có nhóm đối chứng.

## Đề bài

Head of CRM có ngân sách cho **một** chiến dịch win-back và hỏi: **"Gửi cho nhóm nào thì đáng tiền?"**. Dữ liệu: bộ
`online-retail-ii` (UCI, CC BY 4.0), cả hai sheet, bỏ phần trùng 01-09/12/2010, dòng hợp lệ theo định nghĩa dùng
chung. Mở `starter/winback.ipynb`:

1. Phân khúc khách tại ngày chốt 01/06/2011 (gợi ý: RFM của bài Intermediate 01 trên 12 tháng trước ngày chốt; được
   thêm tách theo điểm M hoặc tự định nghĩa phân khúc, miễn là ghi rõ).
2. `segment_outcomes(sales, segments, start, end)`: với mỗi phân khúc, số khách, tỉ lệ có mua trong cửa sổ, doanh
   thu, doanh thu mỗi khách, tỉ trọng doanh thu. Chạy cho cửa sổ 01/06-10/12/2011.
3. `campaign_value(outcomes, uplift, margin, cost_per_customer)`: bảng kịch bản lợi nhuận gộp thêm, chi phí, net theo
   phân khúc; `uplift` là một số hoặc Series theo phân khúc. Mọi tham số là **giả định**.
4. Phân tích tự do: tỉ lệ quay lại theo phân khúc, tách nhóm at_risk theo giá trị, kiểm khách hoặc hoá đơn lớn nhất
   của mỗi phân khúc, vài kịch bản uplift khác nhau theo phân khúc (vì sao uplift của champions gần 0?).
5. Viết `starter/MEMO.md` theo khung có sẵn: headline có con số, phân khúc và bằng chứng, đề xuất, cách đo (nhóm đối
   chứng, metric chính, guardrail), giả định và giới hạn.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: cửa sổ nửa mở, chỉ khách có phân khúc, khách không mua vẫn tính vào mẫu số, uplift
  theo phân khúc (thiếu là 0), sắp theo net.
- `MEMO.md` không còn TODO, 250-700 từ, đủ mục, headline có con số, có chữ "giả định". Nội dung chấm theo rubric trong
  `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Đặt khung thời gian trước khi chạy: phân khúc chỉ dùng dữ liệu **trước** ngày chốt, kết quả chỉ dùng dữ liệu **sau**.
Dùng dữ liệu sau ngày chốt để chấm phân khúc là nhìn trước đáp án. Nửa cuối năm có mùa cao điểm: tỉ lệ quay lại sẽ
cao hơn một nửa năm bình thường, nói rõ trong memo.

### Gợi ý 2

Con số "doanh thu mỗi khách" của một phân khúc nhỏ dễ bị một khách quyết định: xem `nlargest` doanh thu theo khách
trong từng phân khúc trước khi viết. Uplift không đo được từ dữ liệu quá khứ: champions quay lại 95% dù không có
chiến dịch, nên uplift hợp lý gần 0; kịch bản tốt dùng uplift khác nhau theo phân khúc, và đề xuất thử nghiệm để đo.
