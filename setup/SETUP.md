# Cài đặt môi trường học

Hướng dẫn cho Linux (Debian/Ubuntu; distro khác đổi lệnh cài gói tương ứng). Mọi lệnh chạy từ
**thư mục gốc repo** trừ khi ghi khác.

## 1. Yêu cầu máy

| Thành phần | Tối thiểu | Khuyến nghị |
| --- | --- | --- |
| RAM | 8 GB (bật 2–3 dịch vụ một lúc) | 16 GB |
| Đĩa trống | 15 GB (image Docker + dữ liệu) | 30 GB |
| CPU | 4 nhân | 8 nhân |

Bạn **không cần** bật hết dịch vụ. Mỗi module chỉ cần vài cái (xem mục 5).

## 2. Python với uv

Repo dùng [uv](https://docs.astral.sh/uv/) để quản lý Python 3.12 và thư viện (`pyproject.toml`, `uv.lock`).

```bash
# nếu chưa có uv
curl -LsSf https://astral.sh/uv/install.sh | sh

uv --version
uv sync                   # tạo .venv, cài Python 3.12 nếu thiếu và toàn bộ thư viện
uv run python -c "import duckdb, pyspark, kafka; print('ok')"
```

Mọi lệnh Python dùng `uv run ...` (không cần activate venv). Muốn activate: `source .venv/bin/activate`.

## 3. Docker

```bash
# Docker Engine + Compose plugin (Debian/Ubuntu, theo docs.docker.com/engine/install)
sudo apt-get update && sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# chạy docker không cần sudo (đăng xuất rồi đăng nhập lại)
sudo usermod -aG docker $USER

docker --version && docker compose version
```

Debian thì thay `ubuntu` bằng `debian` trong URL. Kiểm tra cấu hình compose mà không chạy gì:

```bash
docker compose -f setup/docker-compose.yml --profile all config -q && echo OK
```

## 4. Bật / tắt dịch vụ

Tất cả dịch vụ định nghĩa trong `setup/docker-compose.yml`, chung network `de-net`.

```bash
# bật một hoặc vài dịch vụ theo tên
docker compose -f setup/docker-compose.yml up -d postgres
docker compose -f setup/docker-compose.yml up -d mongo redis

# bật theo nhóm (profile)
docker compose -f setup/docker-compose.yml --profile nosql up -d

# xem trạng thái (chờ cột STATUS là "healthy")
docker compose -f setup/docker-compose.yml --profile all ps

# tắt tất cả, GIỮ dữ liệu trong volume
docker compose -f setup/docker-compose.yml --profile all down
# tắt và XOÁ dữ liệu (làm lại từ đầu)
docker compose -f setup/docker-compose.yml --profile all down -v
```

| Profile | Dịch vụ |
| --- | --- |
| `sql` | postgres |
| `nosql` | mongo, redis, cassandra, neo4j |
| `lake` | minio |
| `stream` | kafka |
| `bi` | metabase, postgres |
| `cloud` | localstack |
| `all` | tất cả |

Thông số kết nối:

| Dịch vụ | Từ máy host | Đăng nhập |
| --- | --- | --- |
| postgres | `localhost:5432` | `de` / `de`, database `de` → `postgresql://de:de@localhost:5432/de` |
| mongo | `mongodb://localhost:27017` | không |
| redis | `redis://localhost:6379/0` | không |
| cassandra | `localhost:9042` | không |
| neo4j | `bolt://localhost:7687`, web http://localhost:7474 | `neo4j` / `password123` |
| minio | S3 API `http://localhost:9000`, console http://localhost:9001 | `minioadmin` / `minioadmin` |
| localstack | `http://localhost:4566` (endpoint chung cho mọi API AWS giả lập) | key bất kỳ, vd. `test` / `test`, region `us-east-1` |
| kafka | `localhost:9094` (container khác dùng `kafka:9092`) | không |
| metabase | http://localhost:3000 | tạo tài khoản lúc mở lần đầu. Kết nối Postgres bằng host `postgres`, cổng 5432 |
| airflow | http://localhost:8080 | `airflow` / `airflow` (xem `setup/airflow/README.md`) |

Airflow chạy ở compose riêng:

```bash
docker compose -f setup/airflow/docker-compose.yml up -d
docker compose -f setup/airflow/docker-compose.yml down
```

## 5. Module cần dịch vụ nào

| Module | Dịch vụ Docker | Ghi chú |
| --- | --- | --- |
| 01 Foundations | postgres (một số bài) | Phần lớn bài chạy DuckDB / SQLite, không cần Docker |
| 02 Data Modeling | postgres | |
| 03 NoSQL | mongo, redis, cassandra, neo4j | Bật từng cái theo bài. Test cơ bản dùng mongomock / fakeredis |
| 04 Warehouse & Lakehouse | minio | DuckDB, Delta Lake chạy local |
| 05 Batch Pipelines | postgres, airflow | dbt-duckdb và Prefect chạy local |
| 06 Spark | không | PySpark local, cần Java (mục 6) |
| 07 Streaming | kafka | |
| 08 DevOps | tuỳ bài | Terraform cài riêng (mục 6) |
| 09 Serving & BI | postgres, metabase | Streamlit chạy local |
| 10 Security & Governance | postgres | |
| 11 Cloud | localstack hoặc minio (tuỳ chọn) | Phần lớn bài là hàm thuần/Terraform, không cần Docker. Bài S3 chạy offline bằng `moto` nếu có, không cần tài khoản cloud |
| Capstone | theo milestone | Xem `tracks/data-engineer/capstone/README.md` |

Bật đúng cái cần, tắt khi học xong module: tiết kiệm RAM đáng kể (Cassandra + Neo4j + Metabase mỗi cái ~1–1.5 GB).

## 6. Java cho PySpark (và công cụ phụ)

PySpark 3.5 cần Java 8/11/17/21 (máy đã có Java 21 thì dùng luôn).

```bash
java -version                         # cần thấy "openjdk version 21..." hoặc 17
# nếu chưa có
sudo apt-get install -y openjdk-21-jdk-headless   # hoặc openjdk-17-jdk-headless

# nếu có nhiều bản Java, chỉ định rõ
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))

uv run python -c "from pyspark.sql import SparkSession; s=SparkSession.builder.master('local[2]').getOrCreate(); print(s.range(5).count()); s.stop()"
```

Với Java 17/21, Spark 3.5 đã tự thêm các cờ `--add-opens` cần thiết. Nếu gặp
`IllegalAccessError ... sun.nio.ch`, đặt:

```bash
export JDK_JAVA_OPTIONS="--add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED"
```

Terraform (module 08, capstone M08), tuỳ chọn:

```bash
# theo developer.hashicorp.com/terraform/install
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install -y terraform
```

## 7. Dữ liệu

```bash
uv run python data/generate_olist.py                  # 50k đơn giả vào data/raw/ (~3 giây)
uv run python data/simulate_events.py --count 20 --stdout
uv run python data/download_olist.py                  # tuỳ chọn: bộ thật, cần Kaggle token
```

Chi tiết schema: `data/README.md`.

## 8. App học tập

App đọc nội dung trong `tracks/` và hiện lý thuyết, bài tập, tiến độ. Cần Node.js 20+ và pnpm.

```bash
# nếu chưa có pnpm
corepack enable && corepack prepare pnpm@latest --activate     # hoặc: npm install -g pnpm

cd app && pnpm install && pnpm dev
```

Mở http://localhost:5173.

## 9. Chạy test bài tập

Mỗi bài tập có `starter/` (bạn sửa) và `tests/`.

```bash
# test code của bạn trong starter/ (chưa làm thì test fail, đó là bình thường)
uv run pytest tracks/data-engineer/modules/03-nosql/exercises/intermediate/02-cassandra-query-model -q

# test lời giải mẫu (thư mục solutions/ cùng cấu trúc)
SOLUTION=1 uv run pytest tracks/data-engineer/modules/03-nosql/exercises/intermediate/02-cassandra-query-model -q

# cả một module
uv run pytest tracks/data-engineer/modules/02-data-modeling -q
```

Bài cần dịch vụ Docker sẽ **skip** kèm lệnh bật dịch vụ nếu dịch vụ chưa chạy. Đổi host/cổng
bằng biến môi trường (`POSTGRES_PORT`, `POSTGRES_DSN`, `KAFKA_BOOTSTRAP`…, xem `testkit.py`).

## 10. Xử lý sự cố

### Cổng đã bị dùng (`bind: address already in use`)

```bash
sudo ss -ltnp | grep -E ':(5432|6379|27017|9042|7687|9000|9094|3000|8080)\b'
```

- Có Postgres cài sẵn trên máy: `sudo systemctl stop postgresql`, hoặc đổi cổng host trong
  compose thành `"5433:5432"` rồi chạy test với `POSTGRES_PORT=5433 POSTGRES_DSN=postgresql://de:de@localhost:5433/de`.
- Tương tự cho dịch vụ khác: đổi vế trái của `ports` và đặt biến `<SERVICE>_PORT`.

### Cassandra khởi động chậm / test bị skip

Cassandra cần 30–90 giây sau khi container chạy mới nhận kết nối CQL.

```bash
docker compose -f setup/docker-compose.yml ps cassandra             # chờ "healthy"
docker compose -f setup/docker-compose.yml logs -f cassandra        # tìm "Starting listening for CQL clients"
docker compose -f setup/docker-compose.yml exec cassandra cqlsh -e "DESCRIBE KEYSPACES"
```

Nếu container chết với exit code 137: thiếu RAM (xem mục dưới). Heap đã giới hạn `MAX_HEAP_SIZE=1G`.

### Hết RAM, máy chậm

```bash
docker stats --no-stream                                          # xem ai ăn RAM
docker compose -f setup/docker-compose.yml stop cassandra neo4j metabase
```

- Chỉ bật dịch vụ của module đang học.
- Cassandra (~1.5 GB), Neo4j (~1.5 GB), Metabase (~1 GB), Airflow (~1.5 GB) là bốn dịch vụ nặng nhất. Đừng bật cùng lúc trên máy 8 GB.
- Spark local: giảm `spark.driver.memory` (vd. `1g`) và dùng `local[2]`.

### Kafka: client kết nối được rồi treo / `NoBrokersAvailable`

- Từ máy host luôn dùng `localhost:9094`. Cổng 9092 chỉ dành cho container trong network `de-net`.
- Xoá dữ liệu Kafka hỏng sau khi đổi cấu hình: `docker compose -f setup/docker-compose.yml rm -sfv kafka && docker volume rm de-learning_kafka_data`.

### `permission denied` khi gọi docker

Chưa vào nhóm `docker`: `sudo usermod -aG docker $USER` rồi đăng xuất / đăng nhập lại (hoặc `newgrp docker`).

### `uv sync` lỗi khi build gói

`cassandra-driver` và `psycopg` dùng wheel có sẵn cho Python 3.12. Nếu uv cố build từ source, cài
`sudo apt-get install -y build-essential python3-dev libpq-dev` rồi chạy lại.

### Airflow không thấy DAG / lỗi quyền

Xem `setup/airflow/README.md`.

## Cổng bị dự án khác chiếm

Nếu `docker compose up` báo `port is already allocated`, hoặc test kết nối nhầm vào một database khác cùng cổng:

```bash
cp setup/.env.example setup/.env
# bỏ dấu # ở dòng cổng bị trùng, ví dụ POSTGRES_PORT=15432
docker compose -f setup/docker-compose.yml up -d postgres
```

`docker compose` và `testkit.py` (dùng trong test bài tập) cùng đọc `setup/.env`, nên chỉ cần đổi một chỗ.
Câu lệnh kết nối viết tay trong bài (psql, mongosh…) thì nhớ dùng cổng mới.

## Lab bổ trợ: CDC và cloud

- [CDC PostgreSQL → Debezium → Kafka](../tracks/data-engineer/modules/07-streaming-kafka/cdc-lab.md)
  dùng `setup/cdc/docker-compose.yml`, cổng 55432/19094/18083, network và volume riêng.
  `setup/.env` của stack chung không tự đổi các cổng của lab này. Nếu trùng cổng, sửa mapping lab
  và tham số `--bootstrap` của sink tương ứng; hostname nội bộ container vẫn giữ nguyên.
- [GCP từ Parquet tới KPI](../tracks/data-engineer/modules/11-cloud/cloud-gcp-lab.md) dùng
  `setup/cloud-gcp/prepare.py` cho phần local và Terraform cho hạ tầng. Cloud thật là tùy chọn,
  cần Google Cloud CLI, Terraform và quyền/tài khoản phù hợp. Không cần cài chúng để làm test offline.

## Về image MinIO

MinIO đã ngừng phát hành image chính thức `minio/minio` trên Docker Hub, nên `setup/docker-compose.yml`
dùng `pgsty/minio` — bản build cộng đồng (dự án Pigsty) từ cùng mã nguồn MinIO, API S3 và lệnh `mc` giữ nguyên.
Đây là image bên thứ ba: muốn tự chủ hoàn toàn thì build image từ mã nguồn MinIO, hoặc thay bằng một
S3 tương thích khác (vd. LocalStack, service `localstack` trong compose) rồi đổi `MINIO_ENDPOINT`.
