---
title: "Sự cố: job nhiều tiến trình đứng im ngay từ đầu"
level: intermediate
services: []
files:
  - path: starter/train_job.py
    note: Job đang chạy ở production, tìm và sửa
  - path: tests/fixtures/train_job.original.py
    note: Bản gốc, test hồi quy dùng
  - path: tests/test_job.py
    note: Không sửa
run:
  - uv run python -m torch.distributed.run --nproc_per_node=2 --rdzv-backend=c10d --rdzv-endpoint=127.0.0.1:0 --local-addr=127.0.0.1 tracks/mlops/modules/15-distributed-training/exercises/intermediate/04-incident-multiproc-job-stalls/starter/train_job.py --out /tmp/mlops-15/job
  - uv run pytest tracks/mlops/modules/15-distributed-training/exercises/intermediate/04-incident-multiproc-job-stalls -q
---

## Mục tiêu

Chẩn đoán một job huấn luyện nhiều tiến trình đứng im không báo lỗi, sửa nó, và rút ra một thay đổi để loại sự cố cùng loại không lặp
lại.

## Đề bài

Thứ Năm, 09:40. Đội ETA chuyển job huấn luyện hằng đêm từ một tiến trình sang `torchrun --nproc_per_node=2` để chuẩn bị lên nhiều GPU.
Từ đó:

- Job chạy một tiến trình (`--nproc_per_node=1`) vẫn xong trong vài giây, metric đẹp như cũ. Review code không thấy gì lạ.
- Chạy hai tiến trình thì job **đứng im**: không lỗi, không traceback, không thoát. `top` cho thấy cả hai worker gần như 0% CPU.
- Trong thư mục output, `rank0.jsonl` trống; `rank1.jsonl` có đúng một dòng (bước 0) rồi dừng. `metrics.jsonl` không có dòng nào.
- Đêm qua job đứng như vậy 30 phút thì tự chết với một lỗi timeout dài; scheduler retry và nó lại đứng thêm 30 phút. Không ai được
  báo vì job "đang chạy".
- `Ctrl-C` torchrun thì nó đợi một lúc lâu mới thoát, và đôi khi `ps` vẫn thấy worker còn sống sau đó.

`starter/train_job.py` là job đang chạy. Sửa nó để chạy được với một hay nhiều tiến trình. Giữ nguyên tham số dòng lệnh, hằng số,
model, dữ liệu và các tệp output. Luật mà test kiểm:

- Test hồi quy chứng minh bản gốc (`tests/fixtures/train_job.original.py`) xong khi chạy một tiến trình, và với hai tiến trình thì vẫn
  chưa xong sau 30 giây; mỗi rank ghi được nhiều nhất một bước; sau khi test diệt job không còn tiến trình nào sống.
- Bản của bạn, hai tiến trình, 40 bước, xong trong 90 giây: có `model.pt`, `rank0.jsonl` và `rank1.jsonl` đủ bước 0-39.
- `metrics.jsonl` có đúng một dòng cho mỗi bước 0, 10, 20, 30 (theo `LOG_EVERY`), và `loss` của mỗi dòng là **trung bình loss của mọi
  worker** ở bước đó (so với `rank0.jsonl`, `rank1.jsonl`, sai số tương đối 1e-5).
- Một tiến trình, 20 bước: vẫn xong, `metrics.jsonl` có bước 0 và 10 bằng loss của rank 0.

Chạy test trên starter mất khoảng 2 phút: test phải chờ hết timeout để chứng minh job đứng im. Mọi lần chạy đều bị diệt sạch khi hết
giờ, kể cả worker đang treo.

Ghi lại một câu nguyên nhân gốc và một thay đổi (code, review, hay vận hành) để sự cố cùng loại không lặp lại; đối chiếu với
`SOLUTION.md` sau khi xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/15-distributed-training/exercises/intermediate/04-incident-multiproc-job-stalls -q` pass.
- Bạn giải thích được vì sao job không báo lỗi gì mà chỉ đứng im, và vì sao một tiến trình thì chạy được.
- Bạn nêu được cách phát hiện job kiểu này trong vài phút thay vì 30 phút, mà không cần ai nhìn `top`.

## Gợi ý

### Gợi ý 1

Mỗi rank đang đứng ở dòng nào? Chạy lệnh trong `run`, rồi ở terminal khác `uv run --with py-spy py-spy dump --pid <pid>` cho từng worker
(lấy pid bằng `pgrep -f train_job.py`; Ubuntu mặc định chặn ptrace tiến trình không phải con, khi đó py-spy cần `sudo`), hoặc thêm
`print(rank, ..., flush=True)` quanh từng bước. Xong nhớ diệt worker còn sót: `pkill -f train_job.py`.

### Gợi ý 2

So danh sách thao tác giao tiếp giữa các tiến trình mà rank 0 và rank 1 thực hiện ở bước 0 và bước 1, theo đúng thứ tự. `TORCH_DISTRIBUTED_DEBUG=DETAIL` giúp được.
