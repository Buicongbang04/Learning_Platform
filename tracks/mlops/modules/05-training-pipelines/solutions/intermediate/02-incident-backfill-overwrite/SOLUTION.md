# Lời giải: backfill làm đổi số liệu các tháng cũ

## Nguyên nhân

`load_month` giữ dữ liệu đã đọc trong một dict cấp module (`_LOADED`) "để khỏi đọc lại tệp", nhưng khoá của dict là **thư mục dữ
liệu**, không phải tháng. Lần gọi đầu của một lần chạy đọc tệp tháng 8 và lưu dưới khoá `data_dir`; tháng 9 và tháng 10 cùng
`data_dir` nên trúng cache và dùng lại DataFrame của tháng 8. Cả ba tháng ra cùng `rows`, `mean_duration`, `mae`, rồi ghi đè lên
kết quả đúng đã có của tháng 9 và 10.

Vì sao chỉ lộ ra khi backfill: lệnh chạy hằng tháng chỉ xử lý một tháng, cache nhìn "đúng" vì chỉ có một tháng để đọc. Flow còn
xoá `_LOADED` ở đầu mỗi lần chạy nên không có rò rỉ giữa các lần chạy, và đó là lý do chạy riêng từng tháng ra số đúng. Không lỗi,
không cảnh báo: mọi thứ chạy "thành công", chỉ có con số sai, và cái sai ghi đè lên cái đúng.

## Cách sửa

Bỏ cache cấp module (đọc tệp mỗi lần cần; chi phí không đáng kể so với train). Nếu thật sự cần cache thì khoá phải gồm **mọi
thứ quyết định đầu ra**: `(data_dir, month)`, và tốt hơn là hash nội dung như bài 03. Mã sửa ở `monthly.py` cạnh tệp này.

## Rộng hơn bài này

- **Trạng thái chung biến "hàm thuần" thành hàm phụ thuộc lịch sử.** Cache, biến toàn cục, singleton, tệp tạm có tên cố định đều
  là chỗ một tháng nhìn thấy dấu vết của tháng trước. Đặc điểm nhận dạng: kết quả phụ thuộc vào cái đã chạy trước đó trong cùng
  tiến trình.
- **Ghi đè kết quả đúng bằng kết quả sai là lỗi nặng hơn không chạy.** Backfill nên ghi sang vị trí tạm rồi so sánh với kết quả
  cũ (diff số liệu theo tháng) trước khi thay; một cổng "tháng nào đổi quá X% so với bản cũ" bắt được ca này ngay.
- **Kiểm thử bằng bất biến:** "kết quả một tháng không phụ thuộc thứ tự và không phụ thuộc các tháng khác trong đợt" là một thuộc
  tính test được, rẻ hơn nhiều so với truy ngược sau sự cố. Các test của bài này kiểm đúng thuộc tính đó.
- **Sau khi sửa:** khôi phục số liệu tháng 9 và 10 từ bản sao lưu hoặc chạy lại từng tháng, rồi thêm kiểm tra đối soát
  (`rows` trong kết quả bằng số dòng thật của tệp nguồn) vào cuối mỗi lần chạy.
