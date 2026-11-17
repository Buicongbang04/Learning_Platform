---
title: Viết lại Dockerfile API Olist Shop thành multi-stage, non-root
level: basic
services: []
files:
  - path: starter/Dockerfile
    note: 5 TODO
  - path: tests/test_multistage_image.py
    note: Không sửa
  - path: tests/fixtures/Dockerfile.starter
    note: Bản gốc của starter, test dùng làm mốc so sánh kích thước
run:
  - docker pull python:3.12.16-slim-trixie
  - uv run pytest tracks/devops/modules/06-containers/exercises/basic/01-multistage-nonroot-api -q
---

## Mục tiêu

Biến một Dockerfile "chạy được là được" thành image bạn dám đưa lên production: build và runtime tách stage, runtime không
có compiler, chạy bằng user thường, có HEALTHCHECK dùng được thật, và uvicorn là PID 1.

## Đề bài

`starter/Dockerfile` là Dockerfile một đồng nghiệp viết cho API của Olist Shop (`tracks/devops/sample-app`). Nó build được,
chạy được, nhưng image nặng gần 900 MB, chạy bằng root, mang theo `gcc`, `make`, `libpq-dev`, `curl`, và CMD dạng shell. Viết
lại `starter/Dockerfile` cho đạt các tiêu chí dưới.

Build context là thư mục `tracks/devops/sample-app` (có `requirements.txt` và gói `olist_shop/`); bạn chỉ sửa Dockerfile, không
sửa code ứng dụng. Muốn tự build thử từ gốc repo:

```bash
DEVOPS_CPU=${DEVOPS_CPUSET:+--cpuset-cpus=$DEVOPS_CPUSET} &&
nice -n 15 docker build $DEVOPS_CPU --pull=false -t olist-api:m06 \
  -f tracks/devops/modules/06-containers/exercises/basic/01-multistage-nonroot-api/starter/Dockerfile \
  tracks/devops/sample-app &&
docker image ls olist-api:m06
```

Image chỉ phục vụ API (`uvicorn olist_shop.main:app`, cổng 8000). Worker, compose production và quét lỗ hổng của mọi service
là việc của capstone m03, bài này không làm.

**Cách test chấm.** Test chép `olist_shop/`, `requirements.txt` và Dockerfile của bạn vào một thư mục tạm rồi build bằng
`DockerLab.build` (BuildKit, ghim CPU theo `DEVOPS_CPUSET`, giới hạn RAM 1 GB, không tự kéo image nền: thiếu image thì test
skip kèm lệnh `docker pull`). Test build cả `tests/fixtures/Dockerfile.starter` để lấy kích thước mốc. Lần build đầu cần mạng
để tải gói apt và pip; build lỗi vì mạng thì test skip, các lần sau dùng cache của BuildKit.

## Tiêu chí đạt

- Dockerfile có ít nhất 2 dòng `FROM` (stage build và stage runtime).
- `Config.User` của image không rỗng, không phải `root`/`0`; chạy `os.getuid()` trong container ra khác 0.
- Stage cuối không có `gcc`, `cc`, `g++`, `c++`, `make`, `ld` trong `PATH` (test chạy `python3 -c` trong image để kiểm).
- `CMD`/`ENTRYPOINT` dạng exec: Docker không ghi lại thành `["/bin/sh", "-c", ...]`.
- Image có `HEALTHCHECK`. Test chạy đúng lệnh đó bằng `docker exec` trong container đang chạy và đòi mã thoát 0.
- Kích thước image (`Size` của `docker image inspect`) nhỏ hơn 75% image của starter build cùng lúc.
- Container chạy với `DATABASE_URL=sqlite:////tmp/olist.db`, `APP_VERSION=m06-basic01`, mở cổng 8000; `GET /healthz` trả 200
  với JSON đúng bằng `{"status": "ok", "version": "m06-basic01"}` (test chờ tối đa 90 giây).
- Một test build Dockerfile gốc của starter và đòi các phép kiểm trên bắt được đủ lỗi của nó: một stage, root, có compiler, CMD
  dạng shell, không HEALTHCHECK.

## Gợi ý

### Gợi ý 1

Mọi gói trong `requirements.txt` đều có wheel dựng sẵn cho Linux x86_64 (`psycopg[binary]` mang sẵn libpq), nên có khi không
cần compiler nào. Ở stage build, tạo venv (`python -m venv /opt/venv`) rồi `pip install` vào đó; stage runtime chỉ cần
`COPY --from=<stage build> /opt/venv /opt/venv` và thêm `/opt/venv/bin` vào `PATH`.

### Gợi ý 2

Image `slim` không có `curl`. HEALTHCHECK dạng exec có thể gọi chính Python:
`["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]`. Tạo user
bằng `useradd --system --uid 10001 ...` rồi `USER 10001:10001` (dùng số để Kubernetes kiểm được `runAsNonRoot`).
