---
title: Sự cố - container API restart liên tục
level: intermediate
services: []
files:
  - path: starter/compose.yaml
    note: Compose đang chạy trên staging, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/fixtures/compose.incident.yaml
    note: Bản gốc lúc sự cố
run:
  - nice -n 15 uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/intermediate/02-incident-restart-loop -q
---

## Mục tiêu

Chẩn đoán một sự cố container theo thứ tự một on-call làm: xem trạng thái, đọc log, đối chiếu cấu hình với hợp đồng của service, sửa tối thiểu.

## Đề bài

Thứ Hai, đội staging báo: "API dự đoán ETA **restart liên tục**" ngay sau khi chạy `docker compose up -d`. Bước build không lỗi. Dịch vụ `api` chưa bao giờ ổn định, và khi nó có vẻ chạy được thì Compose vẫn không coi nó là sẵn sàng. `starter/compose.yaml` là tệp đang chạy trên staging.

Hợp đồng của service (không đổi): code và `Dockerfile` trong `service/` giữ nguyên; image không chứa model; service nghe cổng 8000, đọc model ở đường dẫn trong biến `MODEL_PATH` và có `GET /healthz`; thư mục model của dự án là `./models` cạnh `compose.yaml`. Chỉ sửa `compose.yaml`, và dịch vụ `api` vẫn phải có `healthcheck` hoạt động (xoá nó để qua bài là không đạt). Có thể có nhiều hơn một lỗi.

Test dựng dự án tạm (`service/`, `models/model.joblib`, `compose.yaml` của bạn), một test chạy lại bản lúc sự cố và đòi nó tái hiện triệu chứng.

## Tiêu chí đạt

- `nice -n 15 uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/intermediate/02-incident-restart-loop -q` pass: `up --wait` thành công, `/healthz` 200, `/predict` trả kết quả, và service khởi động đúng một lần trong 8 giây theo dõi.
- Với mỗi lỗi bạn sửa, chỉ ra được dòng lệnh hoặc dòng log đã dẫn bạn tới nó.

## Gợi ý

### Gợi ý 1

Thứ tự xem: `docker compose ps -a` (trạng thái, số lần restart), `docker compose logs api` (dòng cuối trước khi thoát), rồi `docker inspect` phần `State` và `Health`.

### Gợi ý 2

Sau khi sửa lỗi đầu, đừng dừng nếu trạng thái chưa `healthy`: đọc log của chính healthcheck trong `docker inspect` và chạy thử lệnh đó bên trong container.
