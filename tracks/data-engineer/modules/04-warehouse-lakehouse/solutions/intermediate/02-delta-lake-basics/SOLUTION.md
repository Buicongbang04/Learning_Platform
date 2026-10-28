# Lời giải: Delta Lake căn bản

Xem `delta_ops.py`.

## Cái gì làm nên một "bảng" Delta

Thư mục bảng gồm các tệp Parquet + thư mục `_delta_log/` chứa các commit JSON `00000000000000000000.json`, `...01.json`.
Mỗi commit ghi lại tệp nào được **add**, tệp nào bị **remove**. Phiên bản bảng = tập tệp còn "sống" sau khi
áp lần lượt các commit. Mở thư mục ra xem sau mỗi bước của test để thấy:

- `append` chỉ thêm tệp mới, không đụng tệp cũ.
- `MERGE`/`DELETE` không sửa Parquet tại chỗ (Parquet bất biến): ghi tệp mới chứa các dòng còn lại/đã sửa và đánh
  dấu tệp cũ là removed (copy-on-write). Vì tệp cũ vẫn còn trên đĩa nên **time travel** đọc được version cũ.
- `VACUUM` mới thật sự xoá các tệp đã removed quá hạn retention (mặc định 7 ngày), sau đó không time travel về
  trước mốc đó được nữa.

## ACID

Ghi commit log là thao tác nguyên tử (put-if-absent trên tệp version kế tiếp). Hai writer cùng ghi version N thì một
bên thắng, bên kia phải đọc lại và thử lại (optimistic concurrency). Reader luôn thấy một snapshot nhất quán.

## Schema enforcement và evolution

- Mặc định Delta **từ chối** dữ liệu khác schema (thừa cột, sai kiểu). Đây là điểm khác biệt lớn so với thư mục
  Parquet trần, nơi ai cũng có thể thả vào một tệp sai schema và làm hỏng reader.
- Muốn thêm cột thì phải nói rõ: `schema_mode="merge"`. Dòng cũ đọc ra NULL ở cột mới.

## MERGE

`MERGE` là cách chuẩn để nạp tăng dần idempotent: chạy lại cùng batch không sinh bản trùng. Điều kiện khớp nên
dùng đúng khoá nghiệp vụ; nếu source có trùng khoá, MERGE sẽ lỗi hoặc cho kết quả không xác định, nên luôn khử trùng
source trước (xem bài advanced/02).
