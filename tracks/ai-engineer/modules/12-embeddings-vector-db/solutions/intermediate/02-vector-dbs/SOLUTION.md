# Lời giải: bốn vector store, một giao diện

## Cách làm

**`distance_to_cosine`**: với vector đơn vị, $$\lVert a - b\rVert^2 = 2 - 2c$$, nên `squared_l2` thành $$1 - d/2$$, `l2` thành
$$1 - d^2/2$$, `cosine_distance` thành $$1 - d$$. **`latency_summary`**: `np.percentile(a, 50)`, `np.percentile(a, 95)`,
`a.mean()`, ép `float`. **`sql_quote`**: `"'" + value.replace("'", "''") + "'"`.

**`FaissStore`**: `upsert` xoá id cũ của uid đã có (`remove_ids`, xoá khỏi hai `dict`), cấp id mới tăng dần, ghi ba `dict`,
`add_with_ids`. `search` với `where` dựng mảng id có metadata khớp; rỗng thì trả `[]` ngay (một `IDSelectorBatch` rỗng vẫn
chạy nhưng vô ích); truyền `SearchParameters(sel=IDSelectorBatch(...))`; bỏ mọi id `-1` FAISS điền khi thiếu kết quả.

**`QdrantStore`**: `QdrantClient(path=...)` hoặc `":memory:"`; tạo collection nếu chưa có với `Distance.COSINE`; point id là
`str(uuid5(NAMESPACE_URL, uid))`, payload `{"uid": uid, **meta}`; upsert theo lô 1 024; `query_points(..., query_filter=Filter(
must=[FieldCondition(key, match=MatchValue(value))]))`; trả `(payload["uid"], score)`; `count(exact=True)`; `close()`.

**`LanceStore`**: lần đầu `create_table` từ một bảng Arrow (`_arrow` có sẵn), sau đó
`merge_insert("uid").when_matched_update_all().when_not_matched_insert_all().execute(...)`. Tìm bằng
`.distance_type("cosine")`, `where` ghép từ `sql_quote`, đổi `_distance` về cosine. Xoá bằng `uid IN (...)`.

## Kết quả thật

PC của track, 4 luồng, mọi store chạy trên đĩa, 300 câu ghim, k = 10, gọi từng câu
(`.superpowers/scratch/logs/vectordbs_results.txt`, lần chạy đầu; cả notebook 13 phút; lần chạy lại Chroma cho 0.994 / 0.905
và p50 2.7 ms, Qdrant nạp 166 s):

| Store | Nạp 61 425 vector | Đĩa | recall ANN@10 | Recall@10 (nhãn) | p50 | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| FaissStore (`IndexFlatIP`, exact) | 0.2 s | 240 MB (`write_index`) | 0.998 | 0.905 | 13.8 ms | 17.3 ms |
| ChromaStore (HNSW) | 29.7 s | 284 MB | 0.993 | 0.902 | 3.2 ms | 4.5 ms |
| QdrantStore (local mode) | 160.8 s | 605 MB | 0.999 | 0.905 | 245 ms | 291 ms |
| LanceStore (quét phẳng) | 1.0 s | 241 MB | 1.000 | 0.905 | 295 ms | 336 ms |
| LanceStore + `IVF_HNSW_SQ` (dựng 8.4 s, đĩa 313 MB) | | | 0.951 | 0.888 | 7.6 ms | 11.6 ms |
| FAISS HNSW M=16 (dựng 10.8 s), efSearch 16 | | | 0.932 | 0.875 | 0.14 ms | 0.22 ms |
| FAISS HNSW, efSearch 64 | | | 0.987 | 0.898 | 0.35 ms | 0.48 ms |

Lọc `where law = văn bản chứa điều đúng đầu tiên` (lọc trong truy vấn): Recall@10 theo nhãn **0.978** ở cả bốn store; p50
FaissStore 3.8 ms, LanceStore 13.1 ms, ChromaStore 94 ms, QdrantStore 789 ms. Post-filter trên FAISS HNSW (efSearch 64): lấy
top-10 rồi lọc thì 282/300 câu thiếu kết quả, top-100 còn 76/300, top-1 000 còn 33/300; trong đó 13 câu có văn bản ít hơn 10
điều nên không cách nào đủ 10. Xoá 197 điều đúng của 300 câu: không câu nào còn thấy điều đã xoá; mở lại từ đĩa: Chroma 0.02 s,
LanceDB 0.18 s, Qdrant 7.8 s (local mode nạp lại mọi point vào RAM).

## Đọc kết quả

- **Không store nào thắng mọi cột.** FAISS nạp nhanh nhất và lọc nhanh nhất (exact trên tập con), nhưng bạn phải tự viết mọi
  thứ quanh nó. Chroma truy vấn nhanh nhất nhờ HNSW nhưng nạp chậm hơn 100 lần FAISS và lọc chậm. LanceDB nạp như ghi một tệp
  cột, nhẹ trên đĩa, chậm khi chưa có index và nhanh hẳn khi có. **Qdrant local mode** là chế độ nhúng Python cho thử nghiệm
  (chính `qdrant-client` in cảnh báo "Local mode is not recommended for collections with more than 20,000 points"): không có HNSW, quét bằng numpy, lưu cả payload; con số của nó **không**
  phải con số của Qdrant server (Rust, HNSW, payload index), chạy bằng Docker.
- **Recall ANN dưới 1 gần như không đổi Recall@10 theo nhãn**: Chroma đạt recall ANN 0.993 và 0.994 ở hai lần chạy, Recall@10
  0.902 và 0.905 (HNSW của Chroma dựng đa luồng nên không tái lập tới từng chữ số). Index IVF_HNSW_SQ của LanceDB
  (lượng tử 8 bit, tham số mặc định) mất nhiều hơn: 0.951 → 0.888. Chênh dense và hybrid ở module 13 cỡ 0.01; một index cấu
  hình tệ có thể ăn hết lợi ích đó, nên luôn đo cả hai thứ recall.
- **Lọc là tính năng chứ không phải hậu xử lý.** Lọc trong truy vấn trả đủ kết quả, Recall@10 0.978. Post-filter thiếu kết quả
  ở 26% số câu ngay cả khi lấy top-100, vì văn bản đích chỉ chiếm vài chục trên 61 425 điều. (Lọc theo văn bản đúng là "nhãn
  vàng": hệ thật lọc theo quyền, hiệu lực, loại văn bản, không biết trước văn bản đáp án.)
- `count` và các thao tác xoá, upsert đều đúng; khác biệt thật nằm ở thời gian mở lại và ở việc Qdrant/Chroma tự giữ index
  cập nhật, còn FAISS thì bạn tự dựng lại.

## Bẫy thường gặp

- Collection Chroma không khai báo `space`: mặc định L2. Ở đây vector đã chuẩn hoá nên thứ hạng không đổi, nhưng điểm trả về
  là L2 bình phương và mọi ngưỡng tính theo cosine sẽ sai.
- Giữ id `-1` của FAISS: ra uid sai (bản ghi cuối, nếu dùng `list[-1]`) hoặc lỗi.
- Id Qdrant từ số thứ tự lúc nạp: mở lại và upsert lần sau tạo bản trùng.
- SQL ghép chuỗi không escape: tên văn bản có nháy đơn làm truy vấn lỗi; với input người dùng là SQL injection.
- So độ trễ của chế độ nhúng với server, hoặc đo cả lô rồi hứa độ trễ từng request.
