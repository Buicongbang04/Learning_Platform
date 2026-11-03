# Lời giải: review image GPU

## Hướng làm

Đọc từng dòng, tự hỏi: dòng này ảnh hưởng kích thước, tái lập, bảo mật hay khả năng chạy trên máy không GPU? Rồi gom thành findings có mức độ.

## Findings tiêu biểu

| Mức | Vấn đề | Vì sao nguy hiểm | Sửa |
| --- | --- | --- | --- |
| blocker | `HF_TOKEN` dán thẳng vào compose | Token vào git, lộ ở `docker inspect` | `env_file` ngoài git hoặc Docker secret; thu hồi token đã lộ |
| blocker | `nvidia/cuda:...-devel` làm base | Image `devel` kèm compiler, header, nặng thêm vài GB, bề mặt tấn công lớn | `-runtime` (hoặc cudnn-runtime) cho inference |
| blocker | Chạy bằng root, cache model ở `/root/.cache` | Root trong container; mount cache thuộc root trên host | `USER` thường, `HF_HOME=/models-cache` thuộc user đó |
| nên sửa | Không ghim phiên bản `pip3 install torch sentence-transformers ...` | Hôm nay và tuần sau cho hai môi trường khác nhau; torch bản mặc định kèm CUDA khác bản của base | `requirements.txt` ghim, index torch đúng CUDA (cu124) |
| nên sửa | `COPY . /app` trước `pip install -r` và cài pip hai lần | Sửa code là cài lại torch nặng hàng GB; context kéo theo data, `.git` | Copy `requirements.txt` trước, `.dockerignore`, một lệnh cài |
| nên sửa | `runtime: nvidia` (cú pháp cũ) | Không chạy ở Compose mới nếu daemon không đăng ký runtime; hỏng im lặng trên máy khác | `deploy.resources.reservations.devices` với `driver: nvidia`, `capabilities: [gpu]` |
| nên sửa | `CMD` dạng shell, không `HEALTHCHECK` | Không nhận SIGTERM đúng (PID 1 là sh), orchestrator không biết lúc nào sẵn sàng | `CMD ["uvicorn", ...]` dạng exec, healthcheck bằng python |
| nên sửa | `restart: always` | Lỗi cấu hình thành vòng restart vô hạn, che mất nguyên nhân | `unless-stopped` hoặc `on-failure:3` kèm healthcheck và alert |
| tuỳ chọn | `NVIDIA_DRIVER_CAPABILITIES=all` | Mở nhiều hơn cần thiết | `compute,utility` |
| tuỳ chọn | `git curl` cài trong image cuối | Thêm công cụ thừa | Chỉ cài ở stage build |

## Đường CPU

Một Dockerfile, `ARG BASE=python:3.12.11-slim` và `ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu`. Production GPU build với `--build-arg BASE=nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu124`. Compose chia hai tệp: `compose.yaml` chung và `compose.gpu.yaml` chỉ thêm phần `deploy.resources.reservations.devices` (hoặc profile `gpu`). CI và máy dev chỉ dùng bản CPU, nên test không bao giờ phụ thuộc GPU.

## Kích thước và cache

torch CPU khoảng 200 MB wheel, bản CUDA kéo theo thêm vài GB thư viện nvidia; base CUDA runtime thêm khoảng 1 đến 2 GB. Giữ layer nặng: `requirements.txt` ghim copy trước, một `RUN pip install` riêng, code sau cùng. Model đặt ở volume hoặc tải lúc khởi động có kiểm checksum, không bake vào layer nặng nếu đổi thường xuyên.

## Điều kiện tiên quyết trên host

Driver NVIDIA (không cài trong image) và NVIDIA Container Toolkit. Kiểm bằng `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`: in ra bảng GPU nghĩa là toolkit, driver và runtime đã nối đúng.

## Rubric (tối đa 20 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Tìm ≥6 findings đúng, mỗi cái có mức độ, rủi ro vận hành và cách sửa | 6 |
| Có findings về base image, user, khai báo GPU trong Compose, ghim phiên bản | 4 |
| Phát hiện bí mật trong compose và hậu quả (thu hồi token) | 2 |
| Đường CPU dùng build-arg hoặc compose override, không nhân đôi Dockerfile | 3 |
| Ước lượng kích thước và chiến lược layer cache hợp lý | 2 |
| Điều kiện host và lệnh kiểm `nvidia-smi` đúng | 1 |
| Dockerfile sửa nhất quán với các findings | 2 |

Từ 14 điểm trở lên là đạt.
