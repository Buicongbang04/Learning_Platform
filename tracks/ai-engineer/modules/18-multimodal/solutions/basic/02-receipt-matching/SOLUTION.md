# Lời giải: chấm hoá đơn trích xuất bằng code

## Cách làm

- `parse_amount`: số (`int`, `float`) trả luôn; chuỗi thì bỏ khoảng trắng, lấy cụm `\d[\d.,]*` đầu tiên, bỏ dấu phân cách
  thừa ở cuối (`"2.000,-"`). Âm khi phần trước cụm số có `-` hoặc kết thúc bằng `(`. Hai loại dấu: dấu đứng sau cùng là
  thập phân. Một loại dấu: nhóm đầu 1 tới 3 chữ số và mọi nhóm sau đúng 3 chữ số thì là phân cách nghìn; đúng hai nhóm
  thì là thập phân; còn lại `None`.
- `gold_from_cord`: một hàm phụ `_as_list` biến dict thành list một phần tử, rồi duyệt `[dòng, *sub của dòng]`.
- `name_similarity`: `re.sub(r"[^0-9A-Z]+", " ", name.upper())`, gộp khoảng trắng, `SequenceMatcher.ratio()`.
- `match_items`: liệt kê mọi cặp (tiền bằng nhau, tên đủ giống) với khoá `(-sim, i, j)`, sắp xếp, nhận tham lam.
- `score_receipt`, `aggregate`: đếm rồi chia, theo đúng định nghĩa mẫu số trong đề.

## Vì sao các lựa chọn này

- **Quy tắc ba chữ số** là đúng cho hoá đơn tiền đồng và rupiah (không có xu), và sai cho hoá đơn đô la ("12.500" có thể
  là 12.5). Bộ chấm phải mã hoá giả định về locale **một cách tường minh**, không để `float(text.replace(",", ""))` quyết
  định ngầm. Với dữ liệu nhiều locale, thêm tham số `locale` thay vì đoán.
- **Tiền và tên cùng lúc.** Chỉ dùng tiền thì "SERVICE CHARGE 51.000" ghép nhầm với món 51.000; chỉ dùng tên thì món đọc
  đúng tên mà sai tiền (lỗi nguy hiểm nhất của trợ lý tài chính) vẫn được tính là đúng. Ngưỡng tên 0.5 đủ lỏng cho lỗi
  OCR kiểu "ICE BLACKCOFFE" so với "ICE BLACK COFFEE" (độ giống 0.933) và "BASMINE MT (L)" so với "JASMINE MT ( L )" (0.917), trong khi "SERVICE CHARGE" so với "CHIKEN KATSU FF" chỉ 0.207.
- **Một-một, ưu tiên giống nhất.** Ghép nhiều-một làm model lặp một dòng ba lần vẫn được recall cao. Ghép theo thứ tự
  xuất hiện thay vì độ giống làm "NASI GORENG SPECIAL" chiếm mất chỗ của chính nó.
- **Micro, không macro.** Hoá đơn 1 dòng và hoá đơn 12 dòng không nên có trọng số bằng nhau khi hỏi "bao nhiêu phần trăm
  dòng hàng đọc đúng". Báo thêm `total_acc` theo hoá đơn vì đó là trường người dùng quan tâm nhất.
- **`total_ok = None` khi không có nhãn**, để 7/200 hoá đơn CORD không có `total_price` không bị tính là sai.

Một kiểm tra hay bị đề xuất nhưng không dùng được trên CORD: "tổng các dòng phải bằng tổng hoá đơn". Trên 200 hoá đơn
của `cord-v2` (validation + test), điều đó sai ở 87 hoá đơn (thuế, phí phục vụ, giảm giá, món kèm không ghi giá riêng).
Dùng nó làm luật validate sẽ loại oan gần một nửa số hoá đơn đúng; mục 2 lý thuyết bàn cách dùng nó làm **tín hiệu** cần
người xem lại thay vì luật.

## Bẫy thường gặp

- `float("60.000")` ra 60.0: sai 1 000 lần mà không báo lỗi. Đây là lỗi im lặng tệ nhất của cả pipeline.
- Quên `sub`, hoặc quên trường hợp `menu` là dict (một dòng): hoá đơn một món bị chấm 0 dòng nhãn.
- Chia `total_acc` cho mọi hoá đơn kể cả không có nhãn tổng.
- F1 trung bình theo hoá đơn (macro) rồi gọi là F1 dòng hàng.
