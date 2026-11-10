# Câu hỏi phỏng vấn: nền tảng ML nhiều đội và bảo mật model

## "Golden path" là gì, và làm sao để các đội thật sự dùng nó?

Là con đường đã lát sẵn từ dự án mới tới production mà đi theo thì mọi quy định (tag chi phí, model card, quét, ký, SLO) tự đúng. Các đội
dùng nó khi nó **nhanh hơn** tự làm, không phải khi bị bắt: template sinh dự án chạy được trong 10 phút, CI có sẵn, deploy canary một lệnh.
Đo mức áp dụng (% model production đi qua cổng chung) và thời gian từ dự án mới tới production. Đội không theo được thì có ngoại lệ có hạn
và điều kiện thoát, không phải con đường thứ hai vĩnh viễn.

## Vì sao chọn Copier thay vì Cookiecutter cho template dự án?

Copier lưu câu trả lời (`.copier-answers.yml`) và có `copier update`: khi template đổi (thêm bước quét model vào CI), mọi dự án đã sinh kéo
thay đổi về, xung đột giải như merge. Cookiecutter chỉ sinh một lần, sau đó template và dự án trôi xa nhau. Thêm vào đó Copier có validator
và câu hỏi bắt buộc không default, nên chế độ không hỏi (`--defaults`) thất bại thay vì điền giá trị rác. Lưu ý bảo mật: template có `_tasks`
chạy lệnh shell trên máy người sinh dự án, Copier đòi `--trust`; template nền tảng nên chạy được không cần trust.

## Thiết kế quy ước registry cho 5 đội dùng chung MLflow. Bạn ép quy ước thế nào?

Tên có không gian tên theo đội (`<team>-<model>`), tag bắt buộc `owner`, `team`, `cost_center`, `data_classification`, model card có các
phần bắt buộc. Ép bằng ba lớp: cổng đăng ký kiểm luật và từ chối kèm lý do (self-service); quyền trên registry để chỉ service account của
cổng tạo được version (MLflow basic-auth với quyền theo registered model, hoặc Unity Catalog mỗi đội một schema); audit hằng đêm quét mọi
version để bắt thứ lọt qua đường vòng. Cổng mà registry vẫn nhận ghi trực tiếp từ mọi người thì chỉ là gợi ý.

## Cụm GPU dùng chung chạy 30% công suất. Bạn phân bổ chi phí cho các đội thế nào?

Gắn chi phí trực tiếp theo request (không theo mức dùng thật, vì scheduler giữ chỗ theo request) cho đội qua namespace và cho model qua nhãn
pod. 70% còn lại là idle, tính theo từng loại tài nguyên, và phải hiện ra: chia cho các đội theo một chính sách công khai (theo chi phí trực
tiếp, theo GPU đã xin) hoặc để thành chi phí của đội nền tảng để đội này có động lực bin-pack và autoscale. Phần không gắn được nhãn là một
dòng `UNALLOCATED` riêng. Showback trước; chargeback khi phần chưa gắn nhãn dưới khoảng 5%.

## Ban lãnh đạo muốn giảm 25% chi phí hạ tầng ML trong hai quý. Bạn làm gì trước?

Đo trước khi cắt: showback theo đội và model, tỉ lệ dùng trên request, chi phí trên 1 000 dự đoán. Rồi đòn bẩy theo thứ tự rủi ro tăng dần:
rightsizing request theo p95 dùng thật; scale-to-zero và autoscale cho model ít lưu lượng (KEDA); hàng đợi cho GPU huấn luyện thay vì giữ
node (Kueue); gom node khi đã bin-pack; cuối cùng mới đổi loại máy hay mua cam kết. Giữ ngân sách headroom riêng cho đội có mùa cao điểm để
không cắt nhầm. Báo kết quả bằng chỉ số đơn vị, không chỉ tổng tiền.

## Build vs buy: khi nào bạn chọn SageMaker hay Vertex AI thay vì tự vận hành Kubeflow/KServe?

Khi đội nền tảng nhỏ, tải theo đợt, đã ở cloud đó, và nền tảng ML không phải lợi thế cạnh tranh. TCO phải có chi phí người: 3 kỹ sư vận
hành có thể tốn ngang hoá đơn hạ tầng; managed tốn phí cộng thêm trên compute nhưng giảm vận hành và tính theo giờ dùng. Tự vận hành hợp khi
mức dùng cao và ổn định, có ràng buộc đặc thù, và có đủ người trực. Thường là lai: managed cho huấn luyện và notebook, tự giữ serving và
lớp quy ước. Giảm lock-in bằng định dạng mở, container chuẩn, lớp mỏng nội bộ trước SDK của hãng.

## Vì sao nạp một tệp pickle lại nguy hiểm? Giải thích cơ chế.

Pickle là chương trình cho máy ảo của module `pickle`, không phải dữ liệu thuần. Opcode `GLOBAL` nạp một hàm bất kỳ theo tên module và tên
hàm (`os.system`, `builtins.exec`), `REDUCE` gọi nó với tham số trong tệp; `__reduce__` cho phép mọi đối tượng tự mô tả cách dựng lại bằng
một lời gọi hàm. Vì vậy `pickle.load` là chạy code của người tạo tệp. `joblib.load`, `torch.load(weights_only=False)`, `pandas.read_pickle`
đều qua pickle. Cách đúng: định dạng không chứa code (safetensors, ONNX, định dạng gốc của LightGBM), và không bao giờ nạp pickle lạ ngoài
sandbox.

## Đã có modelscan rồi, sao còn cần allowlist định dạng?

Vì máy quét có giới hạn cấu trúc. modelscan dò theo danh sách module/hàm nguy hiểm, nên payload dùng một hàm ngoài danh sách (vd. ghi tệp
qua `pathlib`) qua được. Nó chọn scanner theo đuôi tệp: pickle đặt tên `model.safetensors` bị coi là "không có gì để quét", đuôi `.bin` bị
bỏ qua. Allowlist theo nội dung (nhận diện bằng byte, chỉ nhận định dạng không có code) là lớp chính; máy quét là lớp phụ cho đường chuyển
tiếp. Khi nhận pickle, đòi bằng chứng máy quét đã đọc đúng tệp đó, và fail closed khi máy quét lỗi.

## Ký model giải quyết vấn đề gì, và không giải quyết vấn đề gì?

Chữ ký chứng minh thư mục model giống từng byte với thứ mà người giữ khoá (pipeline CI) đã ký: phát hiện sửa, thêm, xoá tệp sau khi ký. Nó
không chứng minh model vô hại: pipeline bị chiếm (dependency độc, model gốc độc) vẫn ký một model chứa payload; vì vậy cổng deploy gộp
verify và quét. Nó cũng chỉ bảo vệ những byte thật sự được verify: verify bản trong registry rồi nạp bản sao trên node là không có tác dụng.
Và chữ ký chỉ mạnh bằng việc quản lý khoá: khoá trong KMS của CI, cổng chỉ có khoá công khai, có quy trình thu hồi và xoay khoá.

## Sigstore keyless khác ký bằng khoá riêng thế nào? Khi nào chọn cái nào?

Keyless: người ký đăng nhập OIDC (tài khoản, hoặc danh tính workflow CI), Fulcio cấp chứng chỉ ngắn hạn gắn danh tính đó, chữ ký ghi vào log
minh bạch Rekor; người verify kiểm **danh tính** ("ký bởi workflow `train.yml` của repo X") chứ không giữ khoá công khai. Không có khoá dài
hạn để lộ, và mọi chữ ký đều tra được trong log công khai. Đổi lại cần mạng tới Sigstore (hoặc tự dựng instance riêng) và danh tính bị ghi
công khai. Khoá riêng hợp với môi trường offline hay đã có KMS/PKI nội bộ; keyless hợp với dự án công khai và CI trên GitHub Actions.

## Sự cố: model đã ký, log cổng deploy ghi "signature OK", nhưng một node phục vụ model khác. Bạn điều tra thế nào?

Tin log là thật và hỏi "verify chạy trên bản nào". So hash của tệp mà node đang nạp với bản trong registry: khác thì liệt kê mọi bản sao
từ registry tới tiến trình serving (thư mục tải, cache trên node, volume) và xem bước verify chạy ở bản nào. Lỗi hay gặp: verify bản nguồn
rồi dùng bản cache cũ mà không kiểm lại (TOCTOU). Giảm thiểu: rút node đó khỏi lưu lượng, xoá cache, deploy lại. Sửa gốc: verify đúng bản
sẽ nạp ở mọi lần (init container trước serving), thư mục model mount chỉ đọc, quyền vào node có log, đối soát định kỳ hash model đang
phục vụ trên từng node với manifest đã ký. Coi đây là sự cố bảo mật: ai đã sửa tệp, khi nào.

## SBOM cho một service ML gồm gì, và bạn dùng nó vào việc gì?

SBOM phần mềm (CycloneDX hoặc SPDX) liệt kê mọi gói và phiên bản trong image serving, kể cả gói gián tiếp; sinh từ image đã build (Syft,
`cyclonedx-py environment`), không chỉ từ requirements, vì requirements không ghim cho thành phần không có phiên bản. Dùng khi có CVE (tra
service nào đang chạy bản bị ảnh hưởng qua Dependency-Track hay Grype) và khi phát hành (diff SBOM bản mới với bản đang chạy, gói lạ xuất hiện
là dấu hiệu cần hỏi). ML-BOM của CycloneDX thêm model gốc kèm hash, dataset và tham số: trả lời "model này làm từ gì".

## Đội search muốn dùng một model mới ra trên Hugging Face ngay hôm nay. Bạn đặt đường đi thế nào?

Không cấm, mà cho một đường nhanh có kiểm soát: nhập model vào mirror nội bộ ghim theo revision (commit hash), chỉ nhận safetensors (từ
chối tệp `.bin`/`.pt` pickle hay code tuỳ biến cần `trust_remote_code`), quét và ghi ML-BOM khi nhập, rồi đội dùng bản mirror như mọi
artifact khác qua cổng ký và quét. Không tải thẳng từ Hub trong lúc serving khởi động. Nếu model chỉ có bản pickle: chuyển đổi sang
safetensors trong sandbox không mạng, hoặc chờ, và ghi đây là ngoại lệ có người chịu trách nhiệm.

## Thiết kế nền tảng ML cho 5 đội với 3 kỹ sư nền tảng. Bạn ưu tiên gì trong quý đầu?

Ba câu hỏi trước công cụ: ai được làm gì, model nào được phép chạy, ai trả tiền. Quý đầu làm những thứ rẻ mà mở khoá phần còn lại: quy ước
tên và tag trên registry kèm cổng và audit; nhãn chi phí bắt buộc và showback có dòng idle và `UNALLOCATED`; cổng quét và ký cho model
mới; một đội (thường là đội mới, ít nợ cũ) đi trọn golden path làm mẫu. Mua hay dùng dịch vụ managed cho phần không phải lợi thế (Kubernetes
managed, object storage), tự xây lớp mỏng (template, cổng, báo cáo). Lộ trình theo quý có chỉ số: % model qua cổng, % chi phí có chủ,
thời gian tới production cho đội mới, số model pickle còn lại.
