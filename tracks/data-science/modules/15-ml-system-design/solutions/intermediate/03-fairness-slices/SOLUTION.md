# Lời giải: fairness theo vùng

Notebook lời giải: `fairness.ipynb` (chạy được toàn bộ khi đã tải Olist).

## Kết quả trên Olist thật

Tỉ lệ trễ trên 96 470 đơn giao xong: Bắc / Đông Bắc 13.6%, São Paulo 5.9%, bang khác 8.8%. Top 5% tập
test (1 607 đơn) theo model lúc giao vận chuyển:

| Vùng | Selection rate | Precision | Recall | FPR | Phần cảnh báo | Phần đơn trễ |
| --- | --- | --- | --- | --- | --- | --- |
| N/NE | 17.0% | 20.6% | 31.7% | 15.2% | 35.0% | 18.9% |
| SP | 4.4% | 60.1% | 43.6% | 1.9% | 40.6% | 46.4% |
| khác | 2.8% | 30.5% | 17.9% | 2.0% | 24.5% | 34.7% |

Model lúc đặt hàng đẩy 50.0% cảnh báo về N/NE, recall SP chỉ 4.4%: model yếu dùng vùng làm proxy.

Chia ngân sách theo nhu cầu: recall N/NE 20.8%, SP 44.2%, khác 23.5%; số đơn trễ được nhắn 628 → 631,
giá trị 2 022.5 → 2 036 R$ trên tập test.

## Cách nghĩ

- Can thiệp có lợi (nhắn tin hỗ trợ) → equal opportunity (recall) là metric fairness chính; FPR là chi
  phí làm phiền. Can thiệp có hại (khoá tài khoản) thì ngược lại.
- Chênh lệch precision giữa vùng phần lớn là hệ quả tỉ lệ nền và độ khó phân biệt trong vùng, không thể
  xoá cùng lúc với chênh lệch recall (Kleinberg et al.; Chouldechova).
- Biện pháp nào cũng đổi lợi của nhóm này lấy lợi của nhóm khác. DS trình bày bảng trước / sau và giá
  trị; quyết định thuộc về business và legal.

## Rubric cho câu trả lời

| Tiêu chí | Đạt khi |
| --- | --- |
| Chọn đúng metric | Gắn metric fairness với bản chất can thiệp (có lợi / có hại) |
| Đọc bảng đúng | Phân biệt "được chọn nhiều" với "được giúp đúng" |
| Hiểu giới hạn | Nhắc tới impossibility khi tỉ lệ nền khác nhau |
| Đề xuất có giá | Nêu biện pháp kèm giá trị mất / được và nhóm bị ảnh hưởng |
| Proxy | Giải thích vì sao bỏ cột vùng không giải quyết vấn đề |

## Bẫy thường gặp

- Chỉ báo selection rate (demographic parity) cho một can thiệp có lợi: N/NE "được ưu ái" nhưng phần lớn
  là cảnh báo nhầm.
- Báo cáo metric nhóm trên tập nhỏ mà không có khoảng tin cậy: N/NE chỉ có 3 298 đơn test, khoảng 366 đơn
  trễ.
- Dùng `idxmin` cho FPR rồi gọi nhóm có FPR thấp nhất là "tệ nhất".
