---
title: Checkpoint và resume khi bị thu hồi spot
level: basic
services: []
files:
  - path: starter/train_resumable.py
    note: 2 hàm TODO (save_checkpoint, load_latest); vòng huấn luyện có sẵn
  - path: tests/test_resume.py
    note: Không sửa
run:
  - uv run python -m torch.distributed.run --nproc_per_node=2 --rdzv-backend=c10d --rdzv-endpoint=127.0.0.1:0 --local-addr=127.0.0.1 tracks/mlops/modules/15-distributed-training/exercises/basic/02-checkpoint-resume-spot/starter/train_resumable.py --out /tmp/mlops-15/resume --step-delay 0.05
  - uv run pytest tracks/mlops/modules/15-distributed-training/exercises/basic/02-checkpoint-resume-spot -q
---

## Mục tiêu

Làm một job DDP hai tiến trình chịu được việc bị kill bất kỳ lúc nào (máy spot bị thu hồi): checkpoint định kỳ ghi nguyên tử, chạy lại
thì tiếp từ checkpoint mới nhất còn đọc được, kết quả cuối giống hệt chạy liền một mạch, và chạy lại job đã xong thì không làm gì thêm.

## Đề bài

`starter/train_resumable.py` có sẵn dữ liệu, model, optimizer Adam và vòng huấn luyện. Thứ tự batch là hàm của số bước
(`batch_indices(step, rank, world)`), nên không cần lưu trạng thái sampler. Vòng lặp gọi `load_latest` trước khi bọc DDP và gọi
`save_checkpoint(ckpt_dir, step + 1, ...)` sau mỗi `--every` bước. Điền 2 hàm:

**`save_checkpoint(ckpt_dir, step, model, optimizer, rank)`**, mọi rank đều gọi:

- Chỉ rank 0 ghi, vào `checkpoint_path(ckpt_dir, step)` (tên `step-<6 chữ số>.pt`), một dict đúng ba khoá:
  `{"step": step, "model": model.state_dict(), "optimizer": optimizer.state_dict()}` (`step` là số bước đã xong).
- Ghi **nguyên tử**: bị kill giữa lúc ghi thì không bao giờ để lại tệp `step-*.pt` dở dang. Tệp tạm (nếu có) không được khớp mẫu
  `step-*.pt`.
- Rank khác chờ rank 0 ghi xong rồi mới đi tiếp.

**`load_latest(ckpt_dir, model, optimizer) -> int`**:

- Thử các tệp `step-*.pt` từ bước lớn nhất xuống; tệp nào không nạp được (hỏng, cụt) thì bỏ qua, in một dòng cảnh báo ra stderr, thử
  tệp kế tiếp.
- Nạp vào cả model và optimizer, trả số bước đã xong ghi trong checkpoint. Chưa có thư mục hay không có tệp đọc được: trả 0.

Luật mà test kiểm (`--steps 120 --every 10 --step-delay 0.05`, timeout 240 giây mỗi lần chạy):

1. Chạy liền một mạch: xong, có `final.pt`, checkpoint ở bước 10, 20, ..., 120.
2. Chạy lần hai từ đầu ở thư mục khác, chờ tới khi có checkpoint bước 40 trở lên thì **SIGKILL cả job** (torchrun và mọi worker, như
   máy bị thu hồi); job phải còn đang chạy lúc bị kill và không còn tiến trình nào sau đó.
3. Test cấy một tệp hỏng (nửa đầu của checkpoint mới nhất) với tên bước kế tiếp, rồi chạy lại: log ghi `{"event": "start", "from_step": K}`
   với `K` là bước của checkpoint mới nhất **còn đọc được**.
4. `final.pt` của lần chạy lại bằng `final.pt` của lần chạy liền (sai số tuyệt đối 1e-6), loss bước cuối cũng vậy.
5. Chạy lại lần nữa khi đã xong: `from_step` là 120, không có bước huấn luyện nào được ghi thêm, `final.pt` không đổi.
6. Sau cùng, thư mục có đủ `step-*.pt` của bước 10, 20, ..., 120, mọi tệp nạp được, có đúng ba khoá trên, khoá của `model` là khoá của model gốc (không có tiền tố `module.`).

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/15-distributed-training/exercises/basic/02-checkpoint-resume-spot -q` pass.
- Bạn giải thích được vì sao bỏ optimizer state khỏi checkpoint làm kết quả lệch dù model nạp đúng.
- Bạn nói được job này cần thêm gì để resume đúng nếu thứ tự batch phụ thuộc trạng thái (sampler xáo ngẫu nhiên, dropout).

## Gợi ý

### Gợi ý 1

Ghi vào một tệp tạm cùng thư mục (vd. `.step-000040.pt.tmp`), rồi `os.replace(tmp, final)`: trên cùng filesystem, đổi tên là nguyên tử.

### Gợi ý 2

`dist.barrier()` sau phần ghi của rank 0 giữ các rank đi cùng nhau. `torch.load(path, weights_only=True)` nạp được dict chứa tensor và số,
và báo lỗi (nhiều loại khác nhau) khi tệp bị cụt.

### Gợi ý 3

Tự thử: chạy lệnh trong `run` ở trên, `Ctrl-C` khi đã thấy vài checkpoint trong `/tmp/mlops-15/resume/ckpt`, rồi chạy lại đúng lệnh đó.
