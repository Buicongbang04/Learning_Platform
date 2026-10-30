---
title: Đọc code R (dplyr, tidyr, ggplot2) và chọn bản pandas tương đương
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Đọc được một đoạn tidyverse của đồng nghiệp (team nghiên cứu, bài báo, khoá học thống kê) và chọn đúng bản pandas /
seaborn cho **cùng kết quả**, kể cả ở những chỗ hai ngôn ngữ khác nhau lặng lẽ: `NA`, đếm dòng và đếm giá trị khác
nhau, `mutate` theo nhóm, join nhân dòng, `geom_bar` và `geom_col`.

## Đề bài

Bài này không có code và không cần cài R. Làm 12 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới). Mỗi câu cho
một đoạn R chạy trên một trong hai bảng quen thuộc của module:

- `co2`: bảng OWID (`country`, `year`, `iso_code`, `co2`, `co2_per_capita`...), mỗi dòng một cặp nước-năm.
- `tx`: Online Retail II (`Invoice`, `StockCode`, `Quantity`, `Price`, `Customer ID`, `Country`, `InvoiceDate`), mỗi
  dòng một dòng hàng trong hoá đơn. Trong R, cột có dấu cách viết trong dấu backtick: `` `Customer ID` ``.

Chọn đoạn pandas (hoặc seaborn) cho **cùng kết quả** với đoạn R, hoặc trả lời câu hỏi về khác biệt. Hai bảng đối chiếu
dplyr ↔ pandas và ggplot2 ↔ seaborn ở phần 5 lý thuyết là đủ để làm hết bài.

## Tiêu chí đạt

- Trả lời đúng ít nhất 10/12 câu.
- Với mỗi câu sai, chỉ ra dòng nào trong bảng đối chiếu ở phần 5 lý thuyết đã bị bỏ qua.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Đọc pipe `|>` từ trên xuống như method chaining: mỗi dòng nhận bảng của dòng trên. `group_by` không tự làm gì; nó đổi
nghĩa của động từ **ngay sau**: `summarise` thu mỗi nhóm về một dòng (`agg`), `mutate` giữ nguyên số dòng
(`transform`), `slice_max` lấy dòng trong từng nhóm.

### Gợi ý 2

Ba chỗ R và pandas khác mặc định: R không bỏ `NA` khi tính (`na.rm = TRUE` mới bỏ), pandas bỏ `NaN` mặc định;
`n()` đếm dòng như `size`, `n_distinct()` là `nunique`; `geom_bar()` đếm dòng còn `geom_col()` vẽ giá trị có sẵn,
trong khi `sns.barplot` mặc định vẽ trung bình.
