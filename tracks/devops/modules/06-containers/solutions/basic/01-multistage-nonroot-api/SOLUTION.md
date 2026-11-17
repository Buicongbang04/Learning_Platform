# Lời giải: Dockerfile multi-stage, non-root cho API Olist Shop

## Kết quả đo trên máy viết bài

| Image | Kích thước (`docker image inspect .Size`) | User | Compiler trong image |
| --- | --- | --- | --- |
| Starter | khoảng 869 MB | root | `gcc`, `g++`, `make`, `ld` |
| Lời giải | khoảng 293 MB | `10001:10001` | không |

Phần lớn chênh lệch đến từ `build-essential` và `libpq-dev` (hơn 500 MB) mà app không hề cần: mọi dependency đều có wheel dựng
sẵn, `psycopg[binary]` mang theo libpq. Đây là phát hiện quan trọng hơn cả kỹ thuật multi-stage: trước khi tối ưu, hỏi xem gói
đó có cần không.

## Từng quyết định

**Hai stage dùng cùng một image nền.** Stage `build` tạo venv ở `/opt/venv` và cài dependency vào đó. Stage `runtime` bắt đầu
lại từ `python:3.12.16-slim-trixie` sạch và chỉ `COPY --from=build /opt/venv /opt/venv`. Venv chứa đường dẫn tuyệt đối tới
interpreter (`/usr/local/bin/python3.12`), nên hai stage phải cùng image nền và cùng đường dẫn venv; chép venv từ image
`python:3.12` sang distroless (Python 3.13) sẽ hỏng. Nếu sau này cần compiler (gói không có wheel), chỉ thêm `build-essential`
vào stage `build`, runtime vẫn sạch.

**`requirements.txt` chép trước, mã nguồn chép sau.** Sửa code không làm `pip install` chạy lại (bài Basic 02 đo điều này).

**`PIP_NO_CACHE_DIR=1`.** Cache của pip ở stage build không đi vào runtime vì runtime chỉ chép venv, nhưng tắt cache giữ stage
build nhỏ và cache BuildKit gọn.

**User có UID số.** `USER 10001:10001` thay vì `USER olist`: Kubernetes với `runAsNonRoot: true` chỉ kiểm được khi USER là số;
UID trên 10000 tránh trùng user của máy host khi mount volume. Mã nguồn thuộc root (`COPY --chown=root:root`) và user của app
không ghi được vào đó: kẻ tấn công chiếm được tiến trình cũng không sửa được code. App ghi SQLite vào `/tmp` qua `DATABASE_URL`.

**HEALTHCHECK bằng chính Python.** Không cài `curl` chỉ để healthcheck: thêm một binary là thêm CVE và công cụ cho kẻ tấn công.
Dạng exec (mảng JSON) chạy được cả trên image không có shell. `--start-period=10s` cho app thời gian khởi động trước khi tính
lần fail. Healthcheck gọi `/healthz` (liveness, không chạm DB), không gọi `/readyz`: Docker và Swarm khởi động lại container
unhealthy, mà DB chết thì khởi động lại API không giúp gì.

**CMD dạng exec.** `CMD uvicorn ...` (dạng shell) thành `/bin/sh -c "uvicorn ..."`. Trên image Debian trixie, `dash` không
`exec` lệnh trong `-c` (đã thử: tiến trình con nhận PID 7, `sh` giữ PID 1), nên `sh` là PID 1, không chuyển SIGTERM cho uvicorn,
và `docker stop` chờ đủ 10 giây rồi SIGKILL. `bash` và một số bản `dash` mới có tối ưu này, nên hành vi đổi theo image nền:
đừng dựa vào nó. Dạng exec loại bỏ hẳn câu hỏi đó. Bài Intermediate 01 là sự cố đúng loại này.

## Dockerfile

```dockerfile
FROM python:3.12.16-slim-trixie AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

FROM python:3.12.16-slim-trixie AS runtime
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN groupadd --system --gid 10001 olist \
 && useradd --system --uid 10001 --gid olist --no-create-home --shell /usr/sbin/nologin olist
COPY --from=build /opt/venv /opt/venv
WORKDIR /srv
COPY --chown=root:root olist_shop ./olist_shop
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["uvicorn", "olist_shop.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
```

## Đi xa hơn

- **Ghim digest**: `FROM python:3.12.16-slim-trixie@sha256:8523d6ab...` ở cả hai stage, để Renovate hay Dependabot đề xuất cập
  nhật có kiểm soát khi Debian vá lỗ hổng.
- **Distroless**: runtime `gcr.io/distroless/python3-debian13` nhỏ hơn và không có shell, nhưng chạy Python 3.13; phải build venv
  bằng đúng Python đó (ví dụ stage build `debian:trixie-slim` với `python3-venv`), không chép venv từ image `python:3.12`.
- **`uv`**: `uv sync --frozen --no-dev` với lock file cho build tái lập được, nhanh hơn pip nhiều lần.
- **Bỏ pip khỏi runtime**: venv vẫn mang pip; `pip` là nguồn CVE hay gặp nhất trong image Python (xem Intermediate 02). Tạo venv
  bằng `python -m venv --without-pip` rồi cài bằng `pip --python /opt/venv/bin/python` (pip 22.3 trở lên) hoặc `uv`.
- **Read-only rootfs**: image này chạy được với `--read-only --tmpfs /tmp` vì app chỉ ghi vào `/tmp`; thử để chắc chắn.
