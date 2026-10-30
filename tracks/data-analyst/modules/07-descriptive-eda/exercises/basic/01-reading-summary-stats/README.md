---
title: Đọc bảng thống kê mô tả - Telco và Rossmann
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Đọc một bảng `describe()` như DA senior: biết con số nào trả lời câu hỏi nào, nhận ra hình dạng phân phối và
các bẫy (tập dòng được tính, ô trống, mẫu hay tổng thể) chỉ từ vài con số, và biết công cụ nào tính ra con số đó.

## Đề bài

Bài này không có code. Đọc hai bảng dưới (tính trên dữ liệu thật, phần 2–6 của lý thuyết giải thích cách tính),
rồi làm 10 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới).

**Bảng 1. Telco Customer Churn** (7 043 khách; `TotalCharges` là chuỗi trong tệp gốc, 11 ô trống được đổi
thành NaN trước khi tính):

| | `tenure` (tháng) | `MonthlyCharges` (USD) | `TotalCharges` (USD) |
| --- | --- | --- | --- |
| count | 7 043 | 7 043 | 7 032 |
| mean | 32.37 | 64.76 | 2 283.30 |
| std | 24.56 | 30.09 | 2 266.77 |
| min | 0 | 18.25 | 18.80 |
| 25% | 9 | 35.50 | 401.45 |
| 50% | 29 | 70.35 | 1 397.48 |
| 75% | 55 | 89.85 | 3 794.74 |
| max | 72 | 118.75 | 8 684.80 |
| skew | 0.24 | −0.22 | 0.96 |
| kurt | −1.39 | −1.26 | −0.23 |

**Bảng 2. Rossmann Store Sales** (`train.csv`, một dòng là một cửa hàng một ngày; "mở cửa" là `Open = 1` và
`Sales > 0`):

| | `Sales`, mọi dòng (EUR) | `Sales`, ngày mở cửa (EUR) | `Customers`, ngày mở cửa |
| --- | --- | --- | --- |
| count | 1 017 209 | 844 338 | 844 338 |
| mean | 5 773.8 | 6 956.0 | 762.8 |
| std | 3 849.9 | 3 103.8 | 401.2 |
| min | 0 | 46 | 8 |
| 25% | 3 727 | 4 859 | 519 |
| 50% | 5 744 | 6 369 | 676 |
| 75% | 7 856 | 8 360 | 893 |
| max | 41 551 | 41 551 | 7 388 |
| skew | 0.64 | 1.59 | 2.79 |
| kurt | 1.78 | 4.85 | 13.32 |

`std` là độ lệch chuẩn mẫu (`ddof=1`, mặc định của pandas); `kurt` là excess kurtosis (phân phối chuẩn = 0).

## Tiêu chí đạt

- Trả lời đúng ít nhất 8/10 câu.
- Với mỗi câu sai, chỉ ra được dòng nào trong bảng (hoặc phần nào của lý thuyết) cho đáp án đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Trước khi đọc mean, đọc `count`: nó cho biết con số được tính trên tập dòng nào. Hai cột có `count` khác nhau
là hai tổng thể khác nhau.

### Gợi ý 2

So mean với median (50%) để biết hướng lệch; so skew và kurt để biết có nên tin một con số tóm tắt không.
Kurtosis âm không có nghĩa là "ổn định": nó thường là dấu hiệu phân phối phẳng hoặc nhiều đỉnh.
