# Câu hỏi phỏng vấn: Experiment tracking và model registry

## Experiment tracking giải quyết vấn đề gì mà notebook và Git chưa giải quyết?

Git lưu code, không lưu "lần chạy": tham số, số đo, dữ liệu đã dùng, artifact sinh ra, và liên hệ giữa chúng. Tracking ghi mỗi
lần train thành một run có param, metric, tag (git commit, phiên bản dữ liệu) và artifact, để trả lời được sau vài tháng "model
AUC 0.80 này train bằng gì". Có truy vấn thay cho đọc notebook, và so sánh thay cho trí nhớ. Điều kiện để có ích: quy ước đặt
tên, tag bắt buộc và ghi dữ liệu cùng model.

## Vì sao không dùng file store `./mlruns` khi cả đội dùng chung?

Ghi đồng thời lên cùng thư mục dễ hỏng, truy vấn chậm khi có nhiều run, Model Registry cần backend database, và MLflow 3 đã đưa
file store vào chế độ bảo trì. Chuyển sang server với Postgres (backend) và S3/MinIO (artifact). SQLite vẫn ổn khi học một mình
hoặc cho test. Điều đổi lại: có thêm thứ phải vận hành, backup và bảo mật.

## Một run cần những gì để "tái lập được"? Bạn ghi lineage thế nào?

Ba thứ: code (git commit, kèm cờ cây thư mục bẩn), dữ liệu (hash phiên bản, lấy từ `dvc.lock`), môi trường (lockfile hoặc
digest image). Tôi ghi chúng thành tag ngay lúc tạo run. Cây bẩn thì ghi `git_dirty=true` và cổng promotion từ chối.
Lợi ích thứ hai là truy ngược: khi phát hiện một phiên bản dữ liệu lỗi, `tags.data_version = '...'` cho biết model nào bị ảnh
hưởng.

## Alias khác stage ở registry như thế nào, và vì sao alias thắng?

Stage (`Staging`/`Production`) là một vòng đời cố định và bị MLflow deprecated; mỗi model chỉ có vài trạng thái. Alias là
con trỏ có tên tới một version, đặt tên tự do (`champion`, `challenger`, `shadow-eu`), một version có thể có nhiều alias. Service
nạp `models:/tên@champion`; đổi model nghĩa là đổi con trỏ, không phải deploy lại. Trạng thái phê duyệt đặt ở tag, không ở alias.

## Làm thế nào rollback một model trong 5 phút lúc 3 giờ sáng?

Dời alias `champion` về version trước. Để người trực không phải nhớ, lúc promote ghi tag `previous_champion` lên version mới.
Version lỗi giữ lại để điều tra. Với service đang chạy cần cơ chế nạp lại: restart, hoặc poll alias và nạp lại với quy tắc
"refresh lỗi thì giữ model cũ". Sau rollback phải kiểm bằng đầu ra thật (phân phối dự đoán, `model_version` trong response), không
chỉ tin vào việc đã đổi alias.

## Sự cố: sau một đợt deploy thường lệ, dự đoán của service khác hẳn dù không ai báo đổi model. Bạn điều tra thế nào?

Làm theo thứ tự bằng chứng, không đoán. Một: service đang phục vụ model nào? Xem log khởi động và trường `model_version` trong
response. Hai: so với trạng thái registry (model nào đang được duyệt, version nào mới đăng ký hay mới đổi alias gần đây, ai đổi
và khi nào). Ba: nếu hai thứ lệch nhau, tìm trong mã và cấu hình đúng điểm quyết định "nạp model nào", và hỏi vì sao cùng một
mã cho kết quả khác nhau ở hai thời điểm. Bốn: nếu khớp nhau, chuyển sang nghi dữ liệu đầu vào hoặc feature (module 10). Sau khi
khắc phục, thêm phát hiện sớm: alert so phân phối dự đoán 1 giờ với 7 ngày, vì alert chỉ nhìn tỉ lệ lỗi và latency sẽ không thấy
gì khi HTTP vẫn 200, và viết test hồi quy cho tình huống vừa xảy ra.

## Thiết kế cổng promotion cho model ETA: bạn kiểm những gì?

MAE tổng cải thiện tối thiểu một ngưỡng (trên cùng tập đánh giá với champion); không slice quan trọng nào xấu đi quá dung sai
(sân bay, đêm, chuyến dài), bỏ slice quá nhỏ vì nhiễu và coi slice thiếu là trượt; latency p95 trong SLO và không quá k lần
champion; lineage sạch; số đo hợp lệ (không NaN). Hàm quyết định thuần có test ca biên; lớp bọc ghi `promotion.decision` và lý
do lên version. Chính sách có người duyệt cho thay đổi lớn và ngoại lệ có hạn.

## Model mới tốt hơn 10% MAE tổng nhưng tệ hơn 18% ở sân bay. Bạn promote không?

Theo chính sách hiện hành: không, và ghi lý do. Nhưng đây cũng là câu hỏi về chính sách: sân bay chiếm bao nhiêu chuyến và
doanh thu, khách ở đó nhạy với sai số tới mức nào? Nếu thực sự không quan trọng thì sửa chính sách (hạ dung sai của slice
này) bằng một quyết định có người ký, không phải bỏ qua cổng. Phương án trung gian: promote cho các vùng khác, giữ champion
cũ cho sân bay (routing theo slice), nếu hệ thống cho phép.

## Bạn xử lý thế nào khi nhãn về muộn thì không so được champion và challenger ngay?

Cổng offline dùng tập đánh giá giữ lại có nhãn đủ, cho quyết định ban đầu. Sau promote chạy hậu kiểm: shadow hoặc canary với
so sánh phân phối dự đoán ngay lập tức, và so MAE khi nhãn về. Rollback tự động khi lệch quá ngưỡng. Với ETA, nhãn (thời lượng
thật) về sau vài chục phút, nên cửa sổ rủi ro ngắn; với bài toán nhãn về sau vài tuần, phụ thuộc nhiều hơn vào chỉ số thay thế
và mức độ thận trọng khi promote.

## Vì sao chọn MLflow thay vì Weights & Biases (hoặc ngược lại)?

Bắt đầu từ ràng buộc: dữ liệu có được rời mạng không, ai vận hành, ngân sách, cần registry không. MLflow tự host: miễn phí,
kiểm soát dữ liệu, registry tích hợp, đổi lại phải vận hành và UI cơ bản hơn. W&B: so sánh run và sweep rất tốt, cộng tác, không
phải vận hành, đổi lại chi phí theo người và dữ liệu ra ngoài. Tôi chấp nhận mất UI đẹp để giữ dữ liệu trong mạng nội bộ; ở nhóm
nghiên cứu DL phân tán, tôi chọn ngược lại. Quan trọng hơn: giữ tag lineage, tên metric và định dạng model chuẩn để đổi công cụ
không phải làm lại.

## Một người cắm artifact lên MinIO nhưng `load_model` treo mãi. Nguyên nhân có thể là gì?

Client tải artifact trực tiếp qua URL presigned mà server tạo, URL trỏ tới tên miền nội bộ của object storage (ví dụ
`minio:9000`) mà client không phân giải được; các lần thử lại làm nó có vẻ như treo. Cách xử lý: tắt tải trực tiếp để client
đi qua proxy của server (`MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false`), hoặc cấu hình endpoint công khai của object storage.
Bài học chung: lỗi mạng giữa nhiều thành phần thường hiện thành "treo", nên đặt timeout ngắn và xem log của thành phần ở giữa.

## Model card nên có gì, và làm sao để nó không thành tài liệu chết?

Mục đích và ngoài phạm vi, dữ liệu huấn luyện (phiên bản, giai đoạn), hiệu năng theo slice (kể cả chỗ tệ nhất), hạn chế đã biết,
lineage (run, commit). Sinh từ dữ liệu của run, kiểm bằng linter trong CI, đính vào version. Phần hạn chế bắt buộc có, vì mọi
model đều có hạn chế và ép viết là cách rẻ nhất để buộc đội nghĩ về nó.

## Thiết kế hệ thống: bốn đội ML dùng chung một registry. Bạn thiết kế gì?

Một MLflow server sau reverse proxy có SSO, Postgres và object storage có backup nhất quán, tên model có tiền tố đội, tag lineage
bắt buộc. Quyền promote tách khỏi quyền train: chỉ tài khoản CI sau cổng promotion mới đặt `champion`, nên bằng chứng "ai duyệt,
dựa trên số liệu nào" nằm ở tag quyết định. Cô lập đội dữ liệu nhạy cảm ở prefix object storage và proxy; trung thực rằng MLflow
OSS không phân quyền theo model đủ mịn. Vận hành: RPO/RTO bằng số, diễn tập khôi phục, retention có ngoại lệ cho kiểm toán,
điều kiện thoát sang dịch vụ quản lý đo được.

## Server registry chết lúc 9 giờ sáng. Điều gì xảy ra với các service production?

Phụ thuộc thiết kế. Service đã nạp model vẫn phục vụ tốt nếu nó giữ model trong bộ nhớ và `refresh` lỗi không làm mất model.
Service khởi động mới sẽ không lên được nếu nạp model ở bước start; giảm nhẹ bằng cache model cục bộ hoặc đóng gói bản ghim vào
image cho đường khởi động khẩn cấp (đánh đổi: phải có quy trình giữ bản ghim đúng). Không promote hay rollback được trong lúc
đó, nên registry là hạ tầng cần SLO và backup, không phải công cụ phụ.

## Khi nào bạn ghim cứng số version trong cấu hình triển khai thay vì dùng alias?

Khi cần audit và tái lập tuyệt đối: GitOps, đổi model là một commit (version = một dòng trong manifest), có review và lịch sử.
Đổi lại mất tính tức thì và mỗi lần đổi model là một lần deploy. Alias hợp khi muốn đổi model không động tới service và có cổng
kiểm riêng. Dù chọn cách nào, quyền đổi (commit hay đổi alias) phải đi qua cổng promotion và để lại bản ghi.
