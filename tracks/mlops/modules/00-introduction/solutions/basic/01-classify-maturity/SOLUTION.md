# Lời giải: xếp hạng maturity

| Hệ thống | Google | Microsoft | Blocker | Vì sao |
| --- | --- | --- | --- | --- |
| `quote-pricing` | 0 | 1 | `training_triggered_automatically` | Có CI cho code nên Microsoft mức 1 (DevOps, chưa MLOps); nhưng train bằng notebook chạy tay, deploy bằng copy pickle nên Google vẫn mức 0 |
| `recsys-ranking` | 1 | 2 | `pipeline_cicd` | Training tự chạy, có validation, tracking và registry; deploy model còn thủ công và pipeline được cập nhật bằng `ssh` nên chưa phải mức 2 Google |
| `fraud-scoring` | 2 | 4 | không | CI/CD cho pipeline, deploy qua cổng, monitoring kích hoạt retrain |

Bài học: hai thang đo hỏi hai câu khác nhau. Google chỉ nhìn mức tự động hoá của pipeline ML; Microsoft chia mịn hơn ở phần
deploy và vận hành. Sai lầm hay gặp là gán mức theo công cụ ("có Airflow nên mức 2") thay vì theo việc gì còn do con người
làm tay.
