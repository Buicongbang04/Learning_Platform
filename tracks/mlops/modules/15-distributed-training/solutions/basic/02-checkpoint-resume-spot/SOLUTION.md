# Lời giải: checkpoint và resume khi bị thu hồi spot

`train_resumable.py` cạnh tệp này là lời giải chạy được.

## Ý chính

- **Ghi tạm rồi đổi tên.** `torch.save` vào `.step-XXXXXX.pt.tmp`, `fsync`, rồi `os.replace` sang tên thật. Kill giữa lúc ghi chỉ để lại
  tệp tạm (tên không khớp `step-*.pt`, lần sau bỏ qua); tên thật luôn là tệp đầy đủ. Trên S3/GCS không có rename nguyên tử: upload xong
  rồi mới ghi một "con trỏ" (`latest.json`) hoặc dựa vào việc object chỉ xuất hiện khi upload hoàn tất.
- **Vẫn phải chịu được tệp hỏng.** Đĩa đầy, bản copy cụt, người khác sửa tay: `load_latest` thử từ mới tới cũ, bỏ tệp không nạp được.
  Test cấy một tệp cụt để kiểm đúng nhánh này.
- **Optimizer state là một nửa của trạng thái.** Adam giữ hai moment cho mỗi tham số. Nạp model mà không nạp optimizer thì bước đầu sau
  resume dùng moment bằng 0: bước nhảy khác hẳn, loss nhảy, kết quả cuối lệch so với chạy liền. Test so `final.pt` với sai số 1e-6 nên bắt
  được ngay.
- **Mọi rank nạp cùng một checkpoint.** DDP broadcast tham số từ rank 0 khi bọc, nhưng **không** đồng bộ optimizer state; rank nào không
  nạp optimizer sẽ lệch dần.
- **Resume xác định vì dữ liệu là hàm của số bước.** `batch_indices(step, ...)` không phụ thuộc lịch sử, nên chạy lại từ bước 40 thấy đúng
  các batch 40, 41... như lần chạy liền. Nếu thứ tự phụ thuộc trạng thái thì phải lưu thêm: `sampler` epoch và vị trí trong epoch, trạng
  thái RNG (`torch.get_rng_state()`, của numpy, `random`, CUDA) cho dropout và augmentation, LR scheduler, GradScaler.
- **Idempotent.** Chạy lại khi đã đủ bước: vòng lặp rỗng, `final.pt` ghi lại từ cùng trạng thái. Scheduler (Kubernetes Job, Argo, Ray)
  cứ retry mà không sợ huấn luyện thêm hay ghi đè kết quả khác.

## Lỗi hay gặp

- Mọi rank cùng ghi một tệp: tệp cuối là của rank ghi sau cùng, có lúc hai rank ghi chen nhau thành tệp hỏng.
- Lưu `ddp.state_dict()` (có tiền tố `module.`) rồi nạp vào model trần: `load_state_dict` báo thiếu khoá, hoặc tệ hơn với `strict=False`
  thì nạp "thành công" mà không nạp gì.
- Đặt tên checkpoint theo thời gian thay vì theo bước: không biết resume từ đâu, sắp xếp sai khi đồng hồ lệch.
- Chỉ checkpoint mỗi epoch với epoch dài vài giờ: mỗi lần bị thu hồi mất trung bình nửa epoch. Bài Basic 03 tính khoảng tối ưu.
