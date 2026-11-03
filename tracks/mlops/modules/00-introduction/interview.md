# Câu hỏi phỏng vấn: Giới thiệu MLOps

## MLOps là gì và khác DevOps thế nào?

MLOps là tập thực hành để đưa model vào production và giữ nó chạy đúng, lặp lại được. DevOps lo vòng đời của **code**. ML thêm
hai thứ biến đổi: **dữ liệu** (đổi mà không ai commit) và **model** (artifact sinh ra từ code + dữ liệu + cấu hình). Hệ quả cụ
thể: cần version cho dữ liệu và model, kiểm thử bằng ngưỡng thống kê chứ không chỉ đúng/sai, và monitoring chất lượng chứ
không chỉ uptime, vì model hỏng vẫn trả 200.

Ứng viên senior nói thêm: MLOps không phải một chức danh đóng khung; nó là việc có người chịu trách nhiệm ở các ranh giới
giữa DS, DE và backend.

## Mô tả vòng đời ML trong production và chỗ nào hay hỏng nhất

Bài toán → dữ liệu → feature → train + đánh giá → registry → serving → monitoring, rồi quay lại dữ liệu khi drift. Chỗ hay hỏng:
(1) rò rỉ nhãn vì dùng thông tin chưa có lúc dự đoán, (2) training-serving skew do feature tính hai nơi, (3) deploy nhầm
model vì không có alias/cổng, (4) không log dự đoán nên về sau không nối được nhãn thật. Câu trả lời tốt chọn một chỗ và kể
một sự cố cụ thể kèm cách phát hiện.

## Giải thích maturity level 0, 1, 2 của Google. Hệ thống có Airflow chạy train hằng đêm ở mức nào?

Mức 0: thủ công. Mức 1: pipeline ML tự động (CT), có kiểm tra dữ liệu và model, tracking/registry, trigger tự động; deploy
pipeline vẫn tay. Mức 2: CI/CD cho chính pipeline. Có Airflow chạy train hằng đêm **chưa đủ** để nói mức 1: phải hỏi thêm có
validate dữ liệu và model trước khi ghi đè không, có registry không, có cổng không. Nếu model mới tự ghi đè model đang chạy
mà không kiểm tra, đó là automation thiếu an toàn, nguy hiểm hơn thủ công.

## Hai thang maturity của Google và Microsoft khác nhau thế nào? Bạn dùng cái nào?

Google 3 mức, nhìn mức tự động hoá của pipeline. Microsoft 5 mức, chia mịn hơn ở deploy và vận hành (mức 1 "DevOps nhưng chưa
MLOps", mức 4 monitoring kích hoạt retrain). Dùng cả hai như ngôn ngữ chung, nhưng quan trọng hơn là liệt kê **việc đang làm
tay gây sự cố hoặc tốn giờ nhất** và sửa việc đó trước. Đội 3 người với một model hằng tuần không cần mức 2.

## Sự cố: ETA tăng sai 40% sau đợt khuyến mãi, health check vẫn xanh, và mất 5 ngày mới xử lý xong. Bạn điều tra và sửa thế nào?

Thứ tự: (1) **xác minh** là sai thật: so dự đoán với thời gian giao thực tế (nếu không log dự đoán thì chính đây là lỗi hệ
thống số 1); (2) **khoanh vùng**: toàn bộ hay một slice (khu vực, khung giờ), có đổi version model hay dữ liệu đầu vào hay
không; (3) **giảm thiệt hại**: quay về model trước ngay nếu có, nếu không có thì đây là lỗi thứ hai; (4) **nguyên nhân**: drift
do khuyến mãi (concept drift) hay lỗi pipeline dữ liệu; (5) **quyết định** retrain / rollback / giữ nguyên có số liệu;
(6) postmortem với việc chặn lần sau: log dự đoán, job MAE hằng ngày, registry giữ mọi version, runbook. Phát hiện và quay lui
là hai khả năng rẻ nhất mà đáng nhất.

## "Hidden technical debt in ML" nói gì? Cho ba ví dụ bạn từng gặp hoặc sẽ kiểm tra.

Bài báo của Sculley et al.: phần model là hộp nhỏ, nợ nằm ở hệ thống xung quanh. Ba ví dụ: **data dependency không ổn
định** (feature đến từ bảng của đội khác, đổi schema không báo; chặn bằng data contract); **glue code và pipeline jungle**
(chặn bằng pipeline khai báo); **configuration debt** (đường dẫn hard-code, chạy được trên máy một người; chặn bằng config
tách code, ghim môi trường). Bổ sung: feedback loop và undeclared consumer. Nên nói thêm cách biến chúng thành kiểm tra tự
động, ví dụ quét repo tìm model/dữ liệu bị commit hoặc dependency không ghim.

## Ai chịu trách nhiệm khi model sai trên production: DS, ML engineer hay MLOps?

Câu hỏi bẫy. Câu trả lời sai: "DS vì model của họ" hay "MLOps vì họ lo production". Trả lời tốt: phân tách **A** (chịu trách
nhiệm cuối) cho từng loại sự cố. Service chết hay chậm: ML engineer/MLOps. Model sai vì drift: DS đọc chỉ số, người sở hữu
sản phẩm quyết định retrain hay rollback. Dữ liệu đổi schema: DE (data contract). Rollback model: MLOps có quyền làm ngay theo
runbook. Điều quan trọng là phân công được viết ra trước khi có sự cố, tách quyền duyệt khỏi quyền làm.

## Đội mới có 1 DS và 1 backend, model đầu tiên sắp lên production. Bạn dựng gì trước và cố ý chưa dựng gì?

Trước hết (rẻ, giảm thiệt hại lớn): môi trường ghim, script train có seed, registry (MLflow) giữ mọi version để quay lui,
log mỗi dự đoán, một job tính chất lượng khi có nhãn, health check + metric cơ bản, bí mật ra khỏi code. Cố ý chưa: Kubernetes,
feature store, orchestrator phức tạp, training phân tán, vì chưa có vấn đề đo được cần chúng. Nêu điều kiện để xem lại: số
model, số người, tần suất retrain, tải. Cho thấy bạn biết chi phí vận hành của mỗi công cụ.

## Vì sao chọn MLflow thay vì Weights & Biases hay Neptune? Và khi nào bạn đổi ý?

MLflow: mã nguồn mở, tự host (kiểm soát dữ liệu), có cả tracking và model registry, tích hợp rộng; yếu ở UI và cộng tác so với
W&B. W&B/Neptune/Comet: UX, so sánh run, báo cáo tốt, chạy managed, đổi lại là chi phí và dữ liệu đi ra ngoài. Chọn theo ràng
buộc: dữ liệu nhạy cảm hoặc ngân sách thấp, MLflow; đội nghiên cứu nhiều thí nghiệm cần cộng tác, W&B hợp hơn. Đổi ý khi chi
phí vận hành MLflow server vượt giá dịch vụ, hoặc khi nhu cầu cộng tác vượt khả năng UI.

## Vì sao chọn DVC chứ không phải Git LFS hay chỉ thư mục theo ngày trên S3?

DVC gắn **phiên bản dữ liệu với commit** bằng hash nội dung (tệp `.dvc`, `dvc.lock` nằm trong Git), có khái niệm pipeline và
cache, remote ở S3/MinIO. Git LFS không biết pipeline và có giới hạn dung lượng/băng thông trên host; thư mục theo ngày không
cho phép `git checkout` về đúng trạng thái. Nhược điểm của DVC: thêm một công cụ phải dạy, remote cần cấu hình, dễ quên
`dvc push`. Nếu dữ liệu nhỏ và bất biến, một snapshot có hash trong Git cũng đủ.

## Tại sao không cần Kubernetes ngay từ đầu? Khi nào thì cần?

Kubernetes giải bài toán điều phối nhiều dịch vụ, scale, tự phục hồi, multi-tenant. Với một service 8 request/giây trên một
VM, nó thêm hàng loạt thứ phải vận hành (cluster, ingress, RBAC) mà không giải vấn đề đang đau. Cần khi: nhiều dịch vụ và đội
chung hạ tầng, cần autoscale theo tải, GPU chia sẻ giữa các job, hoặc yêu cầu độ sẵn sàng cao hơn một VM. Docker Compose đủ
cho giai đoạn đầu và là bước đệm: chuyển Compose sang K8s ở module 13 là việc có thể làm khi cần.

## Thiết kế hệ thống ML: dự đoán thời gian giao hàng (ETA) cho app giao đồ ăn, 10 000 request/giây cao điểm. Bạn thiết kế thế nào ở mức tổng thể?

Làm rõ yêu cầu: độ trễ (< 100 ms?), độ tươi của feature, nhãn về lúc nào (khi giao xong, tức muộn), chi phí sai. Kiến trúc: đường
**realtime** (API stateless, model nạp theo alias từ registry, nhiều replica sau load balancer, cache feature nóng), feature
online từ feature store (cùng định nghĩa với offline để tránh skew), **log mọi dự đoán** (request id, version, feature) vào
stream để về sau join với nhãn; đường **batch** để tính lại và backfill. Vòng vận hành: pipeline training theo lịch + khi
drift, cổng promotion (MAE tổng, slice theo khu vực/khung giờ, độ trễ), canary/shadow trước khi chuyển hết, rollback bằng đổi
alias. Monitoring: RED cho service, phân phối dự đoán, drift feature, MAE khi nhãn về. Nêu đánh đổi: chất lượng so với độ
trễ, độ tươi feature so với chi phí.

## Làm sao biết một dự án ML sẵn sàng lên production? Bạn có checklist nào?

Dùng ý tưởng ML Test Score: (1) dữ liệu: schema được kiểm, phiên bản ghim; (2) model: tái lập được, kiểm slice, so với baseline
và model đang chạy, test hành vi; (3) hạ tầng: pipeline chạy một lệnh, môi trường ghim, deploy và rollback đã thử; (4)
monitoring: log dự đoán, chỉ số chất lượng, alert có chủ, runbook. Ứng viên mạnh thêm: "thử rollback trước khi cần" và "đã
diễn tập một sự cố". Phản ví dụ: xong khi AUC đẹp trên notebook.

## Một người trong đội đề xuất dựng Kubeflow, Istio và Kafka "cho đúng chuẩn MLOps". Bạn phản biện thế nào?

Không phản biện bằng ý kiến mà bằng câu hỏi: vấn đề nào đo được mà công cụ hiện tại không giải được? Chi phí vận hành (nhân lực,
nâng cấp, trực) của mỗi thành phần là gì? Lộ trình thay thế dần ra sao? Đề xuất bước nhỏ nhất (Compose + MLflow + orchestrator
nhẹ), kèm điều kiện cụ thể để thêm từng thành phần. Tránh hai cực: từ chối mọi công cụ mới, hoặc đồng ý vì "chuẩn ngành".
