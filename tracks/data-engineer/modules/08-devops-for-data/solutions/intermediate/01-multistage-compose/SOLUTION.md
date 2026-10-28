# Lời giải: multi-stage + compose

## Dockerfile

- **Stage `builder`** cài `build-essential`, `libpq-dev`, rồi `pip wheel` để biên dịch mọi
  dependency thành wheel trong `/wheels`. Mọi thứ của stage này bị bỏ lại.
- **Stage `runtime`** chỉ cài thư viện runtime `libpq5`, `COPY --from=builder /wheels`, cài wheel
  rồi xoá. Không có `gcc` nghĩa là image nhỏ hơn vài trăm MB và scanner (Trivy, Grype) báo ít CVE hơn.
- `apt-get install --no-install-recommends` và `rm -rf /var/lib/apt/lists/*` **trong cùng một
  `RUN`**: xoá ở `RUN` sau không giảm kích thước vì file vẫn nằm trong layer trước.
- `USER appuser`, `HEALTHCHECK` exec form, `ENTRYPOINT` exec form.

## Compose

- `postgres:16.4` thay vì `postgres`: tag `latest` có thể nhảy major version (16 → 17) và dữ liệu
  cũ trong volume không mở được bằng major mới.
- `${POSTGRES_PASSWORD}` lấy từ `.env` (đưa `.env` vào `.gitignore`), không commit mật khẩu.
- **Named volume** `pgdata` giữ dữ liệu qua `docker compose down` (mất khi `down -v`).
- `healthcheck` + `depends_on.condition: service_healthy`: loader chỉ chạy khi Postgres nhận kết
  nối, tránh lỗi "connection refused" ở lần chạy đầu.
- Trong mạng compose, hostname là **tên service** (`postgres`). `localhost` bên trong container
  loader trỏ về chính container loader.

Chạy thử (nếu có Docker và mã nguồn `loader/`):

```bash
echo "POSTGRES_PASSWORD=change-me" > .env
docker compose up --build
```
