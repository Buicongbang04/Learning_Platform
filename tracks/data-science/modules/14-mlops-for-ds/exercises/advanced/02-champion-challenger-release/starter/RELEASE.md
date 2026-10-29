# Kế hoạch phát hành model review xấu v2

Người đọc: PM của đội CSKH, kỹ sư vận hành service, DS khác review. Xoá mọi dòng TODO khi viết
xong. Mọi con số phải đến từ code bạn chạy trên Olist thật.

## 1. Model card

TODO: model làm gì, thời điểm dự đoán (lúc đơn vừa giao xong) và vì sao điều đó quan trọng, dữ liệu
train (khoảng ngày, số đơn, tỉ lệ review xấu), feature, metric trên validation và test, các nhóm mà
model kém hơn, những cách dùng **không** được phép.

## 2. Champion và challenger

TODO: hai model khác nhau thế nào (feature, thuật toán, dữ liệu train), kết quả offline của cả hai
trên cùng tập test.

## 3. Lộ trình phát hành

TODO: shadow (bao lâu, đo gì), canary (bao nhiêu % traffic, bao lâu), toàn bộ. Điều kiện chuyển
bước và điều kiện dừng. Nhãn về trễ ảnh hưởng thời lượng mỗi bước thế nào.

## 4. Quy tắc promote

TODO: ngưỡng của `promotion_decision` bạn chọn và lý do kinh doanh của từng ngưỡng.

## 5. Monitoring sau phát hành

TODO: chỉ số nào, cửa sổ nào, ngưỡng nào, ai nhận cảnh báo.

## 6. Rollback

TODO: khi nào rollback, ai quyết định, mất bao lâu, cái gì không rollback được (quyết định liên hệ
khách đã gửi).
