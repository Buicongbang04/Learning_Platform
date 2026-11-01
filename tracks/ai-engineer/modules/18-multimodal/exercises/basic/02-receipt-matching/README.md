---
title: Chấm hoá đơn trích xuất bằng code, không cần LLM
level: basic
services: []
files:
  - path: starter/receipt_check.py
    note: 6 hàm TODO
  - path: tests/test_receipt_check.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/18-multimodal/exercises/basic/02-receipt-matching -q
---

## Mục tiêu

Viết bộ chấm mà bài Intermediate 01 và bài portfolio dùng để đo vision LLM đọc hoá đơn: chuẩn hoá số tiền in theo kiểu
Việt Nam/Indonesia ("60.000", "24,000", "Rp 1.250.000"), ghép dòng hàng dự đoán với nhãn, và tính độ chính xác theo
từng trường. Bộ chấm tất định, chạy trong mili giây, không có LLM nào chấm LLM.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Nhãn là trường `gt_parse` của bộ `cord-v2` (mục 2 lý thuyết): `menu` là **một dict** khi hoá đơn có một dòng hàng và
**một list** khi có nhiều dòng; mỗi dòng có `nm` (tên), có thể có `cnt` (số lượng, như `"2"`, `"1X"`, `"x2"`), `price`
(thành tiền của dòng) và `sub` (món kèm, cũng dict hoặc list, cùng khoá). `total.total_price` là tổng phải trả, có thể
không có. Dự đoán của model có dạng `{"items": [{"name", "quantity", "amount"}], "total": ...}`, số tiền là chuỗi như in
trên hoá đơn hoặc số.

Trong `starter/receipt_check.py`:

1. `parse_amount(text) -> float | None`. Nhận chuỗi hoặc số. Lấy cụm số đầu tiên (chữ số, `.` và `,`), bỏ ký hiệu tiền
   tệ, khoảng trắng, dấu `,-`/`.-` ở cuối. Âm khi có `-` đứng trước số hoặc số nằm trong ngoặc `( )`. Quy tắc dấu phân cách:
   - có cả `.` và `,`: dấu xuất hiện **sau cùng** là dấu thập phân, dấu kia là phân cách nghìn (`"1.234,50"` và
     `"1,234.50"` đều là 1234.5);
   - chỉ một loại dấu: nếu mọi nhóm sau dấu đều đúng 3 chữ số và nhóm đầu có 1 tới 3 chữ số thì đó là phân cách nghìn
     (`"5.455"` là 5455, như mọi hoá đơn tiền đồng và rupiah); nếu chỉ có một dấu và nhóm sau không phải 3 chữ số thì là
     thập phân (`"2.00"`, `"12.5"`); còn lại (như `"1.000.5"`) trả `None`.
   Không có chữ số nào, hoặc `None`, thì trả `None`.
2. `gold_from_cord(gt_parse) -> dict`: `{"items": [...], "total": float | None}`. Mỗi dòng của `menu` (dict hoặc list),
   rồi ngay sau nó các món trong `sub` của nó, thành `{"name": nm, "quantity": q, "amount": parse_amount(price)}`; bỏ dòng
   không có `price` đọc được. `q` đọc từ `cnt` sau khi bỏ chữ `x`/`X`, mặc định 1.
3. `name_similarity(a, b) -> float`: chuẩn hoá hai tên (chữ hoa, mọi ký tự không phải chữ cái A-Z hoặc chữ số thành
   khoảng trắng, gộp khoảng trắng) rồi `difflib.SequenceMatcher(None, a, b).ratio()`.
4. `match_items(pred, gold, min_name_sim=0.5)`: ghép **một-một**. Một cặp hợp lệ khi số tiền bằng nhau (lệch không quá
   0.5) **và** `name_similarity` tối thiểu `min_name_sim`. Xét các cặp hợp lệ theo độ giống giảm dần (hoà thì theo chỉ
   số pred rồi chỉ số gold tăng dần), nhận cặp nếu cả hai phía chưa được dùng. Trả list `(i_pred, i_gold)` đã sắp xếp.
5. `score_receipt(pred, gold) -> dict`: `total_ok` là `None` khi nhãn không có tổng, ngược lại là tổng dự đoán có bằng
   tổng nhãn không (lệch không quá 0.5); `n_pred`, `n_gold`, `n_match`; `qty_ok` là số cặp đã ghép có số lượng bằng nhau
   (số lượng dự đoán thiếu thì coi là 1). `pred is None` (model trả JSON hỏng) chấm như không đọc được gì.
6. `aggregate(scores) -> dict`: `receipts`, `total_acc` (trung bình `total_ok` trên các hoá đơn **có** nhãn tổng; không
   có hoá đơn nào thì `nan`), `item_precision`, `item_recall`, `item_f1` **mức micro** (cộng dồn số đếm rồi mới chia;
   mẫu số 0 thì 0.0), `qty_acc` (trên tổng số cặp đã ghép; 0 cặp thì `nan`). Danh sách rỗng ném `ValueError`.

## Tiêu chí đạt

- `parse_amount` đúng trên 17 chuỗi và số mẫu, trả `None` cho chuỗi rỗng, chữ, `None` và `"1.000.5"`.
- `gold_from_cord` xử lý `menu` dạng dict và list, món kèm `sub`, số lượng `"1X"`, dòng không có giá, hoá đơn không có tổng.
- `match_items` cần **cả** tiền và tên, một-một, ưu tiên tên giống nhất.
- `score_receipt` và `aggregate` đúng số đếm tính tay; F1 là micro.

## Gợi ý

### Gợi ý 1

Viết `parse_amount` bằng `re.search(r"\d[\d.,]*", s)` cho cụm số, xét phần chuỗi **trước** cụm số để biết dấu âm. Tách
nhóm bằng `token.split(sep)` rồi kiểm độ dài từng nhóm. Kiểm từng quy tắc bằng tay trên `"5.455"` (thuế 10% của
54 550 rupiah) trước khi chạy test: đọc thành 5.455 là sai lệch 1 000 lần.

### Gợi ý 2

Ghép một-một kiểu tham lam: dựng danh sách mọi cặp hợp lệ kèm khoá sắp xếp `(-độ_giống, i, j)`, sắp xếp, rồi duyệt và
giữ hai tập chỉ số đã dùng. Hai món cùng tên cùng giá (hai ly trà) phải ghép được với hai dòng nhãn, và ba dòng dự đoán
giống hệt nhau chỉ ghép được hai.
