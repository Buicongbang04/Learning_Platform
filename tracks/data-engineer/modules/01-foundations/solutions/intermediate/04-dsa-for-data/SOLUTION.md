# Lời giải: DSA cho Data Engineer

Mã đầy đủ ở `dsa.py`. Phần dưới giải thích vì sao từng cấu trúc làm như vậy và nó xuất hiện ở đâu trong
công cụ thật.

## 1. Hash partitioning

`hash64(key) % n` đủ cho bài này. Hai điều quan trọng hơn công thức:

- **Hàm băm phải ổn định giữa các tiến trình.** `hash("o1")` của Python đổi theo `PYTHONHASHSEED` mỗi lần
  chạy, nên hai worker sẽ đưa cùng một key vào hai partition khác nhau. Kafka dùng murmur2, Spark dùng
  murmur3; cả hai đều tất định.
- **`mod n` đổi gần hết vị trí khi `n` đổi.** Tăng partition của topic Kafka làm key cũ sang partition
  khác và mất thứ tự theo key. Khi số nút thay đổi thường xuyên thì dùng consistent hashing (bài advanced 01).

Test đếm 16.000 khoá trên 8 partition: hash tốt cho mỗi partition khoảng 2.000 ± 2%. Nếu một key chiếm
phần lớn dữ liệu (seller lớn, `NULL`), hash không cứu được; đó là data skew, xử lý bằng salting.

## 2. External merge sort

Hai pha, mỗi pha đọc và ghi dữ liệu đúng một lần:

1. `list(islice(it, max_lines))` lấy từng chunk, sort trong RAM, ghi thành run. Bộ nhớ tối đa `max_lines` dòng.
2. `heapq.merge(*runs)` giữ một heap kích thước bằng số run, mỗi bước lấy dòng nhỏ nhất rồi đọc dòng tiếp
   theo của run đó. Bộ nhớ tỉ lệ với số run, không tỉ lệ với dữ liệu.

`ExitStack` + `closing` bảo đảm mọi tệp run được đóng kể cả khi ghi `out_path` lỗi, và `finally` xoá run để
job chạy lại không đọc nhầm run cũ. Với 10.500 dòng và `max_lines=1000`, có 11 run.

Đây đúng là cách Spark làm khi một partition không vừa bộ nhớ lúc sort-merge join hoặc `ORDER BY`: dữ liệu
**spill** xuống đĩa thành nhiều tệp đã sort rồi merge. Thấy "spill (disk)" lớn trong Spark UI nghĩa là
đang chạy external sort; tăng bộ nhớ executor hoặc số partition để giảm nó. Lệnh `sort` của GNU coreutils
cũng làm vậy (`sort -S 1G -T /tmp big.csv`).

Khi số run quá lớn (hàng nghìn), mở cùng lúc chừng ấy tệp có thể vượt giới hạn file descriptor; khi đó
merge nhiều vòng (merge 100 run một lần thành run lớn hơn).

## 3. Top-k bằng heap

Sort toàn bộ tốn bộ nhớ và thời gian tỉ lệ với n. Min-heap kích thước k chỉ tốn bộ nhớ k và thời gian
tỉ lệ với n nhân log k. Đỉnh heap là phần tử kém nhất trong top-k hiện tại, nên phần tử mới chỉ cần so
với đỉnh: tốt hơn thì `heapreplace`, không thì bỏ.

Phần khó là tie-break: kết quả yêu cầu cùng value thì key tăng dần, nên trong heap "kém hơn" là key lớn
hơn. Lớp `_ReverseStr` đảo phép so sánh của chuỗi. Bỏ tie-break thì kết quả không tất định: hai lần chạy
có thể trả top 10 khác nhau khi giá trị bằng nhau, và test so khớp sẽ chập chờn.

Trong thực tế: top sản phẩm theo doanh thu từ stream, heavy hitters trong log. Spark có `takeOrdered`
dùng đúng ý tưởng này ở từng partition rồi gộp các top-k cục bộ.

## 4. Bloom filter

Công thức tối ưu cho n phần tử và tỉ lệ false positive mục tiêu p:

$$
m = \left\lceil -\frac{n \ln p}{(\ln 2)^2} \right\rceil, \qquad k = \mathrm{round}\left(\frac{m}{n} \ln 2\right)
$$

Với n = 1000, p = 1%: m = 9586 bit (khoảng 1,2 KB, tức 9,6 bit mỗi phần tử), k = 7. Mỗi khi muốn giảm p
đi 10 lần thì cần thêm khoảng 4,8 bit mỗi phần tử. Lưu 1000 event id dạng chuỗi 20 byte trong `set` tốn
hàng chục KB; Bloom filter tốn 1,2 KB.

**Double hashing** (Kirsch–Mitzenmacher): tính hai giá trị băm rồi lấy `h1 + i * h2` thay vì k hàm băm
độc lập, độ chính xác gần như tương đương mà chỉ băm một lần. `h2 | 1` cho số lẻ để các vị trí không lặp
sớm khi m chẵn.

Đo thật: 5000 phần tử, tỉ lệ dương tính giả trên 20.000 phần tử lạ là khoảng 1,1%, sát lý thuyết 1%.

Dùng ở đâu:

- **Khử trùng lặp event**: kiểm tra `event_id in bloom`; "không" là chắc chắn mới, "có" thì mới cần tra
  kho thật (Redis, bảng). Phần lớn request không phải chạm kho.
- **Bỏ qua dữ liệu khi đọc**: Cassandra và RocksDB giữ Bloom filter cho mỗi SSTable để không đọc tệp chắc
  chắn không chứa key; Parquet có bloom filter theo cột để bỏ qua row group khi lọc `WHERE id = ...`.
- **Join**: Spark có runtime bloom filter join, lọc bớt bảng lớn trước khi shuffle.

Giới hạn: không xoá được phần tử (cần counting Bloom filter), và nếu thêm nhiều hơn n đã thiết kế thì tỉ lệ
dương tính giả tăng nhanh. `expected_fp_rate(m, k, n_thực)` cho bạn biết khi nào phải dựng lại filter.

## 5. HyperLogLog

Ý tưởng: trong các giá trị băm ngẫu nhiên, thấy một giá trị bắt đầu bằng r bit 0 thì nhiều khả năng đã
có khoảng 2 mũ r phần tử khác nhau. Một quan sát thì nhiễu lớn, nên chia thành m = 2 mũ p nhóm theo p bit
đầu, mỗi nhóm nhớ số bit 0 lớn nhất, rồi lấy trung bình điều hoà:

$$
E = \alpha_m \, m^2 \left( \sum_{j=1}^{m} 2^{-M_j} \right)^{-1}
$$

Sai số chuẩn khoảng 1,04 chia căn m. Với p = 12: 4096 register, mỗi register một byte, 4 KB cho bất kỳ
cardinality nào, sai số chuẩn 1,6%. Khi cardinality nhỏ (E không vượt 2,5m) còn nhiều register bằng 0,
công thức trên lệch, nên chuyển sang linear counting: m nhân ln(m / V) với V là số register bằng 0.

Đo thật trong bài: 500 phần tử ra 504, 20.000 ra 20.029, 200.000 ra 204.496 (sai 2,2%, trong 3σ).

`merge` là max từng register và cho đúng HLL của hợp hai tập. Đây là tính chất quý nhất với DE: lưu HLL
của mỗi ngày, rồi số khách unique của tuần/tháng là merge 7 hay 30 sketch, không phải quét lại dữ liệu
thô. Không merge được phép giao trực tiếp; giao suy ra từ `|A| + |B| - |A ∪ B|` thì sai số lớn khi giao nhỏ.

Dùng ở đâu: `approx_count_distinct` (Spark, BigQuery `APPROX_COUNT_DISTINCT` và `HLL_COUNT.*`), Redis
`PFADD`/`PFCOUNT`, Druid/Pinot lưu sketch trong segment, Trino `approx_distinct`.

## Mở rộng

- Count-Min Sketch cho tần suất xấp xỉ (heavy hitters trong stream không giới hạn khoá).
- Thư viện Apache DataSketches (Theta, KLL cho quantile) dùng trong Druid và Spark.
- External sort theo khoá CSV: tách khoá ra và sort `(key, line)`, rồi dùng nó để merge join hai tệp lớn.
