# Lời giải: hiện trường "benchmark trên máy xưởng"

Lời giải ở `bench.py` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/05-gpu-field/exercises/intermediate/01-bench-at-factory -q
```

Đo 2026-11-11 trên máy của repo: 182 s và 178 s (hai lần; boot ~10 s, ba ca, mỗi ca đo lại các model `ok`).

## Chuyện gì đã xảy ra ở ca đêm (đo thật trên `factory`)

Không có OOM-kill, và đó chính là cái bẫy. Cùng snapshot quillo, cờ `-c 4096 -np 1 -t 2`, tokens/s của 3 lần sinh:

| `MemAvailable` trước khi đo | Một model mỗi lúc | Script team: nạp cả hai rồi mới đo |
| --- | --- | --- |
| ~2 090–2 200 MB (ca ngày) | small 43–51, medium 20–25 | small 43–47, medium 21–25 (không chậm) |
| ~1 670–2 000 MB | small 42–53, medium 21–25 | không chậm |
| ~1 070–1 080 MB (job giữ ~1,1 GB; đo hai lần) | small 41–52 (còn ~900 MB trống), medium 21–25 (còn ~330 MB) | **small 5,9–6,3, medium 5,1–5,8**; còn ~170 MB trống |

llama.cpp `mmap` tệp GGUF: trọng số là page cache, được tính vào `MemAvailable` và kernel được bỏ chúng khỏi RAM khi
thiếu rồi đọc lại từ đĩa ở token sau. Nạp model chiếm ít `MemAvailable` hơn kích thước tệp nhiều (đo: small ~150–180 MB,
medium ~740 MB với `-c 4096`), nên ở ca ngày nạp cả hai cùng lúc vô hại. Ở ca đêm, mỗi model riêng vẫn vừa (medium còn dư
~330 MB), nhưng khi script team nạp **cả hai** rồi mới đo, RAM trống xuống ~170 MB: không ai bị kill, nhưng trọng số của
cả hai model, code của Postgres, quillo và job tổng hợp liên tục bị đẩy ra rồi đọc lại. Tokens/s rơi 7–9 lần, quillo chậm,
log sạch, sáng ra hết tải thì "tự khỏi". Số của ca đêm không phải tốc độ của model mà là tốc độ của một máy đang thrash;
khuyến nghị dựa trên nó là sai.

Mặc định của llama.cpp làm chuyện nặng hơn nếu quên cờ: không đặt `-c` thì context theo model (32 768) cho 4 slot,
`llm-medium` chiếm ~2,4 GB thay vì ~1,7 GB (đo bằng `memory.peak`). Bài README module chỉ nói chung về `mmap`; các con
số trên là của riêng máy này.

## Cách sửa

1. **Mỗi lúc một model**: khởi động, đo, xoá container rồi mới sang model sau. Chỉ một server chiếm RAM tại một thời
   điểm. Đây là thứ test ca đêm bắt: bộ chấm đo lại từng model một mình ngay sau đó, số của bạn phải trong 0,5×–2×.
2. **Đọc `MemAvailable` ngay trước mỗi model** và không chạy khi ước tính không vừa (chừa 128 MB). Hệ số 0,8 × tệp làm
   tròn lên từ phần `MemAvailable` đo được mà một server chiếm (0,35× với 0,5B, ~0,7× với 1,5B). Ca đêm cuối tháng (còn
   ~830 MB) thì medium không được chạy: một mình nó cũng làm máy thrash. Model bị bỏ qua được ghi rõ `skipped_memory` kèm
   `need_mb` và `available_mb`: đó là một kết quả, không phải lỗi.
3. **Dọn khi bị ngắt**: `try/finally` bao cả bước `docker run`, chặn tạm SIGINT/SIGTERM/SIGHUP trong lúc `docker rm -f`,
   SIGTERM/SIGHUP (mất SSH) chuyển thành `KeyboardInterrupt` để `finally` chạy. Ngắt ở bất kỳ bước nào cũng không để lại
   container.
4. **Không đi qua proxy**: máy xưởng có `http_proxy` trong `/etc/environment`; client HTTP tới `127.0.0.1` dùng
   `ProxyHandler({})` để không phụ thuộc `no_proxy`.
5. Đo đúng như README: request khởi động, `ignore_eos`, `cache_prompt` false, `timings.predicted_*`, `VmHWM` thay vì
   `memory.peak` của cgroup (page cache được tính cho cgroup đọc tệp đầu tiên, nên cùng model đo hai lần ra 1 658 MB rồi
   1 092 MB).

Kiểm chứng (2026-11-11, mỗi phương án hai lần): script team nguyên trạng (nạp cả hai, không kiểm RAM) trượt ở ca đêm
(`llm-small` báo 6,3 và 6,4 tokens/s, bộ chấm đo lại 48,7 và 51,6); script team thêm đúng quy tắc bỏ qua nhưng vẫn nạp cả
hai trước trượt y như vậy (6,3/6,4 so với 54,2/49,0); lời giải tham chiếu đạt cả hai lần.

Trả lời anh trực IT: số ca ngày đúng (khoảng ±30% tuỳ tải), số ca đêm sai vì chính script đã làm máy thiếu RAM; script mới
đo từng model một, tự bỏ qua model mà máy không đủ chỗ và không làm chậm quillo. Với khách: `llm-medium` chạy được ở ca
ngày và ca đêm thường (~20–25 tokens/s), nhưng những đêm job nặng hơn thì máy không đủ RAM cho cả quillo, job và medium;
lên medium lâu dài cần thêm RAM (xem bài advanced 02) hoặc dời job.

## Các cách khác

Đạt test và đúng với khách này:

- Ước tính `need_mb` chặt hơn (đọc kiến trúc từ metadata GGUF, công thức bài basic 02) để tự quyết định, miễn là trường
  `need_mb` trong báo cáo vẫn theo đúng công thức README để so được giữa các lần.

Qua test nhưng sai với khách này:

- Thêm `--mlock` hoặc `--no-mmap` "cho số ổn định": trên máy chật RAM nó đổi thrash thành OOM-kill, và OOM killer có thể
  chọn Postgres của quillo hay job của xưởng thay vì server benchmark.
- Dừng hay hạ tài nguyên container của quillo trong lúc đo để "có chỗ": đụng vào production của khách mà không ai cho
  phép, kể cả khi trạng thái container sau đó trông như cũ.

Không đạt: script team nguyên trạng hoặc chỉ thêm quy tắc bỏ qua (nạp cả hai, ca đêm ra số sai), đo model khi không đủ
RAM (ca đêm cuối tháng), bỏ qua model mà không ghi lý do, để lại container.
