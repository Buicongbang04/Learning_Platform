# Lời giải: phát hiện, che và giả danh hoá PII tiếng Việt

## Cách làm

**Mỗi loại một regex, kiểm cấu trúc sau.** Regex chỉ tìm ứng viên theo hình dạng; quyết định cuối nằm ở hàm kiểm:

- `CARD`: `\d{4}(?:[ -]?\d{4}){2}[ -]?\d{1,7}` rồi bỏ dấu, đếm 13 tới 19 chữ số, `luhn_ok`. Luhn nhân đôi các chữ số
  ở vị trí chẵn tính từ phải (bắt đầu từ chữ số thứ hai), trừ 9 nếu quá 9, tổng chia hết cho 10.
- `CCCD`: 12 chữ số liền, `cccd_ok` kiểm mã tỉnh và mã thế kỷ.
- `BANK`, `CMND`: một regex có hai named group, `key` (từ khoá) và `num` (phần số); span lấy theo `m.start("num")`.
- `PHONE`: `(?:\+84|84|0)[\s.-]?[35789]\d(?:[\s.-]?\d){7}`.
- Mọi regex chữ số có ranh giới `(?<![\d.,])` ở đầu và `(?![\d]|[.,]\d)` ở cuối: dấu chấm cuối câu ("gọi 0912345678.")
  vẫn cho khớp, còn `1.091.234.567` thì không.

**Chồng lấn.** Sắp theo `(-độ dài, KINDS.index(kind), start)`, nhận span nếu không giao span nào đã nhận
(`s.end <= k.start or s.start >= k.end`), cuối cùng sắp lại theo `start`. `redact` và `pseudonymize` thay từ span cuối
lên span đầu.

**Giả danh hoá.** `hmac.new(key, f"{kind}:{chuẩn}".encode(), hashlib.sha256).hexdigest()[:10]`. Chuẩn hoá trước khi
băm để `+84912345678` và `0912 345 678` là **một** người trong log (join được, đếm được số lần một khách gọi), nhưng không
đọc ngược được nếu không có khoá. `restore` dùng một regex khớp mọi token hợp lệ và tra `vault`; token lạ (LLM bịa ra
hoặc chép sai) được để nguyên, để người đọc thấy chỗ hỏng thay vì một chuỗi rỗng.

## Vì sao như vậy

- **Luhn và mã tỉnh** loại phần lớn số "trông giống" PII: mã vận đơn 16 số chỉ có khoảng 1/10 cơ hội qua Luhn, mã hoá
  đơn 12 số chỉ khoảng 63/1000 cơ hội có 3 số đầu là mã tỉnh, nhân với 4/10 cơ hội ở chữ số thứ 4. Không kiểm,
  precision của hai loại này trên tập sinh của test tụt rõ (test có mẫu gây nhiễu cho đúng hai trường hợp này).
- **Từ khoá cho số tài khoản**: số tài khoản Việt Nam dài 6 tới 19 chữ số, không có checksum chung, nên chỉ nhận ra
  được nhờ ngữ cảnh. Cái giá là recall: "chuyển vào 0071001234568 nhé" không có từ khoá thì bị bỏ sót. Đó là đánh đổi
  phải ghi rõ khi báo cáo con số recall.
- **Token có khoá, không phải hash trần**: SHA-256 của một số điện thoại dò ngược được bằng cách thử hết khoảng
  $$5 \cdot 10^8$$ số di động. Đây là pseudonymization (khôi phục được với khoá), không phải anonymization: dữ liệu đã giả
  danh vẫn là dữ liệu cá nhân, khoá phải được bảo vệ như chính dữ liệu.

## Giới hạn

- Tên người không được bắt: regex không biết "Nguyễn Văn An" là tên. Cần NER (underthesea, mô hình token
  classification) hoặc LLM, và cả hai có recall không hoàn hảo; mục 3 lý thuyết bàn về cách kết hợp.
- Tập sinh của test có định dạng do chính chúng ta chọn, nên precision và recall bằng 1 ở đây chỉ nói rằng code làm đúng
  đặc tả. Văn bản thật có số viết tách lạ (`09 12 34 56 78`), số viết bằng chữ, địa chỉ không có từ "đường": đo lại trên
  mẫu thật có gán nhãn trước khi tin con số.
- Địa chỉ là loại khó nhất cho regex; ở đây chỉ bắt dạng có số nhà và đơn vị hành chính.

## Bẫy thường gặp

- Thay chuỗi từ đầu đến cuối: sau span đầu, mọi offset phía sau lệch.
- Dùng `\b` làm ranh giới chữ số: `.` là ranh giới từ nên `1.091.234.567` chứa "091234567" hợp lệ.
- Giữ cả hai span chồng lấn: `[BANK]` chèn vào giữa `[PHONE]` thành chuỗi vô nghĩa.
- Coi hai span chạm nhau (`end == start`) là chồng lấn và bỏ mất một span.
- Không chuẩn hoá số điện thoại trước khi băm: một khách thành hai người trong log.
