---
title: Cache task theo nội dung dữ liệu và tham số - chạy lại không train lại
level: basic
services: []
files:
  - path: starter/cached.py
    note: 1 hàm TODO và 1 task cần gắn cache
  - path: tests/test_cache.py
    note: Không sửa
  - path: tests/conftest.py
    note: Dựng Prefect tạm và thư mục lưu kết quả tạm, không sửa
  - path: quiz.yaml
    note: Trắc nghiệm về cache và tái lập
run:
  - uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/basic/03-task-cache -q
---

## Mục tiêu

Dùng cache của Prefect để chạy lại một flow với cùng đầu vào thì **không** train lại, và chọn đúng khoá cache: khoá sai làm
bạn nhận lại kết quả cũ trong khi dữ liệu đã đổi.

## Đề bài

`starter/cached.py` có task `fit(data_path, n_estimators, seed)` train một model nhỏ từ tệp CSV và trả dict
`{"r2", "rows", "n_estimators", "seed"}`; mỗi lần thân task chạy thật, nó thêm một mục vào `CALLS`. Flow `train_flow` gọi `fit`.

1. Cài `data_cache_key(context, parameters) -> str`: khoá cache từ **nội dung** tệp dữ liệu (sha256 các byte) cùng
   `n_estimators` và `seed`. Test gọi nó trực tiếp với `context=None`, nên không dùng `context`.
2. Gắn nó vào task: `@task(cache_key_fn=data_cache_key)`.

Quy tắc test ép:

- cùng tệp (cùng nội dung), cùng `n_estimators`, cùng `seed`: khoá bằng nhau, lần chạy thứ hai không gọi thân task (`len(CALLS)`
  vẫn 1) và trả kết quả giống hệt;
- đổi `n_estimators` hoặc `seed`: khoá khác, train lại;
- **ghi đè tệp ở cùng đường dẫn** bằng dữ liệu khác: khoá khác, train lại;
- `touch` tệp hoặc sao chép sang đường dẫn khác với cùng nội dung: khoá không đổi.

Test dựng Prefect tạm và đặt thư mục lưu kết quả của Prefect vào thư mục tạm, nên cache không rò sang lần chạy khác. Làm thêm
`quiz.yaml` (4 câu) sau khi xong phần code.

## Tiêu chí đạt

- Chạy `train_flow` hai lần với cùng đối số thì `CALLS` có đúng một mục.
- Cache nhận ra dữ liệu đổi dù đường dẫn không đổi.
- Quiz đúng cả 4 câu.

## Gợi ý

### Gợi ý 1

Chính sách `INPUTS` mặc định của Prefect băm **giá trị đối số**, mà đối số ở đây là một chuỗi đường dẫn. Hỏi bản thân: điều gì
xảy ra khi tệp ở đường dẫn đó được cập nhật bằng dữ liệu của tháng mới?

### Gợi ý 2

`parameters` là dict các đối số của task theo tên. Đọc `Path(parameters["data_path"]).read_bytes()`, băm, rồi ghép với hai tham số
còn lại thành một chuỗi ổn định.
