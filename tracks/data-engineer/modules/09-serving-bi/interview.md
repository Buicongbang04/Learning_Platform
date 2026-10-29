# Câu hỏi phỏng vấn: Data Serving & BI

## Serving layer là gì? Vì sao DE cần quan tâm, không để analyst tự lo?

Serving layer là tầng cuối của data platform, nơi dữ liệu đã transform được tổ chức và phân phối cho người dùng:
BI dashboard, data app, API, ML, và công cụ nghiệp vụ qua Reverse ETL.

DE cần quan tâm vì các quyết định ở tầng này ảnh hưởng tới:

- **Tính nhất quán**: metric định nghĩa ở đâu, có một nguồn sự thật không.
- **Hiệu năng và chi phí**: dashboard query thẳng fact 1 tỷ dòng mỗi lần mở thì tốn tiền và chậm.
- **Độ mới và SLA**: refresh khi nào, ai được báo khi trễ.
- **Bảo mật**: BI tool dùng tài khoản nào, có đọc được PII không.

Analyst giỏi trả lời câu hỏi nghiệp vụ. DE đảm bảo nền dưới đó nhanh, đúng và ổn định.

## Semantic layer giải quyết vấn đề gì? Kể tên vài công cụ.

Vấn đề: cùng một metric ("doanh thu", "active user") bị định nghĩa lại ở nhiều dashboard, mỗi chỗ một kiểu
(có tính đơn huỷ không, theo ngày đặt hay ngày giao), dẫn tới các con số mâu thuẫn và mất niềm tin.

Semantic layer định nghĩa một lần entity, dimension, measure và metric. Công cụ nhận câu hỏi dạng "metric X theo
dimension Y, lọc Z" rồi tự sinh SQL. Lợi ích: nhất quán, tái sử dụng, version control (metric as code), và kiểm
soát quyền tập trung.

Công cụ: dbt Semantic Layer (MetricFlow), Cube, LookML của Looker, AtScale, measure DAX trong Power BI, Models và
Metrics trong Metabase.

## Additive, semi-additive và non-additive measure khác nhau thế nào? Ảnh hưởng gì khi làm bảng aggregate?

- **Additive**: cộng được theo mọi dimension (`sum(price)`, `count(*)`). Lưu thẳng vào bảng aggregate, rollup tiếp
  thoải mái.
- **Semi-additive**: cộng được theo một số dimension nhưng không theo thời gian (tồn kho, số dư). Cộng tồn kho 30
  ngày là vô nghĩa, phải lấy giá trị cuối kỳ hoặc trung bình.
- **Non-additive**: không cộng được (`count distinct`, ratio, median, percentile).

Khi pre-aggregate: với ratio, lưu tử và mẫu (`revenue`, `orders`) rồi chia khi query. Với `count distinct`, hoặc
tính lại từ dữ liệu chi tiết, hoặc lưu sketch như HyperLogLog (BigQuery `HLL_COUNT`, Druid, DuckDB
`approx_count_distinct`) để merge được với sai số nhỏ.

## Vì sao "trung bình của trung bình" sai? Cho ví dụ.

Ngày 1: doanh thu 1.000 trên 10 đơn (AOV 100). Ngày 2: 300 trên 1 đơn (AOV 300). Trung bình hai AOV = 200. AOV
đúng của hai ngày = 1.300 / 11 ≈ 118. Trung bình các ratio coi mỗi ngày nặng như nhau, bỏ qua số đơn mỗi ngày.

Cách đúng: aggregate tử và mẫu ở grain đích rồi mới chia: `SUM(revenue) / SUM(orders)`. Semantic layer định nghĩa
ratio metric theo kiểu numerator/denominator chính vì lý do này.

## So sánh view, materialized view, bảng aggregate và cache.

| | View | Materialized view | Bảng aggregate (job) | Cache |
| --- | --- | --- | --- | --- |
| Lưu kết quả | Không | Có | Có | Có (tạm) |
| Độ mới | Luôn mới | Theo refresh | Theo lịch job | Theo TTL / invalidation |
| Ai lo refresh | Không cần | Engine | Pipeline của bạn | Ứng dụng |
| Linh hoạt logic | Cao | Hạn chế theo engine | Cao | Không áp dụng |
| Latency | Chậm nhất | Nhanh | Nhanh | Nhanh nhất |

Chọn view khi dữ liệu nhỏ hoặc cần luôn mới. Materialized view khi logic đơn giản và engine hỗ trợ incremental
refresh. Bảng aggregate khi cần kiểm soát hoàn toàn (late data, idempotency, test). Cache đặt trước tất cả cho
các truy vấn lặp lại nhiều.

## Làm sao đảm bảo bảng aggregate cho số đúng?

1. **Reconcile tự động** sau mỗi lần build: tổng revenue, số đơn, số dòng của aggregate so với nguồn (cùng bộ lọc),
   với dung sai cho số thực, và so theo từng partition ngày để khoanh vùng lệch.
2. **Test grain**: khoá grain (ngày, state) phải unique, không null.
3. **Idempotency**: build theo khoảng ngày bằng delete+insert hoặc MERGE, chạy lại không nhân đôi.
4. **Late-arriving data**: tính lại cửa sổ lùi (vài ngày gần nhất) hoặc dựa trên `updated_at` của nguồn.
5. **Freshness check**: cảnh báo khi `max(updated_at)` quá cũ.
6. **Fan-out**: cẩn thận join 1-n trước khi `SUM` (join orders với payments và items cùng lúc sẽ nhân dòng).

## Fan-out trong join là gì và tránh thế nào?

Fan-out xảy ra khi join bảng ở grain đơn hàng với hai bảng con 1-n (order_items và order_payments). Một đơn 2
item và 2 payment thành 4 dòng, nên `SUM(payment_value)` bị nhân đôi.

Cách tránh: aggregate từng bảng con về grain chung (order_id) trước, rồi mới join; hoặc dùng
`COUNT(DISTINCT ...)` cho đếm. Semantic layer tốt (MetricFlow, LookML với `symmetric aggregates`) tự xử lý fan-out.
Luôn kiểm tra số dòng trước và sau join khi viết model.

## Bạn chọn BI tool thế nào cho một startup 30 người và cho một tập đoàn 5.000 người?

**Startup**: Metabase hoặc Superset self-host (miễn phí, một container), hoặc Looker Studio nếu đã dùng Google.
Ưu tiên cài nhanh, người không biết SQL tự hỏi được. Định nghĩa metric trong dbt để sau này đổi tool không mất.

**Tập đoàn**: các yếu tố là hệ sinh thái sẵn có (Microsoft thì Power BI), yêu cầu governance (Looker với LookML
hoặc semantic layer trung tâm), SSO/RLS, số người dùng và mô hình license, khả năng embed, hỗ trợ của vendor.
Thường có nhiều tool cùng tồn tại, nên semantic layer độc lập tool (dbt SL, Cube, AtScale) càng có giá trị.

Dù tool nào: dùng service account read-only, chỉ mở schema mart, bật caching, theo dõi query chậm.

## Dashboard vận hành khác dashboard chiến lược thế nào? Bạn thiết kế dashboard vận hành giao hàng cho Olist ra sao?

Dashboard vận hành phục vụ người xử lý việc hằng ngày: cần dữ liệu mới (phút–giờ), chỉ ra ngoại lệ, và dẫn tới
hành động. Dashboard chiến lược nhìn xu hướng tuần/tháng cho lãnh đạo.

Thiết kế cho Olist:

- **Hàng 1, KPI tile**: đơn hôm nay (vs hôm qua), late delivery rate 7 ngày (vs target 5%), số đơn quá hạn chưa
  giao, review score trung bình 7 ngày. Màu đỏ chỉ khi vượt ngưỡng.
- **Hàng 2, xu hướng**: line đơn và late rate theo ngày; bar ngang late rate theo state/seller.
- **Hàng 3, hành động**: bảng đơn quá hạn chưa giao, seller, số ngày trễ, link sang chi tiết.
- Filter: khoảng ngày (mặc định 7 ngày), state, category. Hiển thị "cập nhật lúc …".
- Dữ liệu từ bảng aggregate refresh 15 phút, alert Slack khi late rate vượt ngưỡng.

## Khi nào dùng Streamlit thay vì BI tool? Bạn tổ chức code Streamlit để test được ra sao?

Streamlit hợp khi cần logic tuỳ biến mà BI tool khó làm: what-if, gọi model ML, form nhập liệu, workflow nội bộ,
prototype nhanh. BI tool hợp với self-service, nhiều người xem, quản lý quyền và chia sẻ.

Tổ chức code:

- `logic.py` thuần Python: lọc, tính KPI, % thay đổi, format. Nhận/trả DataFrame và dict, không import
  streamlit. Viết unit test bằng pytest.
- `data.py`: truy cập dữ liệu, query tham số hoá, bọc bằng `st.cache_data`/`st.cache_resource` ở tầng app.
- `app.py`: chỉ widget và vẽ.

Lưu ý: Streamlit chạy lại cả script mỗi tương tác, nên cache phần đắt; dùng `st.session_state` cho trạng thái;
không nhúng credentials trong code (dùng `st.secrets`).

## Thiết kế API phục vụ metric cho seller (mỗi seller xem doanh thu của mình) với 500 request/giây.

- **Dữ liệu**: pre-compute `agg_seller_daily` (seller_id, date, orders, revenue, late_orders) bằng job batch hoặc
  streaming. Không query fact khi có request.
- **Store**: 500 rps với truy vấn theo key (seller_id, khoảng ngày) hợp với Postgres có index
  `(seller_id, date)` + cache Redis, hoặc ClickHouse/Pinot nếu cần filter linh hoạt.
- **API**: `GET /sellers/{id}/metrics?from=&to=&grain=day`. Validate ngày (tối đa 1 năm), whitelist grain.
- **AuthZ**: token chứa seller_id; API ép filter `seller_id = token.seller_id` (row-level), không tin tham số path.
- **Cache**: key gồm seller, khoảng ngày, grain, `data_version`; TTL vài phút; trả `data_updated_at`.
- **Bảo vệ**: rate limit theo client, timeout query, pagination, monitoring p95 latency và tỉ lệ cache hit.

## Reverse ETL là gì? Khác ETL thế nào? Cho use case.

ETL/ELT đưa dữ liệu từ hệ thống nghiệp vụ vào warehouse. Reverse ETL đẩy dữ liệu đã làm giàu từ warehouse về
công cụ nghiệp vụ (CRM, marketing, support), để người dùng hành động ngay trong công cụ họ quen.

Khác biệt chính: đích là API SaaS bạn không kiểm soát, nên gặp rate limit, giới hạn batch, mapping field, lỗi từng
record, và phải idempotent.

Use case: đẩy LTV và segment khách vào HubSpot để sales ưu tiên; tạo audience "mua đồ nội thất 30 ngày qua" cho
Facebook Ads; cập nhật số lần giao trễ vào Zendesk để CS xử lý khiếu nại nhanh. Công cụ: Hightouch, Census,
Segment Reverse ETL, RudderStack.

## Bạn tự viết job Reverse ETL sang CRM thế nào để chạy lại an toàn?

1. **Model nguồn** trong warehouse với khoá ổn định (`customer_unique_id`) và các field cần đẩy.
2. **Diff**: tính hash từng bản ghi, so với state đã lưu (`external_id → hash`), chỉ gửi bản ghi mới/đổi.
3. **Batching** theo giới hạn API (ví dụ 100 bản ghi/lần).
4. **Idempotent upsert** theo external ID: gửi lại không tạo trùng.
5. **Retry** lỗi tạm thời (429, 5xx, timeout) bằng exponential backoff + jitter, giới hạn số lần; lỗi vĩnh viễn
   (400) không retry, ghi vào danh sách lỗi.
6. **Cập nhật state chỉ sau khi batch thành công**; job chết giữa chừng thì lần sau gửi tiếp phần còn thiếu.
7. **Quan sát**: log số bản ghi gửi/thành công/lỗi, alert khi tỉ lệ lỗi cao; tôn trọng consent và chỉ đẩy field
   cần thiết.

## Khi nào nên mua Hightouch/Census thay vì tự viết?

Mua khi: nhiều đích (5+ SaaS), người làm marketing muốn tự tạo audience, cần UI quản lý mapping, log lỗi từng
record, và connector được vendor bảo trì khi API đích thay đổi. Chi phí bảo trì connector tự viết thường bị đánh
giá thấp.

Tự viết khi: một hai đích đơn giản, dữ liệu nhạy cảm không muốn qua bên thứ ba, hoặc chi phí license không hợp lý
với volume. Dù tự viết, vẫn áp dụng đủ diff, idempotency, retry, state, monitoring.

## Cache cho dashboard và API: invalidation làm thế nào?

- **TTL**: đơn giản, chấp nhận dữ liệu cũ tối đa N giây. Chọn TTL nhỏ hơn hoặc bằng chu kỳ refresh.
- **Versioned key**: đưa `data_version` (thời điểm refresh cuối của bảng nguồn) vào key. Pipeline refresh xong thì
  version đổi, request mới tự trượt sang key mới, key cũ hết hạn dần. Tránh phải xoá thủ công.
- **Event-based**: pipeline phát sự kiện "bảng X đã refresh", service xoá key phụ thuộc X.
- **Cache warming**: chạy sẵn các query phổ biến ngay sau refresh để người đầu tiên không chịu cache miss.

Cẩn thận **cache stampede**: nhiều request cùng miss một key nặng. Dùng lock hoặc "single flight" để chỉ một
request tính.

## Làm sao quản lý thay đổi schema của bảng serving mà không làm hỏng dashboard?

- Coi bảng serving như API công khai: có **data contract** (tên cột, kiểu, ý nghĩa, owner).
- Thay đổi **additive** (thêm cột) thì an toàn. Đổi tên/xoá cột là breaking: thêm cột mới, giữ cột cũ một thời gian,
  thông báo, rồi mới xoá; hoặc tạo `v2` song song.
- Dùng **view làm lớp ổn định** trên bảng vật lý, đổi logic bên dưới mà giữ interface.
- Dùng lineage/exposures (dbt exposures, catalog) để biết dashboard nào phụ thuộc cột nào trước khi đổi.
- CI chạy test contract (dbt `contract: enforced`) để chặn thay đổi breaking ngoài ý muốn.

## Thiết kế hệ thống serving cho Olist: dashboard nội bộ, API cho seller, và đồng bộ CRM.

```
Postgres (OLTP) + Kafka order events
        │ ELT (Airbyte / Debezium)
        ▼
Lakehouse/Warehouse: raw → staging → marts (dbt)
        │
        ├── Semantic layer (dbt SL / Cube): revenue, orders, aov, late_rate
        │       └── Metabase: dashboard vận hành (refresh 15'), dashboard tuần cho lãnh đạo
        ├── agg_seller_daily (incremental, 15') ──► Postgres serving + Redis ──► Seller API
        └── customer_360 (daily) ──► Reverse ETL (diff, batch, retry) ──► HubSpot
```

Điểm cần nói rõ: metric định nghĩa một chỗ và dùng cho cả ba nhánh; mỗi nhánh có SLA freshness riêng; bảng
serving có test reconcile và freshness; API có AuthZ theo seller và cache có version; Reverse ETL chỉ đẩy field
cần thiết và tôn trọng consent; lineage để biết thay đổi model ảnh hưởng dashboard/API/CRM nào; chi phí kiểm soát
bằng pre-aggregation và cache.

## Cache key chỉ có câu SQL có đủ khi mỗi seller có quyền khác nhau không?

Chưa chắc. Kết quả còn phụ thuộc tenant, danh tính/phạm vi quyền và phiên bản dữ liệu.
Nếu dùng chung key sai, người sau có thể nhận dữ liệu của người trước. Kiểm quyền ở backend/database
và test hai danh tính đọc chéo; filter trên giao diện không thay thế phân quyền.

## Đổi metric từ đơn đã giao sang mọi đơn chưa hủy có chỉ cần sửa WHERE không?

SQL là một phần. Cần định nghĩa phiên bản, thông báo consumer, chọn ngày hiệu lực, đối chiếu v1/v2
và giữ cách kiểm lại lịch sử. Nếu âm thầm thay WHERE, dashboard có thể thay nghĩa dù tên cột vẫn như cũ.

## Đội Data Science cần dữ liệu huấn luyện cho model dự đoán đơn bị review xấu. Bạn dựng phần dữ liệu thế nào?

1. **Định nghĩa label và thời điểm**: label = `review_score <= 2`, thời điểm dự đoán = lúc đặt đơn (hoặc lúc
   giao). Mọi feature chỉ được dùng dữ liệu **trước** thời điểm đó.
2. **Bảng feature lịch sử** theo entity và thời điểm (`seller_id`, `feature_ts`, `seller_late_orders_30d`,
   ...), tính bằng pipeline batch có test như mọi mart.
3. **Point-in-time join** (ASOF JOIN / `merge_asof`) giữa label và feature để tránh data leakage. Join với giá
   trị mới nhất sẽ cho điểm offline đẹp giả rồi sụp ở production.
4. **Version training set**: ghi snapshot bất biến (đường dẫn có version, hoặc Delta/Iceberg version), lưu
   cùng model kèm version code và khoảng thời gian label.
5. **Nếu model chạy online**: cùng định nghĩa feature materialize sang online store (Redis/DynamoDB), qua
   feature store như Feast, để không có training-serving skew. Chưa có model online thì chưa cần feature store.

## Training-serving skew là gì và DE ngăn nó thế nào?

Là khi feature lúc serve tính khác lúc train: logic viết hai lần (SQL cho train, code ứng dụng cho serve),
khác múi giờ, khác cách xử lý null, hoặc dữ liệu online trễ hơn offline. Model nhận input khác phân phối nó
đã học nên dự đoán kém mà không báo lỗi.

Cách ngăn: một định nghĩa feature duy nhất sinh cả offline và online store (feature store), cùng một hàm
transform được test dùng ở cả hai nơi, log feature thực tế lúc serve rồi so phân phối với training set
(kiểm tra như data quality check), và theo dõi freshness của online store.
