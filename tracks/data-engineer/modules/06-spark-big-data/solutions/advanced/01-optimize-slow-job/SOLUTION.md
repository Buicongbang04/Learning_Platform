# Hướng giải: Tối ưu job báo cáo seller

Bài này không có một đáp án duy nhất. Dưới đây là hướng làm, các quyết định cần cân nhắc và rubric.

## Anti-pattern trong starter và cách sửa

| Anti-pattern | Vì sao chậm | Sửa |
| --- | --- | --- |
| `items.select("seller_id").distinct().collect()` | Kéo dữ liệu về driver; với hàng triệu key thì OOM driver | Không cần danh sách key: dùng `groupBy` |
| Vòng `for sid in seller_ids` gọi `count()`, `first()` | Mỗi vòng 3 Spark job, mỗi job quét lại `items` và join lại; N seller = 3N job, chạy tuần tự trên driver | Một `join` + một `groupBy("seller_id").agg(...)` |
| `spark.createDataFrame(rows)` từ list Python | Dữ liệu đi vòng driver, mất song song, mất lineage | Giữ dữ liệu trong DataFrame |
| Python UDF `tier` | Serialize từng dòng sang Python worker (`BatchEvalPython`), Catalyst không tối ưu | `F.when(gmv >= 1000, "gold").when(gmv >= 200, "silver").otherwise("bronze")` |
| `tier_counts` lặp 3 lần `filter().count()` | 3 job, mỗi job tính lại cả report vì không cache | Một `groupBy("tier").count().collect()` |

## Phác thảo lời giải

```python
from pyspark.sql.functions import broadcast

def seller_report(spark, orders, items, sellers):
    delivered = orders.filter(F.col("order_status") == "delivered").select("order_id")
    gmv = F.round(F.sum("price"), 2)
    return (
        items.select("order_id", "seller_id", "price")
        .join(delivered, "order_id")
        .groupBy("seller_id")
        .agg(F.countDistinct("order_id").alias("n_orders"), gmv.alias("gmv"))
        .join(broadcast(sellers.select("seller_id", "seller_state")), "seller_id")
        .withColumn("avg_ticket", F.round(F.col("gmv") / F.col("n_orders"), 2))
        .withColumn("tier", F.when(F.col("gmv") >= 1000, "gold")
                             .when(F.col("gmv") >= 200, "silver").otherwise("bronze"))
        .select("seller_id", "seller_state", "n_orders", "gmv", "avg_ticket", "tier")
        .orderBy(F.desc("gmv"), F.asc("seller_id"))
    )

def tier_counts(report):
    return {r["tier"]: r["count"] for r in report.groupBy("tier").count().collect()}
```

Lưu ý `tier_counts`: một action không nhất thiết là một Spark job. Với AQE, mỗi query stage có thể
chạy như một job riêng, và broadcast exchange cũng tạo job. Vì vậy test so với mốc "một action
groupBy + collect", không đếm cứng là 1.

## Quyết định thiết kế cần cân nhắc

- **Join trước hay aggregate trước?** Aggregate `items` theo `seller_id` sau khi lọc delivered làm giảm
  dữ liệu trước khi join `sellers`; `sellers` nhỏ nên broadcast, không shuffle thêm.
- **`countDistinct` vs `count`**: một đơn có nhiều item của cùng seller, phải đếm distinct.
  `countDistinct` sinh thêm một tầng aggregate; trên dữ liệu rất lớn có thể dùng
  `approx_count_distinct` nếu chấp nhận sai số.
- **Có nên cache report không?** Nếu report được dùng cho nhiều output (ghi Parquet, `tier_counts`,
  gửi Reverse ETL) thì `cache()` ngay sau khi tạo và `unpersist()` khi xong. Không cache trong
  `seller_report` vì `cache` + action sẽ phá ràng buộc lazy, và người gọi mới biết có dùng lại hay không.
- **Làm tròn ở đâu**: tính `avg_ticket` từ `gmv` đã làm tròn để khớp đặc tả; trong thực tế nên thống
  nhất với nghiệp vụ.
- **Seller không có trong `sellers`**: inner join loại họ; nếu nghiệp vụ cần giữ, dùng left join và
  điền `seller_state = "unknown"`.

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Test correctness pass | 25 |
| `seller_report` lazy (0 job), không còn vòng lặp Python/collect | 20 |
| Không Python UDF, dùng built-in function | 15 |
| `tier_counts` chỉ một action | 10 |
| Broadcast dimension nhỏ, lọc và chọn cột sớm | 10 |
| Docstring giải thích đúng từng anti-pattern và chi phí của nó | 10 |
| Đọc và giải thích được `explain()` (số `Exchange`, loại join) | 10 |

Trừ điểm: đổi chữ ký hàm, dùng `toPandas()` để tính, cache vô điều kiện mà không unpersist.
