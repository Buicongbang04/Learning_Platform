# Lời giải: classifier phân biệt hai tập

**Ý tưởng.** Nếu một model không phân biệt nổi dữ liệu cũ và mới thì chúng cùng phân phối (AUC ≈ 0.5). Nếu phân biệt được (AUC cao), có thứ gì đó khác nhau, kể cả quan hệ giữa các cột, thứ mà PSI từng cột không thấy.
Kiểm chứng trong bài: tương quan đổi từ +0.9 sang -0.9, phân phối biên giữ nguyên, PSI từng cột gần 0 nhưng AUC trên 0.85.

**Chi tiết quan trọng.**

- **Cross-validation.** AUC trên dữ liệu đã dùng để học luôn cao (rừng ngẫu nhiên nhớ được). Chỉ AUC của dự đoán out-of-fold mới có nghĩa.
- **Mẫu cân bằng và giới hạn.** `max_rows` mỗi tập giữ thời gian chạy ổn định và hai lớp cân bằng; AUC không phụ thuộc cỡ mẫu nhiều như p-value.
- **NaN thành -1** để tỉ lệ thiếu cũng là tín hiệu (trên TLC 2020-04, `passenger_count` thiếu 8.2% so với 0.8% trước đó góp phần đáng kể vào AUC).
- **`driver_features`** cho biết cột nào đóng góp nhiều nhất vào việc phân biệt: bước đầu của "drift đến từ đâu". Importance của rừng ngẫu nhiên thiên về cột liên tục; coi là gợi ý, đừng coi là nguyên nhân.

**Số đo thật** (mẫu 20 000 dòng mỗi tập, 4 feature): 2019-07 sang 2019-12 cho AUC ≈ 0.52 (gần như không phân biệt được), 2020-02 sang 2020-04 cho AUC ≈ 0.73. Importance trên cặp COVID: `PULocationID` 0.34,
`passenger_count` 0.29, `hour` 0.27, `trip_distance` 0.10.

**Giới hạn.** AUC cao nói "khác", không nói "tệ": mùa lễ có thể cho AUC rất cao mà model vẫn đúng. Giống mọi tín hiệu drift, nó chỉ là bước *detect*; *impact* vẫn cần nhãn hoặc proxy.
Đánh đổi khác: classifier khó giải thích hơn PSI và tốn thêm một lần fit mỗi lần kiểm; thường chạy hằng ngày hay hằng tuần, không chạy theo từng request.
