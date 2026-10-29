# Lời giải: phân khúc khách Olist bằng RFM và k-means

Notebook lời giải: `rfm.ipynb` (chạy được toàn bộ khi đã tải Olist; phần silhouette khoảng 20 giây).

## Dữ liệu

93 350 khách (`customer_unique_id`), chỉ **3.0%** mua từ 2 đơn trở lên. Recency trung vị 221 ngày, monetary
trung vị 107.8 R$, lớn nhất 13 664 R$. Dùng nhầm `customer_id` thì mọi khách đều có frequency = 1.

## Scale

k-means trên RFM thô: bốn cụm chia gần như chỉ theo monetary (0–467, 333–1 191, 1 192–13 664 R$…), vì monetary
có thang lớn nhất. Sau `log1p` + chuẩn hoá, ba chiều được đối xử ngang nhau.

## Chọn k

| k | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| silhouette | 0.718 | 0.409 | 0.394 | 0.359 | 0.352 | 0.354 | 0.345 |

k = 2 tách 2 801 khách mua nhiều lần khỏi 90 549 khách mua một lần: một dòng `frequency > 1` làm được, k-means
không thêm gì. Silhouette đo độ tách hình học, không đo giá trị kinh doanh.

## k = 4

| Cụm | n | share | Recency trung vị | Frequency TB | Monetary trung vị | Tên gợi ý | Hành động |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 801 | 3.0% | 201 | 2.11 | 225.6 | Khách quay lại | Chương trình thân thiết, ưu tiên CSKH |
| 3 | 16 615 | 17.8% | 40 | 1.00 | 104.4 | Mới mua | Khuyến khích đơn thứ hai trong 1–2 tháng |
| 0 | 31 920 | 34.2% | 258 | 1.00 | 199.7 | Lâu rồi, chi nhiều | Win-back có chọn lọc, theo danh mục đã mua |
| 1 | 42 014 | 45.0% | 273 | 1.00 | 65.9 | Lâu rồi, chi ít | Kênh rẻ (email đại trà) hoặc bỏ qua |

(Số thứ tự cụm phụ thuộc seed; đọc theo hồ sơ, không theo số.)

## PCA, DBSCAN

PCA trên 3 chiều đã chuẩn hoá: 38.9%, 33.3%, 27.8% phương sai: không nén được, chỉ dùng để vẽ. DBSCAN trên mẫu
10 000 khách: eps 0.2 / 0.3 / 0.5 cho 1 / 3 / 2 cụm, nhiễu 7.9% / 4.0% / 1.4%: rất nhạy tham số, không có cấu
trúc mật độ rõ.

## Trả lời câu hỏi

1. k = 2 tách theo mua một lần / nhiều lần. Không cần k-means.
2. Xem bảng. Cụm "khách quay lại" giá trị nhất mỗi khách; cụm "mới mua" là cơ hội lớn nhất vì còn nóng và đông.
3. Không hẳn. Với F gần hằng số, RFM theo luật (ngũ phân vị R và M) cho kết quả tương đương, dễ giải thích và
   ổn định hơn. Nếu mục tiêu là "ai sẽ quay lại", dựng model supervised (nhãn: mua lại trong 90 ngày), và thêm
   feature danh mục, vùng, trải nghiệm giao hàng (review xấu làm giảm khả năng quay lại).
4. Đổi seed thì số thứ tự cụm có thể đổi, ranh giới có thể xê dịch. Đội CRM dùng nhãn hằng tháng cần nhãn ổn
   định: cố định tâm cụm từ một lần fit và gán khách mới vào tâm gần nhất, hoặc ánh xạ cụm mới về cụm cũ
   theo hồ sơ.

## Rubric (phần phân tích)

| Tiêu chí | Đạt khi |
| --- | --- |
| Đúng khách | Dùng `customer_unique_id`, giải thích vì sao |
| Scale | Chỉ ra k-means thô bị monetary chi phối |
| Chọn k có lý | Không chọn k = 2 chỉ vì silhouette cao nhất |
| Hành động | Mỗi cụm có tên và hành động cụ thể |
| Phản biện | Nêu giới hạn của RFM ở Olist và phương án khác |
