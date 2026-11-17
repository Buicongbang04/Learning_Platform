---
title: "Hiện trường: benchmark llama.cpp trên máy xưởng"
level: intermediate
services: []
files:
  - path: starter/bench.py
    note: Script benchmark của team (chạy trên máy khách), bạn sửa
  - path: tests/test_bench_factory.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit derive 05-gpu-field-factory
  - uv run pytest tracks/fde/modules/05-gpu-field/exercises/intermediate/01-bench-at-factory -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Nhà máy đang chạy quillo 1.0.0 với `llm-small` và hỏi có lên `llm-medium` được không. Máy duy nhất có cấu hình đó là
chính máy production của xưởng, nên benchmark phải chạy **trên máy đang phục vụ người dùng**: số đo phải đúng, và
benchmark không được làm hại thứ đang chạy. Bài này sửa script benchmark của team cho tới khi nó cho số tin được trên máy
xưởng trong mọi ca.

## Đề bài

Máy `factory` (Debian 12, 2 vCPU, 3072 MB RAM, không GPU) đang chạy quillo 1.0.0 bằng compose ở
`/home/fde/quillo-1.0.0` (cổng 18080). Có sẵn image `ghcr.io/ggml-org/llama.cpp:server-b11718` (nạp từ bundle) và hai
model: `llm-small` ở `/home/fde/quillo-1.0.0/models/qwen2.5-0.5b-instruct-q4_k_m.gguf`, `llm-medium` ở
`/home/fde/models/qwen2.5-1.5b-instruct-q4_k_m.gguf`. Tự boot để điều tra: `with fdekit.vm("factory",
base=fdekit.derived("05-gpu-field-factory")) as m:`.

`starter/bench.py` là script của team, chạy tốt trên máy lab. Tuần trước bạn để nó lại cho IT xưởng chạy. Tin nhắn của
anh trực IT:

> Thứ Hai em chạy ca ngày, số đẹp: small ~47 tokens/s, medium ~24. Tối qua em chạy lại lúc ca đêm (giờ đó có job tổng
> hợp dữ liệu sản xuất chạy cùng máy) thì cả hai model chỉ còn khoảng 6 tokens/s, báo cáo ghi không model nào đạt.
> Cùng lúc đó tổ trưởng ca báo quillo trả lời rất chậm, và job tổng hợp chạy lâu gấp mấy lần mọi hôm. Không có lỗi gì,
> không có gì bị tắt, sáng ra mọi thứ lại bình thường. Số nào đúng hả anh? Lần sau em có nên chạy nữa không?

Sửa `starter/bench.py` (Python 3 thư viện chuẩn, chạy trên máy khách bằng user `fde`, không sudo). Cách gọi giữ nguyên:

```bash
python3 bench.py --image ghcr.io/ggml-org/llama.cpp:server-b11718 --out <report.json> \
    llm-small=<gguf> llm-medium=<gguf>
```

Model đi theo thứ tự tham số (từ nhỏ tới lớn). Với **từng** model, theo thứ tự:

1. `need_mb` = 0,8 × kích thước tệp GGUF tính bằng MB (1 MB = 1 048 576 byte), làm tròn lên. `available_mb` =
   `MemAvailable` trong `/proc/meminfo` (MB, làm tròn xuống) đọc **ngay trước** khi xét model đó.
2. Nếu `need_mb > available_mb − 128` thì **không chạy** model đó, `status` = `skipped_memory`.
3. Không thì chạy llama.cpp server trong container từ image trên với đúng cờ `-c 4096 -np 1 -t <số core vật lý>`
   (publish chỉ trên `127.0.0.1`, không đụng cổng 18080), chờ `/health` trả 200, gửi một request khởi động (không tính)
   rồi 3 request `POST /completion` với `n_predict` 64, `ignore_eos` true, `cache_prompt` false, `temperature` 0 và prompt
   `Viết một đoạn ngắn hướng dẫn bảo trì máy CNC cho ca đêm.`;
   `tokens_per_s` = tổng `timings.predicted_n` / tổng `timings.predicted_ms` × 1000. `peak_rss_mb` = `VmHWM` của tiến
   trình server (pid từ `docker inspect -f '{{.State.Pid}}'`, `/proc/<pid>/status`) đổi sang MB, đọc sau 3 request.
   Lỗi khi chạy thì `status` = `failed` kèm `detail`.

Báo cáo JSON (`--out`):

```json
{
  "host": {"physical_cores": 2, "mem_total_mb": 2919, "gpu": null},
  "settings": {"ctx": 4096, "threads": 2, "n_predict": 64, "runs": 3},
  "models": [
    {"name": "llm-small", "file": "...", "need_mb": 375, "available_mb": 2212, "status": "ok",
     "tokens_per_s": 47.1, "peak_rss_mb": 625},
    {"name": "llm-medium", "file": "...", "need_mb": 853, "available_mb": 912, "status": "skipped_memory"}
  ],
  "recommended": "llm-small"
}
```

`host.physical_cores` là số core vật lý (CPU logic cùng `physical_package_id` và `core_id` tính là một), `mem_total_mb`
là `MemTotal` (MB, làm tròn xuống), `gpu` là tên GPU nếu `nvidia-smi --query-gpu=name` chạy được, không thì `null`.
`recommended` là model **cuối cùng** (theo thứ tự tham số) có `status` `ok` và `tokens_per_s` ≥ 10, không có thì `null`.

Test boot snapshot `05-gpu-field-factory` (quillo đang chạy), chép `bench.py` vào `/home/fde/bench/` rồi chạy ba lần,
mỗi lần sau một lần trước (job đã khởi động thì chạy tới hết bài):

1. **Ca ngày**: máy chỉ có quillo.
2. **Ca đêm**: bộ chấm khởi động một tiến trình của xưởng (job tổng hợp) giữ RAM để `MemAvailable` còn khoảng
   `need_mb` của `llm-medium` + 128 + 100 MB.
3. **Ca đêm cuối tháng**: thêm một job nữa, `MemAvailable` còn khoảng `need_mb` của `llm-medium` + 128 − 150 MB.

Mỗi lần chạy `bench.py` ≤ 150 s. Đo trên máy của repo: cả bài ~3 phút.

## Tiêu chí đạt

`test_bench_on_factory`, mỗi lần chạy:

- `bench.py` thoát `0`; báo cáo có đủ khoá, `models` đúng thứ tự tham số; `host` đúng với máy (core vật lý, `MemTotal`
  ±2 MB, `gpu` null).
- Mỗi model: `need_mb` đúng công thức; `status` đúng quy tắc bước 2 theo chính `available_mb` trong báo cáo; model `ok`
  có `tokens_per_s` và `peak_rss_mb` > 0.
- `available_mb` không lớn hơn `MemAvailable` bộ chấm đọc ngay trước lần chạy + 150 MB.
- Ca ngày: cả hai model `ok`. Ca đêm: `llm-small` `ok`. Ca đêm cuối tháng: `llm-small` `ok`, `llm-medium`
  `skipped_memory`. Các job của xưởng vẫn sống.
- Với mỗi model `ok`, ngay sau đó bộ chấm tự đo lại model đó (một container, đúng cờ và request ở trên) trên cùng máy:
  `tokens_per_s` của báo cáo trong khoảng **0,5× – 2×** số đo lại, `peak_rss_mb` trong khoảng **0,75× – 1,33×**.
- `recommended` đúng quy tắc theo các số trong báo cáo.
- Sau mỗi lần chạy không còn container nào ngoài của quillo; sau cả bài, các container quillo không bị khởi động lại hay
  bị kill (trạng thái, `RestartCount`, `StartedAt`, `OOMKilled` không đổi) và `/healthz` trả 200.

## Gợi ý

### Gợi ý 1

Tái hiện trước khi sửa: boot snapshot, tự dựng "ca đêm" bằng một tiến trình giữ RAM (ví dụ Python giữ một `bytearray` đã
ghi từng trang), chạy script của team và quan sát cả máy trong lúc nó chạy (`free -m`, `vmstat 1`, tokens/s của quillo),
không chỉ nhìn báo cáo.

### Gợi ý 2

Đổi từng biến một. Trong cùng một "ca đêm", tự chạy server của một model bằng tay rồi đo như bước 3; so với số của script
team trong cùng điều kiện. Khác nhau thì khác ở đâu?

### Gợi ý 3

Một script chạy trên máy production cần hành xử đúng cả khi bị ngắt giữa chừng (Ctrl-C, mất SSH): không để lại container
nào.
