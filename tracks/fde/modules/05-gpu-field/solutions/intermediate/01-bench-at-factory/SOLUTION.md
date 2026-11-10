# Lời giải: hiện trường "benchmark trên máy xưởng"

Lời giải ở `bench.py` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/05-gpu-field/exercises/intermediate/01-bench-at-factory -q
```

Đo 2026-11-11 trên máy của repo: 114 s (boot ~10 s, ca ngày ~35 s, đo lại ~25 s, ca đêm ~10 s).

## Chuyện gì đã xảy ra ở ca đêm (đo thật trên `factory`)

Không có OOM-kill, và đó chính là cái bẫy. Số liệu, cùng snapshot quillo, `-c 4096 -np 1 -t 2`:

| Tình huống | `MemAvailable` sau khi nạp model | small tokens/s | medium tokens/s |
| --- | --- | --- | --- |
| Mỗi lúc một model, chỉ có quillo | ~2,1 GB (small), ~1,45 GB (medium) | 35–50 | 19–25 |
| Script team (nạp cả hai rồi mới đo), chỉ có quillo | ~1,3 GB | 42–47 | 18–23 |
| Script team, job ca đêm giữ 1,2 GB | **144 MB** | **6,4–6,6** | **5,3–5,6** |

llama.cpp `mmap` tệp GGUF: trọng số là page cache, kernel được bỏ chúng khỏi RAM khi thiếu rồi đọc lại từ đĩa ở token sau.
Khi script team nạp **cả hai** server trước rồi mới đo (thiết kế hợp lý trên máy lab 32 GB: chờ một lần cho cả hai), cộng
với job ca đêm, RAM trống còn ~150 MB: không ai bị kill (không có bộ nhớ ẩn danh nào vượt RAM), nhưng trọng số của cả hai
model, code của Postgres, của quillo và của job tổng hợp liên tục bị đẩy ra rồi đọc lại. Tokens/s rơi 4–8 lần, quillo chậm,
job chậm, log sạch. Sáng ra hết tải thì "tự khỏi". Số của ca đêm không phải "tốc độ của model", mà là tốc độ của một máy
đang thrash; khuyến nghị dựa trên nó là sai.

Mặc định của llama.cpp làm chuyện nặng hơn nếu quên cờ: không đặt `-c` thì context theo model (32 768) cho 4 slot,
`llm-medium` chiếm ~2,4 GB thay vì ~1,7 GB (đo bằng `memory.peak`).

## Cách sửa

1. **Mỗi lúc một model**, xoá container trước khi sang model sau: chỉ một server chiếm RAM tại một thời điểm.
2. **Đọc `MemAvailable` ngay trước mỗi model** và không chạy khi ước tính không vừa (để lại 128 MB cho máy). Hệ số 1,7 ×
   tệp lấy từ đo thật (RSS đỉnh / tệp: 1,33 với 0,5B, 1,55–1,65 với 1,5B ở `-c 4096`), làm tròn lên cho an toàn. Model bị
   bỏ qua được ghi rõ `skipped_memory` kèm `need_mb` và `available_mb`: đó là một kết quả, không phải lỗi.
3. **Dọn khi bị ngắt**: `try/finally` bao cả bước `docker run`, chặn tạm SIGINT/SIGTERM/SIGHUP trong lúc `docker rm -f`,
   SIGTERM/SIGHUP (mất SSH) chuyển thành `KeyboardInterrupt` để `finally` chạy. Ngắt ở bất kỳ bước nào cũng không để lại
   container.
4. **Không đi qua proxy**: máy xưởng có `http_proxy` trong `/etc/environment`; client HTTP tới `127.0.0.1` dùng
   `ProxyHandler({})` để không phụ thuộc `no_proxy`.
5. Đo đúng như README: request khởi động, `ignore_eos`, `cache_prompt` false, `timings.predicted_*`, `VmHWM` thay vì
   `memory.peak` của cgroup (page cache được tính cho cgroup đọc tệp đầu tiên, nên cùng model đo hai lần ra 1 658 MB rồi
   1 092 MB).

Trả lời anh trực IT: số ca ngày đúng (khoảng ±30% tuỳ tải), số ca đêm sai vì chính script đã làm máy thiếu RAM; script mới
tự bỏ qua `llm-medium` khi máy không đủ chỗ và không làm chậm quillo. Với khách: `llm-medium` chạy được ở ca ngày
(~20–25 tokens/s, ~1,7 GB) nhưng ở ca đêm máy không đủ RAM cho cả quillo, job tổng hợp và medium; lên medium cần thêm RAM
(xem bài advanced 02) hoặc chấp nhận dời job.

## Các cách khác

Đạt test và đúng với khách này:

- Ước tính `need_mb` chặt hơn từ công thức bài basic 02 (đọc kiến trúc từ metadata GGUF) thay vì hệ số; miễn là vẫn ghi
  `need_mb` theo đúng công thức README để báo cáo so được giữa các lần.
- Chạy server bằng binary `llama-server` trích từ image thay vì container: không cần, image đã có sẵn.

Qua test nhưng sai với khách này:

- Thêm `--mlock` hoặc `--no-mmap` "cho số ổn định": ở ca ngày đạt, nhưng trên máy chật RAM nó đổi thrash thành OOM-kill,
  và OOM killer có thể chọn Postgres của quillo hay job của xưởng thay vì server benchmark.
- Tự `docker update --memory` cho container của quillo hoặc dừng quillo trong lúc đo để "có chỗ": test vẫn thấy trạng thái
  quillo không đổi nếu bạn khéo, nhưng đó là đụng vào production của khách mà không ai cho phép.

- Giữ thiết kế "nạp mọi model được phép rồi mới đo" và chỉ đọc RAM một lần lúc đầu: ở mức RAM của test ca đêm medium bị
  bỏ qua nên không lộ, nhưng mỗi model đều được so với cùng một con số RAM trống trong khi chúng cùng nằm trong RAM; với ba
  model hay một ca đêm nặng hơn thì tổng vượt RAM và máy lại thrash.

Không đạt: script team nguyên trạng (không có `need_mb`/`available_mb`, ca đêm vẫn đo medium), bỏ qua model mà không ghi
lý do, để lại container khi lỗi.
