# Lời giải: chọn image cho service ML

- **slim-vs-full**: `python:3.12.11-slim` cho wheel manylinux của numpy/scipy/scikit-learn chạy tốt (glibc). Alpine dùng musl: wheel manylinux không dùng được, pip biên dịch từ source, build chậm và dễ lỗi. Bản đầy đủ nặng thêm hàng trăm MB (gcc, header) mà service không dùng. `ubuntu:latest` không ghim, tag trôi.
- **layer-order**: Docker cache layer theo đầu vào. `COPY . .` đứng trước `pip install` làm mọi thay đổi source vô hiệu hoá layer cài đặt. Đặt `COPY requirements.txt` + `pip install` trước, code sau.
- **model-in-image**: model trong image thì version model = image tag, rollback bằng `docker run` tag cũ, tái lập hoàn toàn; đổi lại mỗi lần retrain là một lần build và đẩy image. Mount ngoài (volume, object storage) tách chu kỳ model khỏi image nhưng thêm điểm hỏng lúc khởi động (thiếu file, sai version) và khó truy vết nếu không ghi version model.
- **ml-image-size**: `--no-cache-dir`, multi-stage và `.dockerignore` đều làm image nhỏ hơn hoặc build nhanh hơn; thêm `LABEL` không ảnh hưởng.
- **root-user**: giảm bề mặt tấn công. Tiến trình bị khai thác không có quyền root trong container, và nếu có lỗ hổng thoát container thì không thoát với quyền root của host. Không liên quan tốc độ, healthcheck hay kích thước.
- **cuda-base**: một Dockerfile với build-arg chọn base (slim cho CPU, `nvidia/cuda:*-runtime` cho GPU); driver nằm trên host và được đưa vào bằng NVIDIA Container Toolkit (`--gpus`), không cài trong image. Image `devel` rất lớn, chỉ dùng khi phải biên dịch.
