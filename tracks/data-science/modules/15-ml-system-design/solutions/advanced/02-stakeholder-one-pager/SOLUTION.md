# Hướng làm: memo một trang

## Số liệu tham chiếu

Giả định cơ sở: 70 cảnh báo mỗi tuần, precision 0.391, Δ = 0.15, V = 30 R$, tin nhắn 0.5 R$ →
**88.2 R$ mỗi tuần**. Với khoảng trong test (Δ 0.05–0.25, V 5–60 R$, precision 0.33–0.45, chi phí
0.2–1.0 R$, 50–140 cảnh báo/tuần):

| Giả định | Giá trị ở cận thấp | Giá trị ở cận cao | Swing |
| --- | --- | --- | --- |
| V (thiệt hại một review xấu) | −14.5 | 211.3 | 225.8 |
| Δ (tác động tin nhắn) | 6.1 | 170.3 | 164.2 |
| Số cảnh báo / tuần | 63.0 | 176.3 | 113.4 |
| Chi phí tin nhắn | 109.2 | 53.2 | 56.0 |
| Precision | 69.0 | 106.8 | 37.8 |

Kịch bản: bi quan −45.9 R$/tuần, cơ sở 88.2, lạc quan 917.0. Hoà vốn khi V ≥ 8.5 R$ (giữ Δ = 0.15), hoặc
Δ ≥ 0.043 (giữ V = 30 R$), hoặc chi phí tin nhắn ≤ 1.76 R$.

Đọc: model (precision) là giả định **ít** quan trọng nhất. Hai giả định business (V, Δ) chiếm phần lớn
bất định, và chưa ai đo chúng. Một memo tốt vì thế khuyến nghị **đo V và Δ** bằng thí nghiệm rẻ, không
khuyến nghị đầu tư model.

## Memo mẫu (rút gọn)

> **Khuyến nghị.** Chạy thử 8 tuần tin nhắn tự động xin lỗi và báo ngày giao mới cho đơn còn dưới 5
> ngày tới ngày hẹn lúc giao cho vận chuyển, chia ngẫu nhiên 50/50 để đo tác động. Chi phí tin nhắn
> khoảng 280 R$. Chưa xây model ML cho tới khi có kết quả. Cần COO duyệt trước cuối tháng.
>
> **Vì sao.** 8.1% đơn giao trễ; 54.1% đơn trễ nhận review 1–2 sao so với 9.2% đơn đúng hẹn. Mỗi tuần
> trung vị 61 đơn trễ, tuần khủng hoảng tới 565.
>
> **Con số chính.** Giả định cơ sở cho khoảng 88 R$ mỗi tuần; bi quan lỗ 46 R$, lạc quan 917 R$. Kết
> quả phụ thuộc gần như hoàn toàn vào hai câu hỏi chưa ai đo: một review xấu thiệt bao nhiêu, và tin
> nhắn có làm khách bớt bực không. Hệ thống hoà vốn nếu một review xấu thiệt từ 8.5 R$ trở lên. Dữ liệu
> mua lại chỉ giải thích khoảng 0.36 R$, nên phần còn lại phải đến từ uy tín sàn và chi phí CSKH: cần
> đội tài chính xác nhận.
>
> **Rủi ro và điều chưa biết.** Tin nhắn có thể làm khách không để lại review thay vì review tốt hơn
> (theo dõi tỉ lệ có review); 8 tuần ở quy mô này có thể chưa đủ để thấy tác động nhỏ (đo thêm tỉ lệ
> liên hệ CSKH, phản hồi nhanh hơn); khách vùng Bắc / Đông Bắc bị cảnh báo nhầm nhiều hơn.
>
> **Cần quyết định.** COO: duyệt chạy thử. Trưởng CSKH: chỉ định người theo dõi phản hồi. Tài chính:
> ước lượng thiệt hại một review xấu trước tuần thứ 4.

(Chi phí: luật "còn dưới 5 ngày" cảnh báo 1 596 đơn trong 23 tuần test, khoảng 69 đơn mỗi tuần; 8 tuần
× 69 × 0.5 R$ ≈ 280 R$.)

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| BLUF | 20 | Câu đầu là hành động cụ thể, thời gian, chi phí, người quyết |
| Con số đúng và có nguồn | 15 | Mọi số tính từ dữ liệu / code; không có AUC trần trụi |
| Bất định | 20 | Kịch bản bi quan / cơ sở / lạc quan; nêu giả định nhạy nhất; điểm hoà vốn bằng ngôn ngữ kinh doanh |
| Trung thực | 15 | Nói rõ giá trị nhỏ hoặc chưa chắc nếu đúng vậy; tách đã đo / ước lượng / giả định |
| Rủi ro | 10 | Ít nhất 2 rủi ro kèm cách phát hiện sớm |
| Quyết định | 10 | Ai, quyết gì, khi nào |
| Ngắn gọn | 10 | Một trang, người đọc không phải là DS hiểu được |

## Sai lầm hay gặp

- Mở đầu bằng phương pháp ("Nhóm đã xây model LightGBM…").
- Một con số duy nhất không có khoảng.
- Đề xuất xây hệ thống ML khi tornado cho thấy bất định nằm ở giả định business.
- Khoảng giả định chọn tuỳ tiện, không ghi lý do.
