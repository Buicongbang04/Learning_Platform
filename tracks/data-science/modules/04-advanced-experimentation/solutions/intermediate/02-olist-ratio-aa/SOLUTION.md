# Lời giải: ratio metric trên Olist, kiểm bằng A/A

Notebook lời giải: `ratio_aa.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Cách làm

- `load_items` lọc đơn giao xong **trước** khi nối với items, rồi nối `customer_id` sang
  `customer_unique_id`. Mỗi lần mua Olist tạo một `customer_id` mới, nên random theo `customer_id`
  sẽ chia cùng một người vào hai nhánh.
- `delta_test` tính tỉ số và variance delta method trên bảng theo khách, mỗi nhánh riêng.
- `aa_study` dựng bảng và mã khách một lần, mỗi vòng chỉ lập chỉ mục numpy: 2 000 lần A/A trên
  93 350 khách chạy khoảng 8 giây.

## Kết quả trên Olist thật

| Con số | Giá trị |
| --- | --- |
| Sản phẩm / đơn / khách | 110 189 / 96 470 / 93 350 |
| Khách có từ 2 sản phẩm | 12.4% |
| Giá trung bình mỗi sản phẩm | 119.98 |
| Phân nhóm hash (salt `olist-aov-aa`) | 46 658 / 46 692 khách, SRM p = 0.91 |
| SE delta / SE ngây thơ | 1.1892 / 1.0984 |
| Design effect | 1.172 |
| A/A 2 000 lần, tỉ lệ p < 0.05 | delta 5.3%, ngây thơ 7.3% (lý thuyết từ design effect: 7.0%) |
| Power khi cài +2% giá, 500 lần | 51.8% |

Đọc: cách tính ngây thơ sai ít trên Olist vì cụm nhỏ (đa số khách mua một sản phẩm). Nhưng "ít"
vẫn là 46% báo động nhầm nhiều hơn mức danh nghĩa (7.3% so với 5%), và nhân lên với hàng trăm thí
nghiệm mỗi năm thì đủ để ship vài thay đổi vô dụng. Power 51.8% ở +2% cho thấy dù dùng toàn bộ hai
năm dữ liệu, thí nghiệm về giá trên Olist vẫn chỉ phát hiện tốt những thay đổi lớn hơn 2%.

## Rubric cho phần kết luận

| Tiêu chí | Đạt khi |
| --- | --- |
| Con số | Nêu tỉ lệ A/A của hai cách và design effect |
| Giải thích | Liên hệ độ lớn sai lệch với cỡ cụm (số sản phẩm mỗi khách) |
| Khái quát | Chỉ ra khi nào sai lệch lớn: nhiều quan sát trên mỗi đơn vị random |
| Chọn OEC | Phân biệt metric tỉ số (chẩn đoán) với metric theo đơn vị random (OEC), có lý do kinh doanh |

## Sai lầm hay gặp

- Dùng `customer_id` thay cho `customer_unique_id`.
- Bootstrap theo **sản phẩm** để "kiểm tra lại": mắc đúng lỗi của cách ngây thơ. Bootstrap phải
  resample khách.
- Kết luận "delta method không cần thiết vì chỉ lệch 2 điểm phần trăm": kết luận trên Olist không
  chuyển sang được sản phẩm có cụm lớn. Kiểm A/A trên chính dữ liệu của sản phẩm mình.
- A/A chỉ chạy một lần rồi thấy p > 0.05 và kết luận "hệ thống ổn". Một lần A/A không nói gì về
  tỉ lệ báo động nhầm; cần hàng trăm, hàng nghìn lần.
