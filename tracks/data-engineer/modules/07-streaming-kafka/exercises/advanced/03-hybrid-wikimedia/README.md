---
title: Hybrid ingestion trên Wikimedia EventStreams - stream, batch và đối soát
level: advanced
services: []
files:
  - path: starter/hybrid_wikimedia.ipynb
    note: 9 hàm TODO + 3 biểu đồ; cell explore ghi 5 phút stream thật
  - path: tests/test_hybrid_wikimedia.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/advanced/03-hybrid-wikimedia -q
---

## Mục tiêu

Dựng một pipeline **hybrid** thu nhỏ trên một nguồn stream thật: ghi luồng sửa đổi của mọi wiki
Wikimedia (Server-Sent Events, khoảng 30–50 event mỗi giây) vào lớp raw, tính "số sửa đổi mỗi phút
theo wiki" theo hai cách (stream một lượt có watermark và dedup TTL; batch đọc hết rồi group by), rồi
**đối soát** hai kết quả theo khoá và giải thích từng chỗ lệch. Từ số đo trên chính dữ liệu bạn ghi, chọn
`allowed_lateness` và lập luận Lambda hay Kappa.

## Đề bài

Nguồn: `https://stream.wikimedia.org/v2/stream/recentchange` (công khai, không cần key; gửi
`User-Agent` mô tả rõ ai đang gọi theo chính sách của Wikimedia). Không có thư viện SSE: bạn tự đọc
giao thức bằng `requests` với `stream=True`.

Mở `starter/hybrid_wikimedia.ipynb` (nút **Mở trong VS Code**), sửa email trong `USER_AGENT`, rồi làm lần lượt:

1. `iter_sse(lines)` và `record(seconds, out_path, ...)`: đọc SSE, ghi mỗi event một dòng
   `{"received_at", "event"}` vào `data/raw/wikimedia-recentchange/<thời điểm UTC>.jsonl`; mất kết nối thì nối
   lại với `Last-Event-ID`; ghi qua tệp `.part`. Cell explore ghi 5 phút ở lần chạy đầu.
2. `parse_event(line)`: dict phẳng (khoá dedup `meta.id`, event time `timestamp`, ingestion time
   `received_at`...); dòng hỏng và canary event trả `None`.
3. **Phần stream** `stream_counts(events, window, allowed_lateness, dedup, dedup_ttl)`: một lượt theo thứ
   tự đến, tumbling window event time, watermark, dedup có TTL, trả số đếm và `stats`.
4. **Phần batch** `build_clean(lines)` + `batch_counts(df, window)`: dedup toàn bộ, ép kiểu, đếm cùng định nghĩa.
5. `reconcile(stream, batch)`: outer join theo `(window_start, wiki)`, `diff = batch - stream`.
6. `insights(df, stats)`: sửa đổi mỗi phút, tỉ lệ bot, wiki sôi động nhất, độ trễ p50/p95/max...
7. Ít nhất 3 biểu đồ trong cell `explore` (sửa đổi mỗi phút bot vs người, top wiki, độ trễ và tỉ lệ late theo `allowed_lateness`).
8. `write_clean(df, out_dir)`: ghi đè `data/clean/wikimedia-recentchange/recentchange.parquet`.
9. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook. Câu hỏi có cả lựa chọn Lambda/Kappa.

Lý thuyết nền: README module 07, mục 6 (watermark, dedup, và các phần batch/stream/hybrid, Lambda vs
Kappa, đối soát).

## Tiêu chí đạt

- Test trên fixture nhỏ (luôn chạy, không cần mạng) pass: SSE có comment/data nhiều dòng/event dở;
  `record` nối lại đúng `Last-Event-ID` (session giả); stream khớp batch sau dedup; event trễ và bản
  trùng hiện đúng window trong đối soát; TTL ngắn làm tổng khớp mà window sai.
- Trên tệp bạn tự ghi (test tự skip nếu chưa có): dữ liệu sạch, số đếm batch và insight khớp với tham
  chiếu mà test tự tính lại bằng code độc lập; stream với lateness vô hạn khớp batch tuyệt đối, với
  lateness 0 thì `tổng diff == late`. Ghi ít nhất 2 phút.
- `write_clean` gọi hai lần vẫn đúng số dòng.
- Notebook có ít nhất 3 cell `explore` vẽ biểu đồ.

## Gợi ý

### Gợi ý 1

`resp.iter_lines(decode_unicode=True)` trả từng dòng đã bỏ `\n`. Một biến `data: list[str]` gom các dòng
`data:`, gặp dòng trống thì `yield` rồi xoá. Kết nối cần `timeout=(connect, read)`: không có read timeout
thì khi mạng đứt im lặng, `record` treo mãi. Thử `record(5, tmp)` trước khi ghi 5 phút.

### Gợi ý 2

Stream: hai dict là đủ, `counts[(start, wiki)]` và `seen[event_id] = event_time`. Watermark là
`max_event_time - allowed_lateness`, tính **trước** khi cập nhật `max_event_time` bằng event hiện tại.
Batch: `df["event_time"].dt.floor("60s")` rồi `groupby(["window_start", "wiki"]).size()`. Đối soát:
`merge(how="outer")`, `fillna(0)`, ép về số nguyên.
