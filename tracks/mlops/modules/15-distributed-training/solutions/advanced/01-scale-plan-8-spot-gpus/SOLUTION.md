# Hướng làm và rubric: kế hoạch scale lên 8 GPU spot

Không có một kế hoạch đúng duy nhất. Rubric chấm việc mỗi quyết định có số đứng sau, và việc kế hoạch biết dừng ở đâu. Các con số dưới
đây là một lời giải hợp lý dùng bảng giá minh hoạ của bài Basic 03.

## Hướng làm mẫu

**1. Mục tiêu.** Mỗi lần huấn luyện xong dưới 12 giờ đồng hồ (để chạy đêm, hai lần mỗi tuần còn dư), dưới 150 USD mỗi lần, và chất lượng
validation (MAE phút giao hàng) không kém bản 1 GPU quá 1% trên cùng tập kiểm, so trên 3 seed.

**2. Trước khi thêm GPU.** GPU utilization 55% nghĩa là gần nửa thời gian GPU chờ dữ liệu: nhân 8 GPU lên thì nhân 8 lần chờ. Việc đầu
tiên: đo tỉ lệ chờ như bài Intermediate 03; gộp 2 triệu tệp nhỏ trên S3 thành shard (WebDataset hoặc Parquet, vài trăm MB mỗi shard),
tăng `num_workers` trong giới hạn core (8 GPU x 6 worker = 48 core, kiểm node có đủ), `persistent_workers`, `pin_memory`. Mục tiêu đưa
utilization lên 85-90% **trên 1 GPU**: khoảng 2 200 mẫu/giây, job 1 GPU còn khoảng 38 giờ. Việc này rẻ hơn mọi GPU thêm vào.

**3. Song song.** 350 triệu tham số, đỉnh 41 GB trên GPU 80 GB: vừa một GPU, nên **DDP** (FSDP chỉ thêm giao tiếp). 8 GPU trong một
node NVLink. Batch mỗi GPU giữ 64, batch toàn cục 512; learning rate tăng tuyến tính theo batch (x8) kèm warmup vài trăm bước, hoặc
giữ batch toàn cục 64 bằng batch 8 mỗi GPU nếu chất lượng lệch. Kiểm chất lượng là một bước của kế hoạch, không phải giả định.

**4. Đo hiệu suất scale.** Chạy 30 phút ở 1, 2, 4, 8 GPU, ghi thông lượng: $$e_N = T_N / (N \cdot T_1)$$. Dừng ở mức thấp hơn nếu $$e < 0.7$$
(mỗi GPU thêm vào trả tiền cho hơn 30% thời gian ngồi chờ). Trong một node NVLink, DDP model này thường đạt $$e \approx 0.9$$.

**5. Checkpoint.** Lưu model, optimizer AdamW (2 moment), LR scheduler, GradScaler (nếu fp16), bước, epoch và vị trí sampler, trạng thái
RNG: khoảng 1.4 GB model + 2.8 GB optimizer. Ghi nguyên tử lên S3 (upload xong mới ghi `latest.json`), giữ 3 bản gần nhất. Thời gian ghi
khoảng 1 phút ($$\delta \approx 0.017$$ giờ); Young với $$\lambda = 0.03$$: $$\tau = \sqrt{2 \cdot 0.017 / 0.03} \approx 1$$ giờ. Job chỉ dài
khoảng 5 giờ nên checkpoint mỗi 30 phút (rẻ). Bắt `SIGTERM` (thông báo thu hồi) để ghi thêm một checkpoint nếu kịp. Kiểm resume bằng
đúng cách của bài Basic 02: kill giữa chừng, chạy lại, so loss với chạy liền.

**6. Chi phí và thời gian** (hàm `estimate` của Basic 03, $$e = 0.9$$, khởi động lại 15 phút):

| Phương án | Giờ đồng hồ | Giờ GPU | Chi phí |
| --- | --- | --- | --- |
| Hiện tại: 1 A100 on-demand, 60 giờ | 60 | 60 | 246 USD |
| Sau sửa dữ liệu, 1 A100 on-demand, 38 giờ | 38 | 38 | 156 USD |
| 8 A100 on-demand | 5.3 | 42.2 | 173 USD |
| 8 A100 spot, checkpoint 30 phút | 5.3 + 0.08 | 42.9 | 69 USD |

Thêm GPU không làm rẻ hơn (42 giờ GPU so với 38); spot mới làm rẻ hơn. Mỗi tháng dữ liệu tăng 8% thì chi phí tăng theo, kế hoạch nói
khi nào xem lại (vd. khi job 8 GPU vượt 8 giờ).

**7. Rủi ro và rollback.** Không thuê được spot (capacity) quá 2 giờ thì chạy on-demand (ngân sách cho phép 173 USD); chất lượng lệch quá
1% thì quay về 1 GPU và điều tra batch/LR; resume lệch kết quả thì dừng dùng spot tới khi sửa.

**8. Vận hành.** Heartbeat mỗi bước ghi metric; alert khi không có bước mới quá 10 phút (treo, bài Intermediate 04) hay thông lượng dưới
70% mức đo; job có timeout cứng và giới hạn retry; chi phí gắn nhãn theo job trên billing của cloud; người trực là người trực của đội ML
platform, runbook gồm "kill và resume".

## Rubric (100 điểm)

| Mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Mục tiêu có số | 10 | Có thời gian, ngân sách, tiêu chí chất lượng đo được |
| Sửa trước khi scale | 15 | Đọc được 55% utilization là nghẽn dữ liệu; có biện pháp cụ thể và số mục tiêu trên 1 GPU |
| Chiến lược song song | 15 | Chọn DDP với lý do bộ nhớ; nói cách đổi batch/LR và cách kiểm chất lượng |
| Đo hiệu suất scale | 10 | Đo từng mức, có ngưỡng dừng |
| Checkpoint/resume | 20 | Lưu đủ trạng thái (optimizer, scheduler, sampler, RNG); ghi nguyên tử; khoảng checkpoint có tính; có cách kiểm resume |
| Chi phí | 15 | Bảng on-demand và spot có giả định ghi rõ; nhận ra thêm GPU không làm rẻ hơn |
| Rủi ro, rollback, vận hành | 15 | Có kế hoạch khi không thuê được spot; alert theo tiến độ chứ không theo trạng thái tiến trình |

Mức đạt 70. Trừ điểm: scale trước khi sửa nghẽn dữ liệu (-15); chọn FSDP/DeepSpeed cho model vừa một GPU mà không có lý do (-10);
checkpoint chỉ có model (-10); tính tỉ lệ thu hồi của node 8 GPU bằng 8 lần tỉ lệ một node (-5).
