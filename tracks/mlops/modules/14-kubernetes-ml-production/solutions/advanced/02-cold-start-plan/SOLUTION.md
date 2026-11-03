# Lời giải: kế hoạch giảm cold start

## Phân rã

| Đường | p50 | p95 | Chi phối |
| --- | --- | --- | --- |
| Node có sẵn, image có sẵn | 15 + 1 + 12 + 8 = 36 s | 29 + 3 + 25 + 10 = 67 s | Chờ KEDA, tải model |
| Node có sẵn, image chưa có | 71 s | 127 s | Kéo image |
| Phải thêm node | ~250 s | ~310 s | Cluster autoscaler + kéo image |

p95 toàn hệ bị chi phối bởi hai đường hiếm: thêm node và kéo image. Mục tiêu 15 s p95 **không đạt được** chừng nào còn đường "thêm node" hay "kéo image" trên đường nóng.

## Phương án

| Phương án | Giảm | Chi phí/tháng | Rủi ro |
| --- | --- | --- | --- |
| `pollingInterval: 5` hoặc proxy giữ request (KEDA HTTP add-on) báo ngay | Chờ KEDA 15/29 s → 2/5 s (proxy: ~0) | ~0 (proxy: một Deployment nhỏ) | Hỏi metric nhiều hơn; proxy thêm một chặng |
| Pre-pull image bằng DaemonSet trên pool GPU | Kéo image 35/60 s → 0 | Đĩa node | 40 image × 4,2 GB = 168 GB mỗi node: phải giảm/gộp image |
| Image nhỏ: tách model khỏi image, base chung | Kéo image 35 → ~8 s khi chưa có; base chung chỉ kéo một lần | Công sức | |
| Cache model trên node (local PVC, KServe LocalModel) hoặc định dạng nạp nhanh (safetensors, mmap) | Tải model 12/25 s → 2/4 s | Đĩa node | Đồng bộ cache khi model đổi version |
| Giữ 1 node GPU ấm (cluster autoscaler: overprovisioning bằng pod "placeholder" ưu tiên âm) | Bỏ đường 180 s | ~380 USD | |
| `minReplicaCount: 1` cho 5 model nóng nhất | Bỏ cold start cho chúng | 5 × phần GPU (gộp được trên MIG/chung card) | Tốn tiền nếu đoán sai model nóng |
| Gộp 40 model vào 2–3 server multi-model (Triton, KServe ModelMesh) luôn chạy | Cold start → thời gian nạp một model vào server đã sống (~5–10 s), hoặc 0 nếu đã nạp | 2–3 node T4 ≈ 760–1 140 USD | Model chung tiến trình, một model lỗi ảnh hưởng model khác; cần quản lý bộ nhớ GPU |

## Thứ tự

1. Proxy/`pollingInterval` (rẻ nhất, giảm 13–25 s).
2. Cache model trên node + safetensors (giảm 10–21 s).
3. Overprovisioning 1 node ấm (bỏ đường 180 s, 380 USD).
4. Tách model khỏi image, base chung + pre-pull base (bỏ phần lớn đường kéo image).

Sau 1–4: đường thường ~1 + 1 + 3 + 8 ≈ 13 s p50, ~5 + 3 + 4 + 10 ≈ 22 s p95: vẫn trên 15 s ở p95 vì nạp lên GPU + warm-up 10 s và tải model chưa về 0. Bước 5 là quyết định kiến trúc bên dưới.

## Có cần scale-to-zero không

40 model × vài trăm request/ngày ≈ vài chục nghìn request/ngày: một server multi-model gánh được. 2 node T4 luôn chạy (~760 USD) phục vụ cả 40 model với model nóng luôn nạp sẵn và model lạnh nạp trong vài giây, đạt 15 s p95 và rẻ hơn ngân sách. Scale-to-zero từng model chỉ đáng khi model quá lớn để gộp hoặc tenant cần cô lập.

## Đo và dừng

Đo cold start ở hàng đợi/proxy (thời điểm request đến tới lúc có kết quả, gắn nhãn "từ 0"), như queue của bài trung cấp 01. SLO: 95% request "từ 0" có kết quả trong 15 s mỗi 28 ngày. Dừng tối ưu khi SLO đạt 2 tháng liên tiếp hoặc chi phí bước tiếp theo vượt giá trị product đặt cho nó.

## Rubric (tối đa 20 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Phân rã đúng theo đường, chỉ ra p95 bị chi phối bởi đường hiếm | 4 |
| Ít nhất 6 phương án, mỗi cái quy về một dòng đo, có chi phí và rủi ro | 5 |
| Thứ tự hợp lý theo giảm/chi phí, con số sau mỗi bước | 3 |
| Xem xét bỏ scale-to-zero (gộp model) và so bằng tiền | 4 |
| Có cách đo cold start, SLO cho nó và tiêu chí dừng | 4 |

Từ 14 điểm trở lên là đạt.
