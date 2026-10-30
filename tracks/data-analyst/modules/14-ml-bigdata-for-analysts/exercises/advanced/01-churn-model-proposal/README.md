---
title: Đề xuất model churn cho COO - giá trị so với quy tắc, ngân sách gọi, giả định và pilot
level: advanced
services: []
files:
  - path: starter/churn_proposal.ipynb
    note: 1 hàm TODO + phân tích tự do (ngân sách, độ nhạy, pilot)
  - path: starter/PROPOSAL.md
    note: Đề xuất một trang cho COO - đề xuất, model làm được gì, giá trị (giả định), rủi ro, pilot
  - path: tests/test_churn_proposal.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py telco-churn
  - uv run jupyter lab tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/advanced/01-churn-model-proposal/starter/churn_proposal.ipynb
  - uv run pytest tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/advanced/01-churn-model-proposal -q
---

## Mục tiêu

Đưa ra quyết định "có dùng model không" như một DA senior: quy kết quả model ra số cuộc gọi trúng và tiền, so với quy
tắc đang dùng và với gọi ngẫu nhiên ở cùng ngân sách, nói rõ kết luận đứng trên giả định nào, và đề xuất một pilot có
nhóm đối chứng để đo tác động thật.

## Đề bài

COO nhận hai đề xuất: giữ quy tắc gọi giữ chân (month-to-month, gắn bó tối đa 12 tháng) hay thay bằng model churn. Bạn
là DA trung lập. Dữ liệu: bộ `telco-churn` (7 043 khách); model ứng viên (logistic regression, 10 đặc trưng) và cách chia
train/test đã dựng sẵn trong `starter/churn_proposal.ipynb`. Các con số tiền là **ví dụ giả định** do bạn đặt và phải ghi rõ.

1. Viết `campaign_table(y_true, score, budgets, contact_cost, value_per_save, save_rate)`: với mỗi số khách liên hệ `k`,
   số khách rời trong top-k, `capture`, `precision`, số khách giữ được kỳ vọng, chi phí, giá trị, `net`, `net` khi chọn
   ngẫu nhiên và phần chênh (bảng cột trong notebook). `ValueError` khi đầu vào sai.
2. Phân tích tự do trong notebook: ngân sách cho `net` lớn nhất, độ nhạy theo giả định và điểm hoà vốn, so với quy tắc ở
   cùng số cuộc gọi, quy từ tập test ra toàn bộ khách, model có tốt đều giữa các nhóm không, thiết kế pilot.
3. Viết `starter/PROPOSAL.md` cho COO theo khung có sẵn: 250-700 từ, dòng đầu là headline có con số, đủ năm mục, mục giá
   trị nói rõ giả định.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: chọn top-k ổn định khi hoà điểm, đúng từng cột, `k = 0` không lỗi chia, gọi hết bằng gọi
  ngẫu nhiên, từ chối đầu vào sai.
- Trên bộ thật, với giả định 15 USD / 600 USD / 25%: gọi 476 khách test bắt 286 khách rời, net 35 760 USD; gọi 1 200 khách
  bắt 454.
- `PROPOSAL.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Một lần `np.cumsum` trên `y` đã sắp theo điểm cho số khách rời của mọi top-k: `reached[k]` là tổng `k` phần tử đầu (thêm
số 0 ở đầu để `k = 0` hợp lệ). `net` khi chọn ngẫu nhiên dùng tỉ lệ rời chung thay cho precision của model.

### Gợi ý 2

Một khách sắp rời được gọi đem về kỳ vọng `save_rate × value_per_save`; một cuộc gọi tốn `contact_cost`. Gọi thêm khách có
lợi khi precision **biên** (tỉ lệ rời của những khách thêm vào) còn lớn hơn `contact_cost / (save_rate × value_per_save)`.
Với giả định ban đầu ngưỡng đó là 10%: rất thấp, nên hỏi tiếp giả định nào yếu nhất, và vì sao pilot quan trọng hơn con
số tối ưu.
