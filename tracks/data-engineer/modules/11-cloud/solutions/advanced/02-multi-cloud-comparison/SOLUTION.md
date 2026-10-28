# Hướng giải: so sánh 3 cloud và chống lock-in

Không có đáp án duy nhất: điểm và trọng số phụ thuộc bối cảnh công ty. Bài được chấm theo độ chặt
của lập luận và tính nhất quán giữa ma trận điểm, tài liệu và khuyến nghị.

## Hướng làm

1. **Ánh xạ từng thành phần** của kiến trúc sang 3 cloud, không chỉ 6 nhóm cơ bản: thêm CDC,
   orchestration, danh tính, secret, catalog, BI, monitoring. Ghi chú chỗ "tương đương" chỉ gần
   đúng (ADF ≠ Dataflow, Pub/Sub không có partition như Kinesis/Kafka).
2. **Chi phí**: đừng so giá GB lưu trữ (gần như bằng nhau). So **mô hình tính tiền** của warehouse,
   phí cố định của orchestration/streaming, egress và chiết khấu cam kết (Savings Plans, CUD, Azure
   Reservations, credit startup).
3. **Ma trận quyết định**: chọn 5–7 tiêu chí, trọng số phản ánh ưu tiên kinh doanh. Viết hàm
   `weighted_scores` tách biệt khỏi dữ liệu để thử độ nhạy (đổi trọng số xem thứ hạng có đảo không).
4. **Lock-in**: đánh giá từng thành phần theo mức khó chuyển, ước lượng công, nêu chiến lược và
   cái giá của chiến lược đó.
5. **Khuyến nghị** rõ ràng, kèm điều kiện đổi ý (đó là dấu hiệu của tư duy kiến trúc trưởng thành).

## Quyết định cần cân nhắc

| Câu hỏi | Gợi ý lập luận |
| --- | --- |
| Có nên multi-cloud chủ động? | Hiếm khi đáng cho đội nhỏ: gấp đôi IAM, mạng, kỹ năng; egress giữa cloud đắt. Ưu tiên "single cloud, portable design" |
| Định dạng bảng mở? | Iceberg được cả Athena/Glue, BigQuery (BigLake), Snowflake, Databricks/Fabric đọc; Delta mạnh trong hệ Databricks/Fabric |
| Warehouse cloud-native hay Snowflake/Databricks? | Snowflake/Databricks chạy trên cả 3 cloud, giảm lock-in vào cloud nhưng lock-in vào vendor khác, chi phí thường cao hơn |
| Orchestration | Airflow (MWAA/Composer/tự host trên K8s) di động; Step Functions/ADF/Workflows rẻ, tích hợp sâu nhưng khó chuyển |
| IaC | Terraform/OpenTofu dùng chung ngôn ngữ cho 3 cloud nhưng **resource không di động**: `aws_s3_bucket` không tự thành `google_storage_bucket` |

## Bản tham khảo (đã qua bộ test)

`decision.py`:

```python
"""Ma trận quyết định có trọng số để chọn cloud."""

from __future__ import annotations

CLOUDS = ("aws", "azure", "gcp")

# Bối cảnh giả định: startup thương mại điện tử, đội 3 DE đã quen SQL/BigQuery, chưa có hợp đồng cloud.
SCORES: dict[str, dict[str, int]] = {
    "aws": {"cost": 3, "team_skills": 3, "managed_services": 4, "ecosystem": 5, "hiring_market": 5, "ops_simplicity": 3},
    "azure": {"cost": 3, "team_skills": 2, "managed_services": 4, "ecosystem": 4, "hiring_market": 4, "ops_simplicity": 3},
    "gcp": {"cost": 4, "team_skills": 4, "managed_services": 5, "ecosystem": 3, "hiring_market": 3, "ops_simplicity": 5},
}

WEIGHTS: dict[str, float] = {
    "cost": 0.25,
    "team_skills": 0.20,
    "managed_services": 0.20,
    "ecosystem": 0.10,
    "hiring_market": 0.10,
    "ops_simplicity": 0.15,
}


def weighted_scores(scores: dict[str, dict[str, float]], weights: dict[str, float]) -> dict[str, float]:
    if any(w < 0 for w in weights.values()):
        raise ValueError("Trọng số không được âm")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Tổng trọng số phải > 0")
    for cloud, row in scores.items():
        missing = set(weights) - set(row)
        if missing:
            raise ValueError(f"{cloud} thiếu tiêu chí {sorted(missing)}")
        bad = {k: v for k, v in row.items() if not 1 <= v <= 5}
        if bad:
            raise ValueError(f"{cloud} có điểm ngoài [1, 5]: {bad}")
    normalized = {k: v / total for k, v in weights.items()}
    return {cloud: round(sum(row[k] * w for k, w in normalized.items()), 3) for cloud, row in scores.items()}


def rank(scores: dict[str, dict[str, float]], weights: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(weighted_scores(scores, weights).items(), key=lambda item: (-item[1], item[0]))


if __name__ == "__main__":
    for cloud, score in rank(SCORES, WEIGHTS):
        print(f"{cloud:>6}: {score:.3f}")
```

Chạy ra: `gcp 4.150`, `aws 3.600`, `azure 3.200`.

`comparison.md`:

````markdown
# So sánh AWS, Azure, GCP cho data platform Olist

## 1. Ánh xạ kiến trúc

| Thành phần | AWS | Azure | GCP |
| --- | --- | --- | --- |
| Compute chung | EC2, ECS Fargate | Virtual Machines, Container Apps | Compute Engine, Cloud Run |
| Object storage (lake) | S3 | ADLS Gen2 (Blob Storage) | Cloud Storage |
| Managed SQL (nguồn OLTP) | RDS / Aurora PostgreSQL | Azure Database for PostgreSQL | Cloud SQL / AlloyDB |
| CDC từ Postgres | DMS | Data Factory CDC | Datastream |
| ETL / Spark | Glue, EMR Serverless | Databricks, Synapse Spark | Dataflow, Dataproc Serverless |
| Warehouse | Redshift Serverless, Athena | Synapse / Fabric Warehouse | BigQuery |
| Streaming | Kinesis Data Streams, MSK | Event Hubs (Kafka API) | Pub/Sub, Managed Kafka |
| Orchestration | MWAA, Step Functions | Data Factory, Fabric Airflow job | Cloud Composer, Workflows |
| Danh tính workload | IAM role | Managed identity + Entra ID | Service account |
| Secret | Secrets Manager | Key Vault | Secret Manager |
| Catalog / governance | Glue Data Catalog, Lake Formation | Microsoft Purview | Dataplex, Data Catalog |
| BI | QuickSight | Power BI | Looker Studio / Looker |
| Monitoring | CloudWatch | Azure Monitor | Cloud Monitoring |

## 2. Chi phí

- Lưu trữ gần như ngang nhau (~0.02 USD/GB-tháng lớp nóng), không phải yếu tố quyết định.
- Khác biệt lớn nhất là **mô hình tính tiền warehouse**: BigQuery/Athena tính theo byte quét (rẻ
  với 200 truy vấn/ngày đã partition), Redshift Serverless tính theo RPU-giờ với mức tối thiểu,
  Synapse dedicated tính theo DWU-giờ kể cả khi rảnh (phải pause).
- **Orchestration managed** là phí cố định lớn: MWAA và Composer vài trăm USD/tháng; Step
  Functions, Workflows, ADF tính theo lần chạy nên rẻ hơn nhiều cho ít DAG.
- **Egress** ~0.08–0.12 USD/GB ở cả ba; chọn BI cùng cloud với warehouse để tránh egress.
- Ước tính cho workload Olist: 600–900 USD/tháng ở cả ba cloud, chênh lệch chủ yếu do
  orchestration và streaming chạy 24/7, không do lưu trữ.

## 3. Ma trận quyết định

Kết quả `rank()`: gcp 4.15, aws 3.6, azure 3.2.

Trọng số: chi phí 25% (startup), kỹ năng đội 20% và dịch vụ managed 20% (chỉ 3 DE), vận hành
đơn giản 15%, hệ sinh thái 10%, thị trường tuyển dụng 10%. Nếu công ty đã dùng Microsoft 365 và
Power BI, điểm `team_skills`/`ecosystem` của Azure tăng và thứ hạng có thể đảo.

## 4. Lock-in và tính di động

| Thành phần | Mức lock-in | Công chuyển ước tính |
| --- | --- | --- |
| Lake trên object storage, định dạng Parquet + Iceberg | Thấp | Copy dữ liệu (tốn egress một lần) |
| Spark / Beam job | Thấp–trung bình | Đổi connector, cấu hình |
| dbt models | Trung bình | Sửa SQL dialect, macro cross-database |
| Warehouse (BigQuery SQL, UDF) | Cao | Vài người-tuần |
| IAM, mạng, policy | Cao | Viết lại toàn bộ (Terraform giúp có danh sách đầy đủ) |
| Orchestration native (ADF JSON, Step Functions) | Cao | Viết lại; dùng Airflow thì chỉ đổi operator |

Chiến lược: lưu dữ liệu ở định dạng mở (Parquet, Iceberg) trên object storage; logic biến đổi
bằng dbt và Spark; điều phối bằng Airflow; hạ tầng bằng Terraform; streaming qua giao thức Kafka
(MSK, Event Hubs Kafka API, Managed Kafka). Cái giá: không tận dụng hết tính năng native (BigQuery
ML, Glue crawler), tốn thêm công vận hành lớp trừu tượng. Không theo đuổi multi-cloud chủ động khi
chưa có lý do kinh doanh; chỉ giữ **khả năng chuyển**.

## 5. Khuyến nghị

Chọn **GCP** (BigQuery serverless + Dataflow + Composer/Workflows) vì đội đã quen BigQuery, ít phải
vận hành và chi phí warehouse theo byte quét hợp với quy mô hiện tại. Đổi ý nếu: công ty ký hợp đồng
Microsoft (credit Azure, Power BI sẵn có), khách hàng lớn yêu cầu AWS, hoặc khối lượng quét tăng
tới mức BigQuery Editions/Redshift provisioned rẻ hơn rõ rệt.
````

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Bộ test pass (hàm đúng, xử lý lỗi, tài liệu đủ mục, bảng ≥ 8 dòng) | 20 |
| Bảng ánh xạ chính xác, có ghi chú chỗ chỉ tương đương gần đúng | 20 |
| Phân tích chi phí chỉ ra đúng khoản khác biệt (mô hình warehouse, phí cố định, egress, chiết khấu) | 15 |
| Ma trận quyết định: tiêu chí và trọng số có lý do, có thử độ nhạy | 15 |
| Lock-in: đánh giá theo thành phần, chiến lược cụ thể, nêu cái giá của tính di động | 20 |
| Khuyến nghị rõ, nhất quán với ma trận, có điều kiện đổi ý | 10 |
