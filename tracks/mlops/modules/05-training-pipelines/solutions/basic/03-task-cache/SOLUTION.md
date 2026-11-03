# Lời giải: cache task theo nội dung dữ liệu

Mã nằm trong `cached.py` cạnh tệp này; đáp án quiz ở `quiz-answers.yaml`.

## Vì sao khoá là nội dung, không phải đường dẫn

`cache_policy=INPUTS` (mặc định khi bật cache) băm giá trị các đối số. Đường dẫn `data/trips.csv` là cùng một chuỗi dù hôm nay
chứa tháng 9 và tuần sau chứa tháng 10; cache trúng và trả metrics của dữ liệu cũ. Không có lỗi, không có cảnh báo, chỉ có số
sai. Đây là lỗi cache phổ biến nhất trong pipeline dữ liệu: khoá chỉ nhìn **tên** của đầu vào thay vì **nội dung**.

Khoá đúng gồm mọi thứ làm đầu ra đổi: hash nội dung dữ liệu, tham số, seed. Một thứ nữa là **phiên bản code**: sửa hàm train mà
không đổi khoá thì cache trả model của logic cũ. Bài này không đưa code vào khoá để giữ đơn giản; ở production thêm git commit
hoặc digest image vào khoá, hoặc dùng `cache_expiration` ngắn.

## Các quyết định

- **Băm nội dung với tệp nhỏ, băm siêu dữ liệu với tệp lớn.** Đọc cả tệp 20 GB để tính khoá tốn hơn train. Khi đó dùng hash do
  hệ thống dữ liệu cung cấp (DVC `md5`, ETag của S3, snapshot id của Iceberg), vẫn là "nội dung" nhưng không phải đọc lại.
- **Kết quả cache là dict nhỏ.** Cache lưu giá trị trả về; trả cả model lớn làm kho kết quả phình. Lưu model ra artifact store và
  trả đường dẫn kèm hash.
- **Cache và tác dụng phụ.** Khi trúng cache, thân task không chạy, nên tệp mà thân task ghi ra không được tạo lại. Task có tác
  dụng phụ cần cache cùng cơ chế kiểm "đầu ra còn tồn tại" hoặc không nên cache.
- **Cache không thay thế tái lập.** Cache làm bạn **không chạy lại**; một pipeline không tái lập vẫn trông ổn cho tới ngày cache
  hết hạn.

## Lỗi hay gặp

- Dùng `refresh_cache` hoặc xoá thư mục kết quả mỗi khi nghi ngờ thay vì sửa khoá.
- Đưa timestamp hoặc `run_id` vào khoá: cache không bao giờ trúng.
- Cache cả bước gọi API thời gian thực.
