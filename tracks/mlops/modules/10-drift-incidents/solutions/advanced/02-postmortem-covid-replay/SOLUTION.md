# Hướng làm và rubric: postmortem COVID

## Hướng làm

1. **Số đo thật làm trục.** Trên 2020-02 sang 2020-04: PSI `hour` 0.152, `fare_amount` 0.050, `trip_distance` 0.023 (đều thấp tới vừa), `passenger_count` thiếu 8.2% (từ 0.8%); MAE 3.10 sang 5.01 (+62%), thiên lệch dự đoán +4.4 phút; AUC phân biệt hai tháng 0.73.
   Điểm cốt lõi của phần phát hiện: drift đầu vào **ở mức vừa**, chất lượng giảm **mạnh**; chỉ nhãn (hoặc proxy như dự đoán cao hơn baseline) lộ ra.
2. **Dòng thời gian bằng vai trò.** Vd. "Ngày N, 09:00: giám sát báo `hour` PSI 0.15 và tỉ lệ thiếu tăng (mức cảnh báo thấp); on-call xếp vào hàng đợi. Ngày N+1, 10:00: nhãn của ngày N-1 về, MAE tăng 40%; on-call nâng mức..."
   Đánh dấu rõ giả định.
3. **Nguyên nhân hệ thống** (chuỗi): (a) hành vi đi lại đổi đột ngột và bền vững (nguyên nhân bên ngoài, không sửa được); (b) cảnh báo chỉ dựa trên PSI, PSI thấp với loại thay đổi này (phát hiện không phản ánh tác động);
   (c) nhãn trễ 1 ngày và không có proxy phân phối dự đoán so với baseline; (d) không có sẵn pipeline retrain nhanh hay phiên bản dự phòng đã huấn luyện trên dữ liệu gần hơn. Mỗi mắt xích là một điểm hệ thống có thể sửa.
4. **Tốt và may mắn.** Tốt: có nhãn về mỗi ngày, có registry để chuyển phiên bản. May: sự cố rơi vào giai đoạn lưu lượng giảm nên số dự đoán sai tuyệt đối ít.
5. **Hành động tốt** (mẫu): thêm proxy "độ lệch dự đoán so với baseline cùng thứ" cảnh báo cấp trung (phát hiện sớm; chủ: chủ model; hạn 2 tuần; kiểm: bắn đúng trên bản phát lại 2020-02 tới 2020-04); rút ngắn trễ nhãn hoặc thêm ước lượng chất lượng
   (phát hiện sớm); pipeline retrain cửa sổ gần đây chạy trong 4 giờ (giảm thiệt hại; chủ: nền tảng ML; kiểm: diễn tập hằng quý); cảnh báo tổ hợp (nhiều PSI vừa cộng AUC miền) (phát hiện sớm); runbook có nhánh "chất lượng giảm không có bản trước tốt hơn".
6. **Không đổ lỗi.** Câu hỏi là "hệ thống nào để một cảnh báo PSI thấp đi qua", không phải "ai bỏ qua nó". Dùng vai trò, mô tả điều đã biết lúc đó, và các lựa chọn hợp lý tại thời điểm đó.

## Rubric (tối đa 20 điểm)

| Mục | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Tóm tắt và tác động | 3 | người ngoài hiểu được; có số thật (MAE, độ lệch, thời gian) |
| Dòng thời gian | 3 | có mốc, vai trò, giả định được đánh dấu |
| Phát hiện | 4 | giải thích PSI thấp vì sao chưa đủ, tín hiệu nào bù vào, vì sao không sớm hơn |
| Nguyên nhân gốc | 4 | chuỗi hệ thống, không dừng ở "thế giới đổi", không quy lỗi cá nhân |
| Tốt và may | 1 | có cả hai |
| Hành động | 5 | chủ sở hữu (vai trò), hạn, cách kiểm; có phát hiện sớm và giảm thiệt hại |

Trừ điểm: nêu tên hay quy lỗi cho cá nhân (-4); "cẩn thận hơn" hay "theo dõi sát hơn" làm hành động không có chủ, hạn hay cách kiểm (-3); bịa số đo trái với số thật mà không ghi giả định (-2). Mức đạt: 14/20.
