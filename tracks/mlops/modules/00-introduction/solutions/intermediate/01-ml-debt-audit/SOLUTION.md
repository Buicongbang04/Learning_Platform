# Lời giải: máy quét nợ kỹ thuật ML

Xem `audit.py` cùng thư mục. Các điểm đáng nói:

- **Mỗi luật ứng với một nợ có tên.** Model/dữ liệu trong Git: repo phình, lộ dữ liệu, không biết bản nào đúng (module 03).
  Đường dẫn cứng và dependency không ghim: *configuration debt*, chạy được trên máy một người. Không seed: không tái lập
  (module 01). Chỉ có notebook: không test, không import được (*glue/prototype code*).
- **Ca biên là nơi luật hỏng.** `"tests" in path` bắt nhầm `latests/`; chỉ kiểm `.csv` bỏ sót `.CSV`; đếm dòng `-r base.txt`
  là gói không ghim sẽ gây báo động giả; URL chứa `/home/` là false positive điển hình của grep ngây thơ.
- **`block` và `warn` là một quyết định chính sách**, không phải kỹ thuật: ở đây chỉ chặn những thứ khó gỡ khi đã vào lịch
  sử Git (model, dữ liệu, mật khẩu/đường dẫn). Quét bằng regex đủ cho CI nhanh nhưng bắt được ít hơn một công cụ AST;
  đổi lại dễ đọc và dễ thêm luật.
