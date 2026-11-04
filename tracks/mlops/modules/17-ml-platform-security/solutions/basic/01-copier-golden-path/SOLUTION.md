# Lời giải: golden path bằng Copier

`template/` cạnh tệp này là template hoàn chỉnh. Các điểm chính:

- **Câu hỏi bắt buộc không có default.** `owner` và `cost_center` không có `default`, nên `copier copy --defaults` (chế độ không hỏi
  mà CI và test dùng) để trống và validator báo lỗi. Đây là cách ép đội phải trả lời thay vì nhận một giá trị "tạm" mà không ai sửa.
- **Validator là chuỗi Jinja.** Render ra rỗng là hợp lệ. `regex_search` có sẵn trong môi trường Jinja của Copier; Jinja chuẩn không có
  test `match`. `choices` cho `team` và `model_kind` chặn giá trị ngoài danh sách cả khi truyền bằng `--data`.
- **Slug mặc định suy từ tên.** `{{ project_name | trim | lower | replace(' ', '-') }}`, rồi validator kebab-case bắt các trường hợp
  người dùng tự gõ slug sai.
- **Giá trị vào YAML qua `tojson`.** Chuỗi JSON là YAML hợp lệ; câu trả lời có dấu `:` hay `#` không làm hỏng `mlproject.yaml`. Câu trả
  lời đã qua validator, nhưng đây là thói quen đúng với mọi template sinh tệp cấu hình.
- **Tệp câu trả lời** `{{ _copier_conf.answers_file }}.jinja` với `{{ _copier_answers | to_nice_yaml }}`: không có nó thì
  `copier update` không biết dự án sinh từ đâu và với câu trả lời nào, golden path chỉ dùng được một lần.
- **Test canh quy ước nằm trong dự án sinh ra.** Kiểm lúc sinh là chưa đủ: sáu tháng sau ai đó xoá `cost_center` khỏi `mlproject.yaml`,
  CI của chính dự án phải đỏ. Template sinh cả test này, nên mọi dự án đều có nó mà không ai phải nhớ.
- **Không dùng `_tasks`.** Task chạy lệnh shell tuỳ ý trên máy người chạy `copier copy`, nên Copier đòi `--trust`. Template nền tảng
  nên chạy được không cần trust; việc cần chạy (cài dependency, `git init`) để trong `README` hay Makefile của dự án.

Đuôi `.py.jinja` cho mọi tệp Python của template (kể cả không có biến) để pytest của repo không thu thập `tests/` của template như test
thật. Trong repo template riêng (thường là vậy ở công ty), vấn đề này không có.

**Mở rộng ở nơi làm việc.** Template sống trong repo riêng có tag phiên bản; `copier update` kéo thay đổi (vd. thêm job quét model vào CI)
về mọi dự án, xung đột hiện như merge. Một job định kỳ của nền tảng liệt kê dự án có `.copier-answers.yml` với `_commit` cũ để nhắc cập nhật.
