# Hướng làm: funnel plot seller và đặc tả dashboard

## Funnel plot

Ý tưởng (Spiegelhalter, 2005): nếu mọi seller có cùng tỉ lệ trễ thật bằng tỉ lệ chung, tỉ lệ quan
sát của seller có n đơn dao động quanh tỉ lệ chung với độ lệch chuẩn tỉ lệ nghịch với căn n. Vẽ giới
hạn kiểm soát theo n tạo hình phễu: seller nhỏ có biên rộng, seller lớn có biên hẹp. Chỉ điểm nằm
ngoài phễu mới có bằng chứng khác biệt.

Cài đặt: `groupby` lấy n và số đơn trễ, tỉ lệ chung $$p$$ từ toàn bảng, giới hạn
$$p \pm z\sqrt{p(1-p)/n}$$ cắt vào [0, 1], `excess` = số đơn trễ vượt kỳ vọng. `alerts` lọc `above`
với n tối thiểu và sắp theo `excess`, vì đó là **số khách bị ảnh hưởng thêm**, thứ đội vận hành cần
ưu tiên, không phải tỉ lệ.

Kết quả trên Olist thật (96 470 đơn giao xong, seller của item đầu tiên):

| Con số | Giá trị |
| --- | --- |
| Seller | 2 960 |
| Tỉ lệ trễ chung | 8.11% |
| Seller có tỉ lệ trễ 100% | 58 (trên mọi đơn giao xong; 56 nếu chỉ tính đơn có review), tất cả có tối đa 2 đơn |
| Top 10 theo tỉ lệ thô | 10 seller có 1–2 đơn |
| `flag = above` | 140 seller, trong đó 99 có dưới 20 đơn (xấp xỉ normal kém ở n nhỏ) |
| `alerts(min_n=20)` | 41 seller, chiếm 17.1% số đơn trễ |
| Đứng đầu | `06a2c3af…`: 90/388 đơn trễ, vượt kỳ vọng khoảng 58 đơn |

Đánh đổi cần bàn: xấp xỉ normal đơn giản, giải thích được, nhưng báo nhầm ở n nhỏ (cần `min_n`); giới
hạn nhị thức chính xác tốt hơn ở n nhỏ; với nhiều kỳ và nhiều seller, kiểm soát báo động nhầm (z = 3
cho khoảng 0.13% mỗi phía mỗi seller mỗi kỳ, nhân với 2 960 seller là vài báo động nhầm mỗi kỳ);
shrinkage (empirical Bayes) cho xếp hạng ổn định hơn.

## Đặc tả dashboard: những gì một bản tốt có

- **Người dùng và quyết định**: trưởng nhóm quản lý seller, mỗi thứ Hai, quyết định gọi cho seller
  nào. Không dùng để phạt tự động.
- **KPI** (3–5): tỉ lệ trễ (đơn giao xong, theo tuần mua, chỉ tuần đã chín), số đơn trễ vượt kỳ vọng
  của nhóm seller được cảnh báo, tỉ lệ review xấu, thời gian giao trung vị. Mỗi KPI có định nghĩa, kỳ
  so sánh, chủ sở hữu.
- **Biểu đồ**: line theo tuần (chỉ tuần đã chín, tuần đang chín tô nhạt); funnel plot seller (trục n
  thang log); bảng cảnh báo sắp theo `excess`, có n, tỉ lệ, CI. Tiêu đề dạng kết luận sinh tự động
  ("41 seller trễ vượt mức chung, gây thêm khoảng X đơn trễ").
- **Cảnh báo**: z, `min_n`, cửa sổ (ví dụ 8 tuần trượt) chọn trước, kèm ước lượng số cảnh báo mỗi kỳ
  trên dữ liệu lịch sử; seller mới có giai đoạn làm quen.
- **Độ chín và chất lượng**: một tuần chỉ hiện khi đơn của tuần đó đã giao xong phần lớn (ví dụ 30
  ngày); trước khi làm mới chạy báo cáo chất lượng (bài Intermediate 01); pipeline lỗi thì hiện
  banner thay vì số cũ.
- **Giới hạn**: trễ có thể do hãng vận chuyển, khoảng cách, ngày hẹn quá chặt, không chỉ seller; so
  sánh công bằng hơn khi kiểm soát tuyến (bang seller → bang khách). Rủi ro Goodhart: seller nới ngày
  hẹn để giảm "trễ"; theo dõi thêm số ngày hẹn trung vị theo seller.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Funnel và cảnh báo đúng | 20 | Hàm đúng; giải thích vì sao không xếp hạng theo tỉ lệ thô, có số thật (seller 1–2 đơn) |
| Funnel plot | 10 | Trục n thang log, giới hạn rõ, điểm được cảnh báo nổi bật, tiêu đề là kết luận |
| Người dùng và quyết định | 10 | Cụ thể ai, khi nào, làm gì; nói rõ dashboard không dùng để làm gì |
| KPI | 15 | 3–5 KPI có định nghĩa đầy đủ (tử, mẫu, cửa sổ), kỳ so sánh, chủ sở hữu |
| Quy tắc cảnh báo | 15 | z, `min_n`, cửa sổ có lý do; ước lượng số cảnh báo và báo động nhầm; bàn normal và nhị thức chính xác |
| Độ chín và chất lượng dữ liệu | 15 | Quy tắc kỳ chưa chín; kiểm tra chất lượng trước khi làm mới; hành vi khi pipeline lỗi |
| Giới hạn và rủi ro | 15 | Trễ không chỉ do seller; rủi ro Goodhart và cách phát hiện |

Đạt từ 70 điểm trở lên là đủ để đội BI dựng và đội vận hành dùng thử.
