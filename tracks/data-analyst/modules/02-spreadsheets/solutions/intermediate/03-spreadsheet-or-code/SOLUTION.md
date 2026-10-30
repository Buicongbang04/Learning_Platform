# Lời giải: spreadsheet hay SQL/Python

Bốn câu hỏi dẫn đường (phần 7 lý thuyết): dữ liệu bao lớn, lặp lại bao lâu một lần, có cần giải trình
và tái lập, người nhận có cần tự chỉnh/tự lọc. Câu nào sai thường là do bỏ qua một trong bốn câu này.

## Đáp án

- `two-years-retail` (b). 1 067 371 dòng vượt 1 048 576 dòng của một sheet Excel/LibreOffice; Google
  Sheets giới hạn 10 triệu ô (8 cột × 1 067 371 ≈ 8.5 triệu ô là sát trần và sẽ rất chậm). Cộng hai
  pivot bằng tay (c) quên mất hai sheet trùng nhau 01–09/12/2010: phải bỏ trùng theo định nghĩa chung.
  pandas/DuckDB đọc hai sheet, bỏ trùng, tổng hợp; kết quả 25 dòng thì đưa ra Excel được.
- `commission-weekly` (b). Lặp hằng tuần, 300 000 dòng, liên quan tới tiền trả cho người: cần tái lập
  và giải trình. Head of Sales vẫn nhận Excel (đầu ra), nhưng logic nằm trong code có test. (a), (d)
  làm được nhưng mỗi tuần là một cơ hội dán thiếu dòng hoặc quên Refresh; (c) để nhiều người sửa công
  thức tính lương là rủi ro lớn nhất.
- `price-scenarios` (a). Người dùng cần **tự đổi giả định** và thấy kết quả ngay, dữ liệu nhỏ (50 dòng):
  đúng thế mạnh của spreadsheet. Ô giả định có data validation (giới hạn -50%…50%) để không gõ nhầm 5
  thành 500%.
- `partner-excel-2016` (b). XLOOKUP sẽ hiện `#NAME?` ở Excel 2016; VLOOKUP không tra sang trái. (d) chạy
  được nhưng mất khả năng cập nhật khi đối tác sửa mã.
- `campaign-tracker` (b). Cộng tác thời gian thực, lịch sử sửa, công ty dùng Google Workspace. Vùng khoá
  cho phần số liệu đổ từ hệ thống, data validation cho kênh/trạng thái.
- `reconcile` (b). Lệch số thường do **định nghĩa** (gộp/ròng, ngày đặt/ngày ghi nhận, đơn huỷ), sau đó
  mới là lỗi dữ liệu. Ghép ở mức hoá đơn bằng XLOOKUP, pivot chênh lệch theo loại (chỉ có ở A, chỉ có ở
  B, khác số tiền).
- `weekly-distinct` (c). Cộng số khách từng tuần đếm một khách nhiều lần: bài advanced 01 có 232 lượt
  khách-tuần nhưng chỉ 176 khách khác nhau trong 5 tuần. Lấy max (b) thì thiếu.
- `refresh-pipeline` (b). openpyxl ghi công thức nhưng không tính; `data_only=True` trên file vừa ghi trả
  `None`. LibreOffice headless tính lại (đây là cách testkit của repo chấm bài Excel).
- `pivot-vs-sumifs` (b). Công thức trỏ vào ô pivot vỡ khi pivot đổi bố cục hoặc thêm hàng; SUMIFS trên bố
  cục cố định, pivot dùng để đối chiếu.
- `llm-formula` (b). Tên, email là dữ liệu cá nhân; không đưa vào công cụ ngoài công ty khi chưa được
  phép. Mô tả cột (tên cột, kiểu, ví dụ đã che) là đủ để viết công thức; luôn tự kiểm công thức trên vài
  dòng biết trước kết quả. (d) quá cứng: LLM hữu ích để viết và giải thích công thức.
