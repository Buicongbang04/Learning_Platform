# Câu hỏi phỏng vấn: Kubernetes cho ML

## Khi nào một service model nên lên Kubernetes, khi nào Compose hay một VM là đủ?

Kubernetes đáng giá khi có nhiều service/model cần chung một cách deploy, rollout và rollback; khi cần tự phục hồi (pod chết thì được thay), nhiều replica trên nhiều node, tách tài nguyên giữa serving và training, hoặc GPU được lập lịch như tài nguyên chung. Đổi lại là chi phí vận hành cluster (nâng cấp, bảo mật, mạng, observability) và một lớp trừu tượng mới cho cả đội.

Một model, traffic đều, một đội nhỏ: Compose trên một VM hoặc dịch vụ managed (Cloud Run, App Runner, SageMaker endpoint) thường rẻ và đủ. Dấu hiệu nên chuyển: số service tăng, deploy bằng tay hay lỗi, cần canary/rollback chuẩn hoá, nhiều đội dùng chung GPU. Nếu công ty đã có platform K8s thì ngưỡng thấp hơn nhiều: chi phí cluster đã được trả.

## Giải thích startupProbe, readinessProbe và livenessProbe cho một service phải nạp model 60 giây.

- **startupProbe**: "đã khởi động xong chưa". Ngân sách `initialDelaySeconds + periodSeconds × failureThreshold` nên gấp khoảng hai lần thời gian nạp đo được, ví dụ 10 × 12 = 120 giây. Trong lúc nó chưa thành công, kubelet không chạy hai probe kia.
- **readinessProbe**: "nhận traffic được chưa". Kiểm model đã nạp (endpoint trả version), không chỉ cổng TCP. Thất bại chỉ bỏ pod khỏi Endpoints.
- **livenessProbe**: "có bị treo không". Chặt (phát hiện trong vài chục giây), không kiểm phụ thuộc ngoài (database, feature store), vì phụ thuộc chậm sẽ làm mọi pod bị giết cùng lúc.

Sai lầm thường gặp: không có startupProbe, liveness giết pod giữa lúc nạp model, pod rơi vào vòng restart không bao giờ xong; hoặc chữa bằng `initialDelaySeconds: 120` trên liveness, áp cho mọi lần khởi động và làm chậm phát hiện treo.

## requests và limits khác nhau thế nào? Đặt cho một service model ra sao?

requests là thứ scheduler dùng để xếp pod (node phải còn đủ requests) và là trọng số chia CPU khi tranh chấp; limits là trần lúc chạy. Vượt limit CPU thì bị throttle (chậm, latency tăng); vượt limit bộ nhớ thì kernel giết tiến trình. QoS: không khai gì là `BestEffort` (bị đuổi trước), requests = limits là `Guaranteed`.

Cách đặt: đo, không đoán. Chạy ở staging dưới tải giống thật, đọc metric cAdvisor/Prometheus của container; requests quanh mức dùng thường, limit có dư so với mức cao nhất quan sát được; đo lại khi model hay thư viện đổi. Với CPU, nhiều đội bỏ limit để tránh throttle làm tăng p95, chỉ giữ requests và quota ở mức namespace.

## Một pod model bị restart liên tục ngay sau khi deploy bản mới. Bạn chẩn đoán theo thứ tự nào?

1. `kubectl get pods`: STATUS (`CrashLoopBackOff`, `Error`, `OOMKilled`), RESTARTS, thời gian.
2. `kubectl describe pod`: Events (probe thất bại? kéo image lỗi? không xếp được?) và `Last State` của container: `Reason`, `Exit Code`. Exit code > 128 là chết do tín hiệu (137 = SIGKILL, 143 = SIGTERM).
3. `kubectl logs --previous`: log của lần chạy vừa chết. Log dừng giữa chừng không có traceback thường nghĩa là bị giết từ bên ngoài, không phải lỗi code.
4. Đối chiếu với thay đổi: bản mới đổi gì (image, model, config, probe, resources)? So với bản trước đang chạy ổn.
5. Sửa tối thiểu, rollback trước nếu ảnh hưởng người dùng, rồi viết postmortem với hành động ngăn tái diễn (checklist release, alert theo lý do kết thúc container).

Điều quan trọng là phân biệt ba nhóm: kubelet giết (probe), kernel giết (tài nguyên), tiến trình tự thoát (lỗi code, thiếu file, sai config). Mỗi nhóm để lại dấu vết ở chỗ khác nhau.

## InferenceService báo Ready nhưng người dùng nhận dự đoán của model cũ. Vì sao có thể xảy ra và ngăn thế nào?

Ready chỉ có nghĩa là Deployment predictor Available: container trả lời probe. Nguyên nhân hay gặp: probe chỉ kiểm cổng TCP; biến `MODEL_PATH` thiếu nên service nạp giá trị mặc định; ConfigMap đã sửa nhưng pod chưa rollout (env chỉ đọc lúc khởi động); `storageUri` trỏ alias `latest/` chưa cập nhật; cache model ở node.

Ngăn: service tự báo `model_version` (lấy từ chính artifact, không từ biến môi trường); readinessProbe kiểm endpoint model; pipeline CD sau mỗi deploy gọi `GET /v1/models/<tên>` và một `predict` mẫu qua Service, so version và dự đoán với kỳ vọng, lệch thì rollback; version model trong manifest là cố định, không phải alias.

## Vì sao chọn KServe? So với tự viết Deployment, Seldon, BentoML hay dịch vụ managed.

KServe cho một API khai báo (`InferenceService`) thống nhất cho nhiều framework (runtime sklearn, xgboost, Triton, vLLM, Hugging Face), giao thức chuẩn (v1, Open Inference Protocol v2), transformer/explainer, canary và scale về 0 ở chế độ Serverless, storage-initializer tải model từ S3/GCS/PVC. Nó là dự án CNCF, phổ biến trong Kubeflow.

Tự viết Deployment + Service: đơn giản, không thêm CRD, đủ khi có ít model; nhưng mỗi đội tự làm lại probe, giao thức, rollout. Seldon Core: tương tự, mạnh về graph suy luận, license đã đổi (BSL) nên cân nhắc. BentoML: mạnh ở đóng gói phía Python, deploy lên K8s qua Yatai/BentoCloud. Managed (SageMaker, Vertex AI): ít vận hành, khoá vào cloud, chi phí cao hơn khi traffic lớn. Chọn KServe khi đã có K8s, nhiều model và nhiều framework, muốn chuẩn hoá; chọn Deployment thường khi có một hai model và đội không muốn vận hành thêm controller.

## RawDeployment và Serverless của KServe khác nhau thế nào? Canary chạy ra sao ở mỗi chế độ?

Serverless dựng trên Knative: mỗi thay đổi tạo một revision, Knative giữ nhiều revision và chia traffic theo phần trăm, scale về 0 khi không có request; cần Knative Serving và một ingress (Istio, Kourier). RawDeployment (KServe 0.21 gọi là Standard) tạo Deployment + Service + HPA thường: không scale về 0, không revision, ít thành phần hơn.

`canaryTrafficPercent` chỉ hoạt động ở Serverless. Ở RawDeployment, trường này bị bỏ qua và Deployment rolling update thẳng sang bản mới, nên tưởng là 20% nhưng thật ra 100%. Canary ở RawDeployment: hai InferenceService sau một Service chung (tỉ lệ theo số replica, chia theo kết nối) hoặc route L7 có trọng số (Gateway API `HTTPRoute`, mesh). Luôn đo tỉ lệ thật từ trong cluster hoặc từ metric của từng version.

## Argo Workflows, Argo CD, Kubeflow Pipelines, Airflow: mỗi cái giải quyết việc gì?

- **Argo Workflows**: chạy DAG/steps mà mỗi bước là một pod; parameter, artifact (S3/MinIO/GCS), retry, `CronWorkflow`. Hợp với pipeline training khi các bước đã là container và cần tài nguyên K8s.
- **Argo CD**: GitOps, so trạng thái cluster với Git và đồng bộ; không chạy pipeline. Trả lời "production đang chạy gì" bằng commit.
- **Kubeflow Pipelines**: dựng trên Argo (hoặc Tekton), thêm SDK Python, theo dõi artifact và metadata ML, UI so sánh run.
- **Airflow**: orchestrator lịch và phụ thuộc rất phổ biến, Python, nhiều tích hợp; chạy task thành pod bằng KubernetesExecutor/KubernetesPodOperator.

Một tổ hợp hay gặp: Argo Workflows (hoặc KFP) train và ghi model vào registry, mở PR đổi version model trong manifest; Argo CD đồng bộ sau khi merge.

## Trong Argo Workflow, khi nào truyền bằng parameter, khi nào bằng artifact?

Parameter là chuỗi nhỏ nằm trong object Workflow (lưu ở etcd): seed, tháng dữ liệu, ngưỡng, kết quả số (MAE). Dùng được trong `when` để rẽ nhánh. Artifact là tệp: executor đẩy lên kho (S3/MinIO) khi bước xong và kéo xuống bước sau: dữ liệu, model, báo cáo. Nhét dữ liệu vào parameter làm object Workflow phình, chạm giới hạn kích thước object của K8s (~1,5 MB), và làm chậm controller.

Hệ quả vận hành: kho artifact cần vòng đời (xoá artifact cũ), quyền đọc/ghi cho executor, và artifact quan trọng (model đã duyệt) nên được ghi vào model registry chứ không chỉ nằm trong kho của Argo.

## retryStrategy nên đặt thế nào cho bước train tốn 2 giờ GPU?

Phân biệt lỗi: `retryPolicy: OnError` chỉ thử lại lỗi hạ tầng (pod bị evict, node mất, lỗi executor); `OnFailure` thử lại khi container thoát với mã khác 0 (lỗi code hay dữ liệu thì thử lại vô ích và tốn GPU); `Always` cả hai. Với bước train dài: `OnError` hoặc `OnTransientError` với `limit` nhỏ (2), `backoff` có `duration` và `factor`, và **checkpoint** định kỳ ra kho để lần thử lại tiếp tục từ checkpoint chứ không từ đầu. Nếu chạy trên spot/preemptible, retry + checkpoint là điều kiện bắt buộc. Bước tải dữ liệu từ nguồn chập chờn thì retry rộng hơn, vì rẻ.

## Làm sao chạy GPU trên Kubernetes? Những lỗi tốn tiền nào hay gặp?

Node có driver NVIDIA và container toolkit; NVIDIA device plugin (thường cài qua GPU Operator) quảng bá `nvidia.com/gpu`; pod xin `resources.limits: {nvidia.com/gpu: 1}` (số nguyên). Node GPU gắn taint, pod GPU có toleration; DCGM exporter đưa metric GPU vào Prometheus. Chia GPU: time-slicing (không cô lập bộ nhớ) hoặc MIG trên A100/H100.

Lỗi tốn tiền: pod CPU chiếm node GPU (thiếu taint); GPU nhàn rỗi (notebook để mở, serving traffic thấp giữ card cả ngày); xin GPU cho model nhỏ chạy CPU đủ nhanh; cluster autoscaler không co node GPU vì còn một pod lặt vặt. Theo dõi utilization theo đội, và chỉ cấp GPU qua hàng đợi/quota (Kueue, module 14).

## kind có những giới hạn gì khi dùng để học và test ML trên Kubernetes?

kind chạy node là container Docker: không có LoadBalancer cloud (dùng NodePort, port-forward hoặc MetalLB), GPU passthrough phức tạp, đĩa và mạng khác cluster thật, thường một node nên không thấy được hành vi scheduling, anti-affinity, node drain thật. Image tự build phải nạp bằng `kind load`; tag `:latest` làm kubelet đi kéo từ registry. Tài nguyên dùng chung với máy (cgroup của node là container), nên đo hiệu năng trên kind không đại diện cho production. Bù lại: dựng lại trong vài phút, chạy được CRD và controller thật (KServe, Argo), đủ cho CI và lab.

## Thiết kế hệ thống: đưa dịch vụ ETA (API sklearn, retrain hằng đêm, MLflow registry) lên Kubernetes cho 3 đội dùng chung.

Khung trả lời:

- **Tách namespace theo đội và theo môi trường**; quota CPU/bộ nhớ/GPU theo namespace; RBAC: pipeline có quyền ghi namespace của mình, người chỉ đọc production.
- **Serving**: InferenceService custom predictor (service đã test ở module 07) hoặc runtime sklearn nếu không có tiền xử lý; startup/readiness/liveness đúng vai; requests/limits từ số đo; 2+ replica, PDB; version model cố định trong manifest; smoke test kiểm `model_version` sau deploy.
- **Phát hành**: canary hai InferenceService hoặc Serverless nếu cần tỉ lệ mịn; tiêu chí tăng/rút theo tỉ lệ lỗi, p95 và metric chất lượng; rollback < 2 phút.
- **Training**: Argo `CronWorkflow` prepare → train → evaluate → register; artifact trên S3; retry cho lỗi hạ tầng; chỉ register khi đạt ngưỡng; ghi lineage (commit, data version) vào MLflow.
- **GitOps**: pipeline mở PR đổi version model; Argo CD đồng bộ; rollback = revert.
- **Trạng thái ngoài cluster**: MLflow backend (Postgres) và kho artifact là managed service; cluster có thể dựng lại.
- **Observability**: metric request và model (module 09), alert theo lý do kết thúc container và tốc độ restart, không chỉ theo Ready.
- **Đánh đổi nêu rõ**: thêm KServe/Argo là thêm controller phải nâng cấp; với một model duy nhất, Deployment thường + CronJob có thể đủ.

## Đổi giá trị trong ConfigMap mà service vẫn chạy cấu hình cũ. Vì sao, và nên thiết kế thế nào?

Biến môi trường lấy từ ConfigMap (`envFrom`, `configMapKeyRef`) chỉ được đọc lúc container khởi động; sửa ConfigMap không làm pod đang chạy đổi theo, và không tạo rollout vì template của Deployment không đổi. ConfigMap mount thành volume thì tệp được cập nhật sau một khoảng trễ (trừ khi dùng `subPath`), nhưng ứng dụng phải tự đọc lại.

Thiết kế: coi cấu hình quyết định model (đường dẫn, version) là một phần của release. Sinh tên ConfigMap theo hash nội dung (Kustomize `configMapGenerator`, Helm checksum annotation) để đổi cấu hình kéo theo rollout có kiểm soát và rollback được; hoặc ghi version model thẳng vào spec. Sau rollout, smoke test kiểm `model_version` qua Service. Tránh để service tự reload cấu hình model lúc chạy mà không có dấu vết: khó biết lúc nào pod nào chạy model nào.
