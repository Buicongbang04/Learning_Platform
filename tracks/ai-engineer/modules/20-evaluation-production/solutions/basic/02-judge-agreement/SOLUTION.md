# Lời giải: độ khớp của judge và đổi chỗ khi so cặp

## Cách làm

- `cohen_kappa`: $$p_o$$ là tỉ lệ vị trí hai dãy bằng nhau; `Counter` cho tần suất biên, $$p_e = \sum_c n_A(c)\,n_B(c)/n^2$$.
  $$p_e = 1$$ chỉ xảy ra khi cả hai cùng dùng đúng một nhãn: kappa không xác định, trả `nan` (sklearn cũng vậy).
- `calibration_report`: lọc `None` **trước**, rồi mọi tỉ lệ tính trên phần còn lại; `false_pass` có mẫu số là số câu người
  chấm `False`, `false_fail` có mẫu số là số câu người chấm `True`.
- `resolve_swap`: hai bảng tra, một cho lượt A đứng trước (`first` là A), một cho lượt B đứng trước (`first` là B); hai kết
  quả khác nhau là `inconsistent`.
- `pairwise_summary`: đếm bằng `Counter` trên kết quả của `resolve_swap`; `first_rate` tính trên mọi verdict không phải
  `tie` của cả hai lượt.

## Vì sao như vậy

- **Kappa thay accuracy**: test có ca 90% khớp mà kappa bằng 0 (một bên luôn nói "đạt"). Judge trên tập mất cân bằng (đa
  số câu trả lời tốt) cho accuracy cao mà không phân biệt được gì.
- **Hướng sai quan trọng hơn con số tổng**: hai judge cùng accuracy 0.8 có thể một cái dễ dãi, một cái khắt khe. Judge
  dùng làm cổng chặn hồi quy mà dễ dãi thì để lọt đúng loại lỗi cần chặn.
- **Inconsistent tính nửa trận** (như hoà) vì nó không phải bằng chứng cho bên nào: judge đổi ý khi đổi chỗ nghĩa là vị trí
  quyết định chứ không phải nội dung. Lấy verdict của lượt đầu thì thiên vị vị trí đi thẳng vào kết quả.
- `first_rate` gần 0.5 là không thiên vị vị trí; một judge luôn chọn đoạn đứng trước có `first_rate` 1.0 và tỉ lệ thắng
  của A đúng 0.5, dù nó "chọn" ở mọi lượt. Bài Intermediate 01 đo các số này trên judge thật.

## Lỗi hay gặp

- Tính $$p_e$$ từ tần suất của **một** người chấm, hoặc bình phương tần suất trung bình.
- Để `None` vào `bool()` thành `False`: verdict không đọc được biến thành "judge từ chối", làm `false_fail` phồng lên.
- Đảo nhầm bảng tra ở lượt hai, làm judge thiên vị vị trí trông như rất nhất quán.
- Tính `first_rate` trên số cặp thay vì số verdict, hoặc tính cả verdict `tie` vào mẫu số.
