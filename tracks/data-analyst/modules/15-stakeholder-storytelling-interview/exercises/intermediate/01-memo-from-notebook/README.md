---
title: Viết memo một trang từ notebook có sẵn - khách vãng lai Capital Bikeshare
level: intermediate
services: []
files:
  - path: starter/casual_memo.ipynb
    note: Phân tích có sẵn + 1 hàm TODO (memo_facts)
  - path: starter/MEMO.md
    note: Memo một trang gửi giám đốc marketing
  - path: tests/test_casual_memo.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py bike-sharing-uci
  - uv run jupyter lab tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/intermediate/01-memo-from-notebook/starter/casual_memo.ipynb
  - uv run pytest tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/intermediate/01-memo-from-notebook -q
---

## Mục tiêu

Làm đúng việc hay bị bỏ qua nhất sau một phân tích: từ một notebook nhiều bảng và chart (người khác làm), rút ra vài
con số có định nghĩa rõ và viết một memo mà giám đốc đọc một phút là quyết định được: headline là kết luận, khuyến
nghị trước, ba bằng chứng có số, giới hạn và bước tiếp theo.

## Đề bài

Bộ `bike-sharing-uci`, `hour.csv` (17 379 giờ có dữ liệu, 2011-2012). Giám đốc marketing hỏi: **"Năm sau tôi muốn chạy
chiến dịch mời khách vãng lai đăng ký thành viên. Nên tập trung vào lúc nào?"** Một đồng nghiệp đã phân tích xong
trong `starter/casual_memo.ipynb` (các cell `explore`: tỉ trọng theo loại ngày, lượt theo giờ, theo tháng). Bạn:

1. Chạy notebook, đọc phân tích, ghi ra ba điều bạn thấy.
2. Viết `memo_facts(hour) -> dict` trả tám con số theo bảng định nghĩa trong notebook (tỉ trọng khách vãng lai chung,
   theo loại ngày, phần của ngày nghỉ, và của "khung giờ chiến dịch": ngày nghỉ, 10h-17h, tháng 4-10).
3. Viết `starter/MEMO.md` theo khung có sẵn: dòng đầu `# ...` là headline có ít nhất một con số phần trăm lấy từ
   `memo_facts` (làm tròn số nguyên hoặc một chữ số thập phân); năm mục `## Bối cảnh và câu hỏi`, `## Khuyến nghị`,
   `## Bằng chứng`, `## Giới hạn`, `## Bước tiếp theo` theo đúng thứ tự; 200-450 từ; viết cho người không đọc code.
4. Làm phần **trắc nghiệm** trong app.

Memo không phải bản tóm tắt notebook: chọn những con số trả lời câu hỏi của giám đốc, bỏ phần còn lại.

## Tiêu chí đạt

- `memo_facts` đúng trên dữ liệu nhỏ (giờ 17h thuộc khung, tháng 11 ngoài khung, số ngày đếm theo ngày chứ không theo
  dòng), nhận `dteday` dạng chuỗi hoặc datetime, không sửa đầu vào.
- Trên bộ thật: khách vãng lai chiếm 18.8% lượt; ngày nghỉ là 31.6% số ngày nhưng mang 51.1% lượt khách vãng lai;
  tỉ trọng khách vãng lai 31.7% ngày nghỉ so với 13.2% ngày làm việc; khung chiến dịch là 6.1% số giờ, chứa 27.6%
  lượt khách vãng lai, và trong khung khách vãng lai chiếm 38.9%.
- `MEMO.md`: không còn TODO, đủ năm mục theo thứ tự, headline có con số khớp `memo_facts`, mục Bằng chứng có ít nhất ba
  gạch đầu dòng mỗi dòng một con số, không có tên cột, tên tệp hay thuật ngữ pandas. Nội dung chấm theo rubric trong
  `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Số ngày nghỉ phải đếm theo **ngày**: `hour.groupby("dteday")["workingday"].first()`, rồi lấy tỉ lệ bằng 0. Đếm theo dòng
sẽ ra tỉ lệ giờ, không phải tỉ lệ ngày (và `hour.csv` thiếu một số giờ ban đêm). Khung chiến dịch là giao của ba điều
kiện: `workingday == 0`, `hr` trong `range(10, 18)`, tháng trong `range(4, 11)`.

### Gợi ý 2

Viết headline trước, rồi chỉ giữ bằng chứng ủng hộ hoặc giới hạn nó. Một con số mạnh là con số có **tương phản**: "6%
số giờ mang 28% lượt". Mục giới hạn trả lời câu "dữ liệu này không nói gì": thời điểm khách vãng lai đi không phải là
khả năng họ đăng ký; không có dữ liệu trạm; chưa đo được hiệu quả chiến dịch.
