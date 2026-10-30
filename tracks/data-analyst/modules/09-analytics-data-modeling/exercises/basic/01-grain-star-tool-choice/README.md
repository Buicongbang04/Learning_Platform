---
title: Grain, fact/dimension và chỗ đặt logic - đọc schema trước khi viết SQL
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Luyện các quyết định modeling mà DA gặp trước khi viết dòng SQL đầu tiên: bảng ở grain nào, cột nào là fact
hay dimension, measure nào cộng được, chọn SCD nào cho câu hỏi nào, và đặt định nghĩa metric ở đâu để các
báo cáo không lệch nhau.

## Đề bài

Bài này không có code. Làm 12 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới), dựa trên phần 2, 3,
6 và 7 của lý thuyết:

- Câu về **Online Retail II** (sheet `Year 2010-2011`, dòng hợp lệ theo định nghĩa chung của track) dùng các
  con số trong lý thuyết: chạy lại các đoạn code ở phần 2 và 3 nếu muốn tự kiểm.
- Câu về **Grocery Sales** chỉ dùng **schema** 7 bảng dưới đây (bộ dữ liệu sinh giả, không rút insight):

| Bảng | Cột |
| --- | --- |
| `sales` | `SalesID`, `SalesPersonID`, `CustomerID`, `ProductID`, `Quantity`, `Discount`, `TotalPrice`, `SalesDate`, `TransactionNumber` |
| `products` | `ProductID`, `ProductName`, `Price`, `CategoryID`, `Class`, `ModifyDate`, `Resistant`, `IsAllergic`, `VitalityDays` |
| `categories` | `CategoryID`, `CategoryName` |
| `customers` | `CustomerID`, `FirstName`, `MiddleInitial`, `LastName`, `CityID`, `Address` |
| `cities` | `CityID`, `CityName`, `Zipcode`, `CountryID` |
| `countries` | `CountryID`, `CountryName`, `CountryCode` |
| `employees` | `EmployeeID`, `FirstName`, `MiddleInitial`, `LastName`, `BirthDate`, `Gender`, `CityID`, `HireDate` |

- Hai câu cuối là tình huống **chọn chỗ đặt logic** (SQL view, dbt, semantic layer của BI, spreadsheet).

## Tiêu chí đạt

- Trả lời đúng ít nhất 9/12 câu.
- Với mỗi câu sai, chỉ ra được bước nào bị bỏ qua: khai báo grain, kiểm khoá, phân loại measure hay hỏi "ai
  dùng định nghĩa này".
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Với mỗi bảng, viết câu "một dòng = ..." trước khi chọn. Câu hỏi về trung bình hay tỉ lệ: metric đó ở grain nào
(dòng, hoá đơn, khách)? Tổng hợp lên grain đó trước rồi mới chia.

### Gợi ý 2

Snowflake (bảng nối bảng qua nhiều bước) đúng về chuẩn hoá nhưng bất tiện cho người dùng BI; star schema gộp các
bảng mô tả vào một dimension phẳng. Với SCD, hỏi: báo cáo cần thuộc tính **hiện tại** hay **tại thời điểm giao
dịch**?
