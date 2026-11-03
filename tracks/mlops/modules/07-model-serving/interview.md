# Câu hỏi phỏng vấn: Model serving

## `/healthz` khác `/readyz` ở điểm nào, và vì sao tách ra?

Liveness (`/healthz`) trả lời "tiến trình có còn xử lý được request không": nếu không, orchestrator khởi động lại nó. Readiness (`/readyz`) trả lời "có nên gửi traffic cho nó lúc này không": 503 khi đang nạp model, đang warmup, đang tắt. Gộp làm một thì sai cả hai chiều: nạp model lâu bị giết vì liveness fail, hoặc nhận traffic khi chưa có model. Liveness không nên phụ thuộc dịch vụ ngoài, vì registry chập chờn sẽ làm orchestrator giết cả đàn replica đang khoẻ.

## Service của bạn khởi động thế nào, và khi nào nó nhận traffic?

Tiến trình lên, `/healthz` 200 ngay, thread nền phân giải alias ra số version, nạp model, chạy warmup, rồi `/readyz` mới 200. Load balancer chỉ gửi traffic từ lúc đó. Tôi ghi version đã nạp vào log và vào mọi response. Nếu nạp lỗi thì `/readyz` giữ 503 kèm lý do, orchestrator giữ bản cũ thay vì thay bằng bản hỏng.

## Vì sao service nạp model bằng alias thay vì "version mới nhất"?

"Mới nhất" là version ai đó vừa đăng ký, có thể chưa qua cổng nào; alias (`champion`) là con trỏ chỉ đổi khi có quyết định. Phân giải alias ra số version lúc khởi động và ghim nó: log và response nói `version=7` (truy được), không nói `champion` (đổi nghĩa theo thời gian). Không có alias thì không khởi động, thay vì lặng lẽ fallback sang model chưa duyệt.

## Rollback một model trong vài phút, không rebuild: làm thế nào?

Đổi alias `champion` về version tốt trong registry, rồi gọi `POST /admin/reload` ở từng replica. Service nạp model cũ trước, đổi con trỏ trong một bước, và nếu nạp lỗi thì giữ model đang chạy. Xác nhận bằng `model_version` trong response. Điều kiện: reload idempotent, có xác thực, và có người biết version nào là bản tốt. Đánh đổi: trạng thái deploy nằm ở registry, nên kiểm toán phải giữ lịch sử alias; nếu cần "mọi thứ trong Git" thì ghim version trong manifest và rollback bằng commit.

## Canary khác shadow và A/B ở điểm nào? Khi nào dùng cái nào?

Shadow: model mới chạy trên traffic thật nhưng người dùng chỉ thấy model cũ; trả lời "nó chạy được không, lệch bao nhiêu", rủi ro gần bằng không, tốn gấp đôi tài nguyên. Canary: một phần nhỏ người dùng nhận model mới; đo số vận hành thật (lỗi, độ trễ, phân phối dự đoán), rủi ro có giới hạn. A/B: hai biến thể chạy lâu, so tác động nghiệp vụ có ý nghĩa thống kê, cần cỡ mẫu. Thứ tự thường dùng: shadow, canary nhỏ rồi lớn dần, và A/B khi cần đo tác động kinh doanh.

## Vì sao định tuyến canary bằng hash `request_id` thay vì random mỗi request?

Random làm cùng một request (hay người dùng) lúc vào bản này lúc vào bản kia, không tái lập được và không phân tích được. Hash ổn định (SHA-256, không phải `hash()` của Python vì nó đổi theo tiến trình) cho cùng id luôn cùng nhánh ở mọi replica, tỉ lệ xấp xỉ trọng số, và tăng trọng số chỉ thêm id vào canary chứ không đảo ai. Thêm salt theo thí nghiệm để các thí nghiệm độc lập nhau. Chọn khoá theo yêu cầu: `request_id` cho canary vận hành, `user_id` khi trải nghiệm phải nhất quán.

## Bạn thiết kế shadow mode thế nào để chắc nó vô hình với người dùng?

Response luôn là của model chính, nguyên vẹn. Shadow chạy ngoài đường của request (thread/hàng đợi nền) trên bản sao của đầu vào, nên chậm hay lỗi không tới được request. Kết quả shadow chỉ vào log kèm request id, hai version, độ lệch lớn nhất. Lỗi ghi log cũng không làm hỏng request. Hàng đợi shadow phải có giới hạn và đo tỉ lệ bị bỏ, nếu không shadow chậm sẽ ăn hết bộ nhớ.

## Đọc kết quả k6 thế nào để kết luận "service đạt"?

Nhìn p95 (và p99) của `http_req_duration` so với SLO, không nhìn trung bình; `http_reqs` để biết thông lượng thật có bằng tải đặt không; `http_req_failed` và `checks` để chắc rằng độ trễ đẹp không phải do lỗi trả nhanh; `dropped_iterations` để biết k6 có theo kịp nhịp không. Đặt ngưỡng từ SLO, và để k6 thoát mã 99 khi vi phạm để chặn được pipeline. Nhớ rằng sinh tải cùng máy với service làm số đo mang tính tương đối.

## Vì sao dùng `constant-arrival-rate` thay vì số VU cố định?

VU cố định là closed model: mỗi VU chờ response rồi mới gửi tiếp, nên service chậm làm tải tự giảm, và đo ra p95 đẹp hơn thực tế (coordinated omission). `constant-arrival-rate` giữ nhịp đến như người dùng thật, nên hàng đợi dài ra khi service chậm và p95 phản ánh điều họ thấy. Cái giá: cần đủ VU cấp phát trước, thiếu thì k6 bỏ request.

## Sau mỗi lần deploy, p99 tăng vọt trong vài chục giây rồi tự hạ, p50 không đổi, không có lỗi. Bạn điều tra thế nào?

Trước hết xác nhận triệu chứng bằng số: p99 theo thời gian kể từ khi từng replica khởi động, và độ trễ theo thứ tự request trên một replica mới. Tái lập trên máy dev: khởi động và gọi 30 request liên tiếp, in từng độ trễ; hình dạng chuỗi (chỉ vài lần đầu hay đều đều) chia hẹp vùng nghi vấn. So với bản trước, xem có đổi gì ngoài mã (tài nguyên, dữ liệu, cấu hình). Rồi đo từng bước trong đường xử lý (span hoặc `perf_counter`) và đọc mã ở chỗ đo ra chậm. Cuối cùng viết một test hồi quy đo đúng đại lượng đó, để lỗi không quay lại. Tôi không kết luận nguyên nhân trước khi có phép đo.

## Chọn giữa FastAPI tự viết, BentoML, Triton, Ray Serve cho một service mới?

Bắt đầu từ ràng buộc: thông lượng và độ trễ mục tiêu, số model, CPU hay GPU, đồ thị nhiều bước hay không, đội vận hành bao nhiêu người. Một vài model sklearn, vài trăm rps, đội nhỏ: FastAPI tự viết là đủ và dễ debug. Nhiều model Python cần chuẩn hoá đóng gói và batching: BentoML. Deep learning trên GPU, thông lượng cao: Triton (đổi lại định dạng model và cấu hình). Pipeline nhiều bước co giãn theo Ray: Ray Serve. Tôi loại phương án vượt khả năng vận hành của đội trước khi so điểm mạnh, và kiểm tình trạng bảo trì của dự án (TorchServe, chẳng hạn) trước khi phụ thuộc.

## Khi nào chọn batch inference thay vì API realtime?

Khi người dùng không cần câu trả lời trong vài trăm mili giây và đầu vào là cả một bảng: dự đoán nhu cầu mỗi sáng, điểm số khách hàng hằng đêm. Job theo lịch rẻ hơn (chạy ngắn), lỗi chỉ cần chạy lại, dễ so hai phiên bản trên cùng bảng. Vấn đề: dữ liệu về muộn, chạy hai lần ra hai kết quả, bảng dự đoán cũ (stale) với khoá mới. Kết hợp thường hợp lý: batch tính trước, API tra bảng và tính tại chỗ cho khoá mới. Tôi luôn ghi `model_version` vào từng dòng đầu ra.

## Thiết kế hệ thống: service dự đoán ETA 200 rps, p95 dưới 150 ms, retrain hằng đêm. Bạn dựng và tung model mới thế nào?

Service FastAPI trong container, 3 replica CPU sau load balancer, nạp model theo alias `champion`, ghim version, có `/healthz`, `/readyz` (503 tới khi nạp và warmup xong), timeout, validate, và trả `model_version`. Mỗi đêm train xong, cổng promotion (module 04, 08) quyết định có chuyển alias hay không; model mới đi qua shadow vài giờ cao điểm, rồi canary 1%, 5%, 25% với guardrail so với stable cùng cửa sổ (5xx, p95, phân phối dự đoán, MAE theo nhãn trễ), và rollback tự động bằng đổi alias + reload khi guardrail vi phạm hai cửa sổ liên tiếp. Cổng k6 trong CI kiểm p95 trước khi chuyển. Giám sát và alert ở module 09. Tôi nêu rõ điều thiết kế này không bắt được: nhãn đến trễ 30 phút, slice hiếm, mùa vụ.

## Graceful shutdown để làm gì, và làm thế nào?

Để deploy không làm rơi request đang dở. Khi nhận SIGTERM: `/readyz` về 503 ngay để load balancer ngừng gửi request mới, service xử lý nốt request đang chạy trong thời hạn (uvicorn `--timeout-graceful-shutdown`), rồi thoát. Trên Kubernetes thêm một `preStop` ngủ vài giây vì cập nhật danh sách endpoint không tức thời; `terminationGracePeriodSeconds` phải dài hơn thời gian xử lý lâu nhất.

## Bạn bảo vệ endpoint `/admin/reload` thế nào?

Nó đổi model production nên coi như quyền promote: không công khai qua ingress, chỉ nghe trên mạng nội bộ hoặc cổng riêng, xác thực bằng token (hoặc mTLS) do hệ thống quản lý bí mật cấp, ghi log ai gọi và đổi từ version nào sang version nào. Reload idempotent (không đổi nếu alias không đổi), và nạp lỗi thì giữ model cũ, nên gọi nhầm hoặc lặp không gây hại.
