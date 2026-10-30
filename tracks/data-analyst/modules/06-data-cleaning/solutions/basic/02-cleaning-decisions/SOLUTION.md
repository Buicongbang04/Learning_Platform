# Lời giải: chọn cách xử lý và công cụ làm sạch

## Cách làm

Mỗi câu trả lời ba câu hỏi: con số dùng cho chỉ số nào; vì sao dữ liệu thiếu / trùng / lạ; việc này lặp lại bao lâu
một lần và ai review. Phương án sai bỏ qua ít nhất một câu.

## Đáp án từng câu

| Câu | Đáp án | Vì sao |
| --- | --- | --- |
| `mcar-case` | a. Máy quét kẹt giấy ngẫu nhiên | Khả năng thiếu không liên quan tới bất kỳ biến nào. b là MNAR (thiếu phụ thuộc chính thu nhập), c là MAR (phụ thuộc kênh, quan sát được), d là MNAR (cảm biến tắt vì chính giá trị cao) |
| `survey-mnar` | c. MNAR | Khả năng trả lời phụ thuộc vào chính điểm hài lòng bị thiếu; trung bình điểm trên người trả lời bị thổi lên, không điền được bằng dữ liệu có sẵn |
| `missing-region` | b. Giữ, nhãn "Không rõ vùng" | Tổng doanh thu phải đúng; chia theo tỉ trọng là bịa (app cũ có thể tập trung ở vài vùng); bỏ làm tổng thấp đi 3% |
| `missing-price` | d. Lấy từ bảng giá, không được thì báo riêng | Kế toán cần số đúng, không cần số "đầy". Giá trung bình toàn sản phẩm sai cho từng dòng; bỏ hay điền 0 đều làm doanh thu thấp sai mà không ai biết |
| `duplicate-events` | a. Tìm nguồn trùng, khoá đúng | Trùng thường do retry gửi lại; dedupe theo `event_id` (nếu có) đúng hơn so mọi cột; bỏ cả hai dòng làm mất event thật |
| `fuzzy-tool` | c. OpenRefine | Clustering (key collision, nearest neighbor) cho nhóm ứng viên để người duyệt; Remove Duplicates, `DISTINCT`, `drop_duplicates` chỉ bắt trùng chính xác |
| `big-order` | d. Kiểm huỷ, hỏi sales | Outlier nghiệp vụ: trên Online Retail II, hoá đơn 581483 (168 470 GBP) bị huỷ 12 phút sau. Winsorize hay bỏ theo z-score đều không trả lời "giao dịch này có thật không" |
| `weekly-partner-file` | a. Script pandas trong git | Lặp lại hằng tuần, nhiều bước, cần review: code có test và nhật ký. Làm tay trong Excel không tái lập được; OpenRefine hợp cho một lần |
| `warehouse-checks` | d. dbt tests | Công ty đã dùng dbt: `unique`, `not_null`, `accepted_values` chạy cùng `dbt build`, chặn dữ liệu lỗi trước khi lên dashboard |
| `dplyr-distinct` | b. `df.drop_duplicates("customer_id")` | `distinct(..., .keep_all = TRUE)` giữ dòng đầu của mỗi `customer_id` với mọi cột; `unique()` / `drop_duplicates()` trên Series chỉ trả một cột; `size()` đếm |

## Sai lầm hay gặp

- Gọi mọi dữ liệu thiếu là MCAR để được phép `dropna()`.
- Điền trung bình cho tiền: con số "đầy" nhưng sai, và không ai còn biết phần nào là bịa.
- Chọn công cụ theo thói quen: làm tay một việc lặp lại hằng tuần, hoặc viết pipeline cho một việc làm một lần.
