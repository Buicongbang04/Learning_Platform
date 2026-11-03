# Lời giải: Ray Tune với ASHA

`tune_search.py` cạnh tệp này là lời giải chạy được.

## Ý chính

- **Trainable báo metric mỗi epoch.** ASHA chỉ dừng được trial ở các mốc (rung) 1, 2, 4, 8 vòng nếu trial báo metric ở những mốc đó. Báo
  một lần ở cuối thì mọi trial đều chạy đủ 16 epoch và scheduler không làm được gì (giống FIFO).
- **`metric`/`mode` khai báo một chỗ.** Đặt ở `TuneConfig` để cả scheduler lẫn `get_best_result` dùng chung; khai báo trùng ở scheduler
  thì Tune báo lỗi. Ghi `mode="max"` cho loss là lỗi kinh điển: Tune giữ lại trial tệ nhất và báo nó là tốt nhất.
- **ASHA bất đồng bộ.** Trial tới rung nào thì so với những trial đã tới rung đó trước nó; không top `1/reduction_factor` thì dừng. Vài trial
  đầu tiên chạy khi chưa có đối thủ nên có thể đi xa dù kém (khi thử bài, có lần một trial learning rate nhỏ nhất vẫn chạy đủ 16
  epoch). Đó là cái giá của việc không chờ cả đợt.
- **`scope="last"`.** "Tốt nhất" so loss cuối của mỗi trial. Với `scope="all"` Tune lấy loss tốt nhất từng đạt ở bất kỳ epoch nào, có thể
  là một epoch mà sau đó model tệ đi; bạn không có checkpoint ở epoch đó thì config "tốt nhất" không tái hiện được.
- **`storage_path` rõ ràng.** Mặc định Tune ghi vào `~/ray_results`; trên cụm thật đặt S3/GCS để các node và job sau đọc được, và để
  `Tuner.restore` tiếp một lần tìm kiếm bị ngắt.

## Khi nào ASHA dừng nhầm

Config học chậm lúc đầu nhưng tốt về sau (learning rate nhỏ với warmup dài, model lớn) thua ở rung sớm và bị dừng. Giảm rủi ro bằng
`grace_period` dài hơn (tốn tài nguyên hơn), metric ít nhiễu hơn, hoặc dùng PBT/BOHB. Không gian tìm kiếm cũng quan trọng ngang
scheduler: LR quá nhỏ chiếm nửa khoảng log thì nửa số trial là lãng phí dù có dừng sớm.

## Lên cụm thật

Cùng code chạy trên cụm Ray nhiều node: `tune.with_resources(train_model, {"cpu": 4, "gpu": 1})` cho trial cần GPU, `max_concurrent_trials`
để giới hạn theo ngân sách, `RunConfig(storage_path="s3://...")`. Trial dùng nhiều GPU thì trainable là một `TorchTrainer` (Ray Train),
Tune điều phối nhiều trainer.
