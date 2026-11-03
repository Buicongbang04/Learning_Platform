# Câu hỏi phỏng vấn: Container cho ML

## Vì sao ML cần container, khi đã có virtualenv và `requirements.txt`?

Virtualenv chốt thư viện Python, không chốt Python, thư viện hệ thống (libgomp, OpenSSL, glibc) hay CUDA. Model `joblib` còn phụ thuộc phiên bản scikit-learn đã train nó. Image gói cả tầng đó thành một artifact bất biến có digest, chạy giống nhau ở laptop, CI và production. Đổi lại là phải quản lý image: kích thước, quét lỗ hổng, cập nhật base.

## Image sklearn của bạn nặng 2 GB. Bạn giảm bằng cách nào?

Đo trước (`docker history`, `docker image inspect`) để biết cái gì nặng. Rồi theo thứ tự thường gặp: đổi base đầy đủ sang `slim`; `pip install --no-cache-dir`; multi-stage để stage cuối chỉ có venv; `.dockerignore` loại data, notebook, `.git`; bỏ dependency chỉ dùng khi train (jupyter, matplotlib); torch CPU thay vì bản CUDA nếu không có GPU. Không dùng Alpine chỉ vì nhỏ: wheel numpy/scipy/sklearn không có cho musl nên phải biên dịch, build chậm và dễ lỗi.

## Mỗi lần sửa một dòng code, build lại cài lại cả numpy và scipy. Vì sao và sửa thế nào?

Docker cache theo lệnh và nội dung đầu vào; lệnh nào mất cache thì mọi lệnh sau mất theo. `COPY . .` đứng trước `RUN pip install` làm bất kỳ thay đổi nào trong source vô hiệu hoá bước cài. Sửa: `COPY requirements.txt` rồi `pip install`, code chép sau cùng; thêm `.dockerignore` để thay đổi trong notebook không làm mất cache. Với `uv`, thêm cache mount để giữ cache tải giữa các lần build.

## Đóng model vào image hay để ngoài? Bạn chọn thế nào?

Phụ thuộc kích thước model, nhịp retrain và yêu cầu kiểm toán. Trong image: version model = image digest, rollback bằng cách chạy tag cũ, tái lập tuyệt đối, ít điểm hỏng lúc khởi động; đổi lại mỗi lần retrain là một lần build/đẩy (layer dependency dùng lại nên thực tế nhỏ). Ngoài image: rollout nhẹ, một runtime dùng nhiều model, nhưng thêm điểm hỏng (thiếu file, quyền, registry chết) và phải ghi lại model nào chạy ở đâu. Model vài chục MB retrain hằng đêm: tôi chọn trong image; model hàng GB retrain nhiều lần mỗi ngày: tải từ model registry theo alias và log version lúc khởi động.

## Container Python chạy bằng root có sao không?

Có. Nếu service bị khai thác (deserialize pickle độc hại, lỗ hổng framework), kẻ tấn công có root trong container, dễ leo thang tới host nếu có lỗ hổng container escape hay mount nhạy cảm. Thêm `USER` thường (uid cố định), hệ thống tệp image chỉ đọc nếu được, bỏ capability không cần. Cẩn thận quyền của volume mount: user trong container phải đọc/ghi được đúng thư mục cần.

## `depends_on` có đảm bảo database/MLflow sẵn sàng trước khi API khởi động không?

Không nếu chỉ khai báo tên: nó chỉ đảm bảo thứ tự *khởi động container*. Cần `healthcheck` trên dịch vụ phía trước và `depends_on: {mlflow: {condition: service_healthy}}`. Ngoài ra API nên có retry khi kết nối lần đầu: ở production không có Compose lo thứ tự giúp.

## Healthcheck viết thế nào và những lỗi thường gặp?

Chạy một lệnh nhanh bên trong container kiểm service thật sự phục vụ được (gọi `/healthz`), đặt `interval`, `timeout`, `retries`, `start_period`. Lỗi thường gặp: dùng công cụ không có trong image (`curl` trong image slim), healthcheck chạm dependency ngoài làm cả cụm unhealthy cùng lúc, `start_period` quá ngắn với service nạp model lâu, và không bao giờ chạy thử lệnh healthcheck bên trong container trước khi tin nó.

## Sự cố: "container API restart liên tục". Bạn làm gì?

Theo thứ tự: `docker compose ps -a` (trạng thái, số lần restart, mã thoát: 1 là lỗi của chương trình, 137 là bị kill hoặc OOM, 0 là thoát bình thường), `docker compose logs` (dòng cuối trước khi thoát), `docker inspect` phần `State` (OOMKilled) và `Health`. Rồi tách khỏi Compose: `docker run` image với cùng biến môi trường và mount, chạy shell vào xem tệp và quyền. Nguyên nhân thường là cấu hình thiếu hoặc sai (biến môi trường, đường dẫn, mount, quyền), thiếu bộ nhớ, hoặc tiến trình thoát vì không bắt được dependency. Cuối cùng: đổi `restart: always` thành chính sách có giới hạn để lỗi hiện ra thay vì lặp mãi, và thêm kiểm tra lúc khởi động để thông báo lỗi nói rõ thiếu gì.

## Vì sao chọn trivy, và đặt nó ở đâu trong pipeline?

Trivy quét lỗ hổng gói, misconfiguration của Dockerfile/Compose/Kubernetes và bí mật bằng một công cụ, chạy được trong CI không cần server, `trivy config` chạy offline. Đặt ở PR (config), sau build (image, chặn CRITICAL/HIGH có bản vá) và định kỳ trên image đang chạy. Lựa chọn khác: Grype (nhẹ, chỉ lỗ hổng), Docker Scout (tích hợp Docker Hub), Snyk (thương mại, nhiều tính năng). Chính sách (ngưỡng, lỗ hổng chưa có bản vá, ngoại lệ hết hạn) quan trọng hơn chọn công cụ nào.

## Quét ra 40 lỗ hổng HIGH, hầu hết chưa có bản vá. Có chặn deploy không?

Chặn thì không sửa được và team học cách bỏ qua cổng. Chính sách hợp lý: chặn CRITICAL/HIGH **có bản vá**; lỗ hổng chưa có bản vá được ghi nhận, gán người theo dõi, xét lại khi có bản vá; giảm bề mặt bằng base nhỏ hơn (slim, distroless). Việc bỏ qua unfixed là quyết định chính sách có người chịu trách nhiệm, phải ghi lại, không phải mặc định ngầm.

## Làm sao chạy cùng một image trên laptop CPU và server GPU?

Container không chứa driver; driver ở host và NVIDIA Container Toolkit đưa nó vào container (`--gpus`, hoặc `deploy.resources.reservations.devices` trong Compose). Một Dockerfile với build-arg chọn base (`slim` hay `nvidia/cuda:*-runtime`) và index của torch (cpu hay cuXXX); Compose chia tệp chung và tệp override GPU. CI chạy bản CPU, GPU chỉ ở production. Chú ý khớp phiên bản CUDA của wheel với driver host.

## Bạn ghim phiên bản ở những tầng nào, và ghim digest khi nào?

Base image (tag phiên bản đầy đủ), dependency (`requirements.txt` có phiên bản hoặc `uv.lock`), công cụ build. Tag có thể bị đẩy lại (bản vá của base), nên production tham chiếu **digest** để mọi máy chạy đúng cùng một byte, và dùng công cụ như Renovate để đề xuất cập nhật có kiểm soát thay vì để tag trôi.

## Thiết kế: dịch vụ ETA, 6 replica, model retrain hằng đêm, kiểm toán hỏi "tháng 3 trả ETA bằng model nào". Image và registry ra sao?

Hai tầng: image `base` (OS + dependency, đổi hiếm) và image `service` mỗi đêm thêm code và model (layer mới chỉ cỡ model). Tag bất biến `eta:<git-sha>-m<model-version>`, production tham chiếu digest; label OCI ghi commit, version model, version dữ liệu để truy ngược. Release record lưu digest từng lần lên production và giữ trong thời hạn kiểm toán; image còn được tham chiếu bởi bản ghi đã promote thì không xoá. Rollback = đổi về digest "last good" và rolling update, kèm smoke test. Quét trivy ở build và định kỳ.

## `docker compose down -v` làm gì và vì sao nguy hiểm?

`down` xoá container và network; `-v` xoá cả named volume khai báo trong tệp. Với stack có dữ liệu MLflow hay database trên named volume, `-v` xoá sạch lịch sử thí nghiệm. Dùng `-v` cho môi trường tạm (test, như các bài tập ở đây), không dùng cho môi trường có dữ liệu; backup volume trước khi thao tác.

## Khi nào *không* dùng Docker Compose cho ML?

Compose hợp cho dev, CI, một máy. Khi cần nhiều máy, autoscaling, rolling update có điều kiện, quản lý GPU theo lịch, secret và RBAC thì chuyển sang Kubernetes (các module 13 và 14). Đừng dựng Kubernetes sớm chỉ vì "production-grade": chi phí vận hành lớn hơn lợi ích cho một service trên một máy.
