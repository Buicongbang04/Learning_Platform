---
title: Sự cố - p99 vọt lên ở những request đầu sau mỗi lần deploy
level: intermediate
services: []
files:
  - path: starter/service.py
    note: Service đang chạy trên production, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/fixtures/service_incident.py
    note: Bản gốc lúc sự cố, chỉ đọc
run:
  - uv run pytest tracks/mlops/modules/07-model-serving/exercises/intermediate/03-incident-first-request-latency -q
---

## Mục tiêu

Chẩn đoán một sự cố độ trễ từ triệu chứng: tách "chậm" thành "chậm lúc nào, với request nào", tìm đúng dòng mã chịu trách nhiệm và sửa tối thiểu có test chứng minh.

## Đề bài

Thứ Năm, sau đợt deploy thường lệ của `taxi-eta`, dashboard cho thấy:

- Mỗi lần deploy, **p99 vọt từ khoảng 12 ms lên hơn 500 ms** trong vài chục giây rồi tự hạ. Sau đó mọi thứ bình thường; p50 không đổi.
- Orchestrator báo pod `Ready` ngay sau khi tiến trình lên. Không có lỗi trong log, không request nào thất bại, mã nguồn và model không đổi so với tuần trước.
- Đợt deploy rolling 6 replica nên mỗi lần có vài chục người dùng gặp một request chậm bất thường; một vài người báo "app đứng hình một lúc khi mở lần đầu".
- Chạy lại cùng bản trên máy dev cho kết quả tương tự: request **đầu tiên** sau khi khởi động chậm, các request sau thì nhanh.

`starter/service.py` là mã đang chạy. Hợp đồng không đổi: `create_app()` trả ứng dụng FastAPI; `GET /readyz` 200 `{"ready": true}` khi nhận traffic, 503 trước đó; `POST /predict` body `{"rows": [[distance_km, hour, zone], ...]}` trả `{"model_version": 3, "predictions": [...]}` với **đúng các con số hiện tại**; hàm `build_zone_table()` giữ nguyên (cả nội dung và chi phí của nó) và vẫn là nơi dựng bảng zone; nó chạy đúng một lần mỗi tiến trình.

Chỉ sửa `starter/service.py`. Một test chạy lại bản lúc sự cố và đòi nó tái hiện triệu chứng. Test của bạn: sau khi `/readyz` lên 200, request đầu tiên dưới 250 ms và p99 của 30 request đầu dưới 250 ms; `/readyz` không bao giờ 200 trước khi bảng zone dựng xong; bảng zone không được bị bỏ hay thay bằng hằng số.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/07-model-serving/exercises/intermediate/03-incident-first-request-latency -q` pass.
- Với lỗi bạn tìm ra, chỉ được dòng mã và phép đo (độ trễ theo thứ tự request kể từ lúc khởi động) dẫn bạn tới nó.
- Nói được vì sao dashboard trung bình hoặc p50 không bao giờ cho thấy sự cố này, và bạn thêm chỉ số nào để bắt nó.

## Gợi ý

### Gợi ý 1

Đừng đoán từ mã: đo. Gọi `/predict` 30 lần liên tiếp ngay sau khi lên, in độ trễ từng lần. Hình dạng chuỗi số (chỉ lần đầu, vài lần đầu, hay đều đều) cho biết nên tìm ở đâu.

### Gợi ý 2

Tìm trong mã những chỗ làm việc tốn kém và hỏi: việc này xảy ra lúc nào trong vòng đời của tiến trình, và ai đang chờ nó lúc đó?
