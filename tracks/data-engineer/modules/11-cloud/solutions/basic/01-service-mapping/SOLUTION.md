# Lời giải: bảng dịch vụ tương đương

## Cách làm

- **CATALOG**: điền đủ 18 ô. Đây là phần "học thuộc" quan trọng nhất của bài: phỏng vấn DE hay hỏi
  "Bạn dùng GCP, vậy bên AWS bạn sẽ dùng gì thay Dataflow/BigQuery?".
- **Index ngược**: dựng một lần `tên chuẩn viết thường -> (nhóm, cloud)` để `lookup` là O(1),
  thay vì lặp lồng hai vòng mỗi lần gọi.
- **Chuẩn hoá tên**: `" ".join(name.lower().split())` vừa bỏ khoảng trắng hai đầu vừa gộp khoảng
  trắng giữa. Thử tên nguyên bản trước (để `"aws glue"` vẫn có cơ hội khớp alias nếu có), sau đó bỏ
  tiền tố hãng, **tiền tố dài trước** (`google cloud ` trước `google `). Mỗi ứng viên lại đi qua
  `ALIASES` nên `"Azure SQL Database"` → `"sql database"` khớp tên chuẩn, `"Azure SQL"` → alias
  `"azure sql"`.
- **ValueError** cho tên lạ và cloud lạ: đừng trả `None`, lỗi im lặng sẽ lan sang chỗ khác.
- **Bảng Markdown**: ghép list dòng rồi `"\n".join(...) + "\n"`.

## Lưu ý về "tương đương"

Ánh xạ 1-1 là đơn giản hoá để nhớ. Thực tế:

- **Glue vs Data Factory vs Dataflow** khác bản chất: Glue là Spark serverless + Data Catalog +
  crawler; Data Factory thiên về orchestration/copy (Mapping Data Flow chạy Spark phía sau);
  Dataflow là Apache Beam managed, mạnh cả batch lẫn streaming. GCP có thêm Data Fusion (gần ADF
  hơn) và Dataproc (Spark managed, gần EMR).
- **RDS** là họ dịch vụ (Postgres, MySQL, SQL Server, Oracle, Aurora); **Azure SQL Database** chỉ là
  SQL Server, Postgres trên Azure là *Azure Database for PostgreSQL*.
- **Synapse Analytics** đang được Microsoft dồn sang **Microsoft Fabric** (Fabric Warehouse,
  OneLake); JD mới của Azure hay ghi Fabric.
- **Kinesis Data Streams** gần Kafka (shard, retention, replay); **Pub/Sub** là message bus không
  có khái niệm partition do người dùng quản; **Event Hubs** có endpoint tương thích Kafka.
