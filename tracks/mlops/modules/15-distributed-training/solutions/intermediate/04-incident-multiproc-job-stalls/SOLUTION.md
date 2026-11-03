# Lời giải: job nhiều tiến trình đứng im ngay từ đầu

`train_job.py` cạnh tệp này là lời giải chạy được.

## Nguyên nhân gốc

`MetricsWriter.write` thoát ngay ở mọi rank khác 0 (`if self.rank != 0 ...: return`), **rồi mới** gọi `mean_over_workers`, hàm chứa
`dist.all_reduce`. All-reduce là một collective: rank gọi nó đứng chờ mọi rank khác gọi collective tương ứng. Ở bước 0:

- Rank 0 vào `all_reduce` của metric và chờ rank 1.
- Rank 1 bỏ qua, ghi trace bước 0, sang bước 1 và vào collective của DDP (đồng bộ bucket/gradient) và chờ rank 0.

Hai rank đứng ở hai collective khác nhau, không bên nào tới được điểm hẹn của bên kia. Gloo chờ trong lời gọi mạng chặn nên CPU 0% và
không có lỗi, tới khi hết timeout mặc định của process group (30 phút với gloo, 10 phút với NCCL). Một tiến trình thì world size 1,
`all_reduce` trả về ngay: lỗi chỉ lộ ra khi có từ hai rank. Đó cũng là lý do `rank0.jsonl` trống (rank 0 kẹt trước khi ghi trace bước
0) còn `rank1.jsonl` có đúng một dòng.

Một câu: một collective nằm trong nhánh chỉ rank 0 đi vào, nên các rank gọi chuỗi collective khác nhau và chờ nhau mãi.

## Sửa

Mọi rank gọi collective, chỉ rank 0 ghi:

```python
def write(self, step, loss):
    if step % LOG_EVERY:
        return
    value = mean_over_workers(loss)
    if self.rank != 0:
        return
    ...
```

Quy tắc chung: điều kiện `if rank == 0` chỉ được bọc **tác dụng phụ** (ghi tệp, log, upload), không bao giờ bọc tính toán có giao tiếp.
Điều kiện theo bước (`step % LOG_EVERY`) thì an toàn vì mọi rank cùng giá trị `step`. Cẩn thận với điều kiện theo dữ liệu (`if len(batch) > 0`,
`if loss.isnan()`): mỗi rank có thể thấy khác nhau.

Sửa sai hay gặp: ghi `loss.item()` của rank 0 thay vì trung bình (job chạy nhưng metric chỉ phản ánh nửa dữ liệu; test bắt), hay cho
mọi rank ghi `metrics.jsonl` (mỗi bước có nhiều dòng chen nhau).

## Ngăn tái diễn

- **Phát hiện**: watchdog theo tiến độ, không theo trạng thái tiến trình. Job ghi heartbeat (bước cuối, thời điểm) và alert khi không
  có bước mới quá N lần thời gian một bước (vd. 5 phút), thay vì chờ timeout 30 phút. `init_process_group(timeout=timedelta(minutes=5))`
  để treo biến thành lỗi sớm; NCCL có `TORCH_NCCL_ASYNC_ERROR_HANDLING` và flight recorder để ghi collective cuối của từng rank.
- **Ngăn chặn**: CI chạy job với `--nproc_per_node=2` trên CPU (gloo) với timeout cứng, đúng như test này; lỗi kiểu này không bao giờ lộ
  ở một tiến trình. `TORCH_DISTRIBUTED_DEBUG=DETAIL` trong CI để kiểm thứ tự collective.
- **Giảm thiệt hại**: scheduler đặt `activeDeadlineSeconds`/timeout cho job và giới hạn retry; launcher dọn sạch worker khi dừng (torchrun
  đặt mỗi worker ở session riêng, giết torchrun bằng `kill -9` để lại worker mồ côi giữ cổng và RAM).

## Đọc thêm triệu chứng

| Triệu chứng | Nghi |
| --- | --- |
| Treo trước bước đầu, chưa rank nào ghi gì | rendezvous: thiếu rank, sai địa chỉ/cổng, firewall, hostname không định tuyến |
| Một rank đi trước đúng một bước rồi treo | collective trong nhánh rank-riêng (bài này) |
| Treo cuối epoch | dữ liệu chia không đều, một rank hết batch trước và không vào collective cuối |
| Lỗi "Connection closed by peer" ở rank khác | một rank chết thật (OOM, exception); xem log của rank đó trước |
