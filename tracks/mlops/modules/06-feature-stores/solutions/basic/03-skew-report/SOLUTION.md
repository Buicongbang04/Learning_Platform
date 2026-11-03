# Lời giải: báo cáo skew

`skew.py` cạnh tệp này, đáp án trắc nghiệm ở `quiz-answers.yaml`.

- **Báo cáo theo loại lỗi, không chỉ "có lệch".** `null_mismatch` gợi ý default khác nhau hoặc join thiếu; `value_mismatch` với
  `max_abs_diff` nhỏ gợi ý làm tròn hay kiểu số; `max_abs_diff` lớn và `mismatch_rate` gần 1 trên một cột gợi ý biến đổi khác nhau ở
  hai đường. Con số này quyết định bạn tìm ở đâu trước.
- **So trên cùng thực thể, không so phân phối.** So histogram báo drift (thế giới đổi); skew phải so cùng khoá, vì hai đường
  tính trên cùng một chuyến mà vẫn ra số khác nhau thì lỗi nằm trong mã, không trong dữ liệu.
- **Inner join cho giá trị, và `row_coverage` riêng cho khoá lệch.** Một log serve thiếu 1% yêu cầu là vấn đề khác với giá
  trị lệch; lẫn hai thứ sẽ làm tỉ lệ lệch sai.
- **Ngưỡng `rtol`/`atol`** giữ nhiễu dấu phẩy động (`1e-9`) khỏi báo động giả; ngưỡng thật nên chọn theo độ nhạy của model.
- Thứ tự sắp xếp xác định giúp báo cáo diff được giữa hai lần chạy.

Lỗi hay gặp: `a != b` coi `NaN != NaN` là lệch; so cột số nguyên có null (chuyển `float`) với cột `int` bằng `==` hợp lệ nhưng
`np.isclose` trên `object` thì lỗi.
