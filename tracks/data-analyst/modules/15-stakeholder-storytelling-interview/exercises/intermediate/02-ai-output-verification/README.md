---
title: Kiểm lại "insight" do LLM viết trên Bike Sharing và tạo hồ sơ dữ liệu an toàn để hỏi AI
level: intermediate
services: []
files:
  - path: starter/ai_check.ipynb
    note: 3 hàm TODO (actual_values, verify, llm_safe_profile)
  - path: tests/test_ai_check.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/intermediate/02-ai-output-verification/starter/ai_check.ipynb
  - uv run pytest tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/intermediate/02-ai-output-verification -q
---

## Mục tiêu

Dùng AI mà vẫn chịu trách nhiệm được về từng con số: tính lại mọi claim bằng code của mình theo đúng data dictionary,
đối chiếu có sai số cho phép, và trước khi hỏi AI về một bảng có dữ liệu khách hàng, chỉ gửi hồ sơ cột đã che các
trường nhạy cảm.

## Đề bài

Bộ `bike-sharing-uci`, `day.csv` (731 ngày) và `hour.csv` (17 379 giờ). Một đồng nghiệp nhận từ chatbot tám câu "insight"
có số (hằng `LLM_CLAIMS` trong `starter/ai_check.ipynb`) và định gửi thẳng cho giám đốc vận hành. Bạn:

1. `actual_values(day, hour) -> dict`: tính lại tám giá trị theo bảng định nghĩa trong notebook (tăng trưởng năm, mã thứ
   đông nhất, TB mùa 2, nhiệt độ °C, tăng trưởng khách vãng lai, giờ cao điểm, ngày đông nhất, tương quan nhiệt độ).
2. `verify(claims, actual, rel_tol=0.01) -> DataFrame`: đối chiếu từng claim với giá trị thật bằng sai số tương đối;
   claim không kiểm được là không đạt.
3. `llm_safe_profile(df, sensitive=()) -> DataFrame`: hồ sơ cột (kiểu, số ô thiếu, số giá trị khác nhau, một ví dụ),
   che ví dụ của cột nhạy cảm (khai báo hoặc tự nhận theo tên: `id`, `email`, `phone`, `name`, `address`, `dob`), báo lỗi
   khi tên cột nhạy cảm khai báo không tồn tại.
4. Trả lời bốn câu hỏi ở cuối notebook, rồi làm phần **trắc nghiệm** trong app.

## Tiêu chí đạt

- `actual_values` đúng trên dữ liệu nhỏ (năm lấy từ `dteday` dạng chuỗi hoặc datetime, nhiệt độ nhân 41, không sửa đầu vào).
- `verify` giữ thứ tự claim, tính đúng sai số tương đối, xử lý `actual = 0` và claim thiếu giá trị thật.
- `llm_safe_profile` không lộ giá trị của cột nhạy cảm, đúng kiểu và số đếm, cột toàn thiếu có ví dụ rỗng, `ValueError`
  khi gõ sai tên cột nhạy cảm.
- Trên bộ thật: 4/8 claim đúng (`yoy_growth` 64.9%, `peak_hour_mean` 461.45, `peak_day_count` 8 714, `temp_corr` 0.63) và
  4/8 sai: thứ đông nhất là mã 5 (thứ Sáu), TB mùa 2 là 4 992 lượt/ngày (5 644 là của mùa 3), nhiệt độ TB 20.3 °C (0.50 là
  giá trị chuẩn hoá), khách vãng lai tăng 50.8% (68.4% là của thành viên).

## Gợi ý

### Gợi ý 1

So từng con số sai của chatbot với các bảng trong cell explore phần 2: con số không phải bịa ngẫu nhiên, nó là con số
**thật** gắn nhầm nhãn (nhầm mã thứ, nhầm mã mùa, quên đổi đơn vị, nhầm cột). Đó là kiểu lỗi nguy hiểm nhất vì nó trông
hợp lý.

### Gợi ý 2

Tách tên cột thành token: `re.split(r"[^0-9a-z]+", "Customer ID".lower())` cho `["customer", "id"]`. Không dùng phép "chứa
chuỗi con" (`"id" in "paid_amount"` là `True`). Với `verify`, `pd.isna` xử lý được cả `None` và `NaN`.
