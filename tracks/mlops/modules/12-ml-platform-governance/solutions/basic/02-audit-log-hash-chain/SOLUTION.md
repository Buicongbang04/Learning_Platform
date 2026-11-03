# Lời giải: audit log hash chain

Mã trong `auditlog.py`. Điểm mấu chốt:

- **Hash chain làm sửa lén trở nên đắt, không làm nó bất khả.** Mỗi dòng chứa hash của dòng trước, nên đổi một chữ ở dòng k làm hash dòng k sai, và nếu kẻ sửa tính lại hash dòng k thì `prev_hash` của dòng k+1 lệch. Họ phải tính lại **toàn bộ phần đuôi**. Vì vậy cần `anchor`: lưu `head()` ở nơi họ không ghi được (hệ thống khác, ticket kiểm toán, object storage bật object lock).
- **Cắt đuôi không để lại dấu vết trong chính chuỗi.** Bỏ 2 dòng cuối thì phần còn lại vẫn là chuỗi hợp lệ. Chỉ so với anchor mới thấy; đó là lý do `verify(anchor)` trả `len(entries)`.
- **JSON chuẩn tắc.** `sort_keys` và `separators` cố định để hai lần tính cho cùng một bản ghi ra cùng hash; thiếu thì thêm một dấu cách cũng đổi hash.
- **Đọc lại dòng cuối từ tệp mỗi lần append.** Nhớ trong bộ nhớ làm hai tiến trình tách chuỗi thành hai nhánh. Trong production vẫn cần khoá tệp hoặc ghi qua một dịch vụ duy nhất; bài này kiểm phần tuần tự.
- **Lý do bắt buộc.** Log có ai và lúc nào mà thiếu vì sao thì kiểm toán vẫn không trả lời được. Từ chối ghi, không ghi "N/A".
- **`who_promoted` trả danh sách.** Một version có thể được promote, rollback rồi promote lại; trả một người sẽ giấu lịch sử. Muốn biết ai đang giữ alias hiện tại thì đọc bản ghi `set_alias` champion cuối cùng của model, không phải theo version.

Giới hạn: audit log này ghi **sau** khi thao tác xảy ra do chính ứng dụng; người có quyền ghi thẳng vào registry vẫn đổi alias mà không để lại dòng nào. Muốn chặn điều đó phải khoá quyền ở registry (bài thiết kế governance) chứ không phải ở log.
