# Câu hỏi phỏng vấn: CI/CD cho ML

## CI cho một repo ML khác CI cho ứng dụng thường ở đâu?

Cùng phần code: lint, test, build, và chúng bắt buộc như mọi nơi. Khác ở chỗ sản phẩm của repo ML không chỉ là code mà còn là
model, được sinh ra từ code, tham số và dữ liệu. Nên có thêm một lớp (thường gọi CT, continuous training) kiểm phần đó: data test,
train mẫu, kiểm model theo slice và latency, đăng ký version, cổng promotion. Hai lớp có tần suất, chi phí và người chịu trách
nhiệm khác nhau nên tôi tách thành các workflow riêng với trigger riêng. Đổi lại phải chủ động thiết kế chỗ hai lớp giao nhau.

## "Chỗ hai lớp nối nhau" là gì và vì sao bạn nhấn mạnh nó?

Là những thứ được giao từ workflow này sang workflow kia: model từ train sang deploy, image từ CI sang CD, quyền đổi alias từ cổng
sang người triển khai. Mỗi lớp xanh riêng không chứng minh gì về thứ được giao. Tôi muốn ở chỗ nối có một định danh ổn định (version, digest, commit sha),
kiểm ở đầu nhận, và được in ở cả hai đầu (log train, log deploy, response của service). Lỗi ở chỗ nối nguy hiểm vì mọi job đều xanh và không ai có lý do nghi ngờ.

## Bạn quyết định workflow nào chạy trên PR, workflow nào theo lịch, dựa trên gì?

Dựa trên chi phí của một lần chạy và cái giá của việc phát hiện muộn. Lint, test chạy trên mọi PR đụng code vì rẻ và chặn merge.
Train mẫu (vài nghìn dòng, vài phút, CPU) chạy trên PR có đổi tham số hoặc con trỏ dữ liệu, vì lỗi cấu hình nên lộ trước merge. Train đầy
đủ chạy theo lịch hằng tuần và `workflow_dispatch`, vì đắt, và vì dữ liệu mới thường về không kèm commit. Bộ lọc `paths` liệt kê đầu vào thật của model; quên một mục
nghĩa là thay đổi đó đi qua mà không ai train lại.

## Path filter có điểm yếu nào mà bạn đã gặp hoặc sẽ cẩn thận?

Ba điểm. Một, thiếu đầu vào (quên `train.py` hay `dvc.lock`) thì đổi nó không kích hoạt gì và không có lỗi nào báo. Hai, check bắt buộc của branch
protection mà workflow bị lọc mất sẽ kẹt "đang chờ" mãi; cách xử lý là một job tổng hợp luôn chạy hoặc không đặt bắt buộc cho check có lọc. Ba, glob:
`src/*` không khớp thư mục con, `src/**` khớp; và `act` không đánh giá `paths` nên phải mô phỏng trong test hoặc thử trên GitHub thật.

## Cổng promotion nên được cài ở đâu trong pipeline và đỏ thì chuyện gì xảy ra?

Là một job riêng sau train, đọc số đo của challenger và champion rồi **thoát khác 0** khi không đạt. Chính mã thoát làm nó có
tác dụng, vì job `deploy` khai `needs` vào nó nên không chạy. Cổng chỉ in cảnh báo mà thoát 0 là lỗi nguy hiểm nhất. Tôi cũng tách
hàm quyết định thuần (test được bằng ca biên, không cần runner) khỏi lớp đọc tệp, coi giá trị không hữu hạn là không đạt, ghi lý do lên version, và nhớ
rằng cổng là hàng rào chứ không phải bằng chứng: tập đánh giá nhỏ hay thử lại nhiều lần đều làm nó yếu đi.

## CD cho model khác CD cho ứng dụng thế nào, và việc gì kích hoạt deploy?

Ứng dụng đổi khi code đổi; model có thể đổi mà không có commit nào, vì đổi alias `champion` trong registry. Có hai cách: service tự poll alias và nạp lại (nhanh,
không có điểm duyệt), hoặc đổi alias phát sự kiện để một workflow `cd` chạy deploy có smoke test, canary và môi trường `production` có reviewer (có audit, thêm một
pipeline). Tôi chọn cách thứ hai khi thay đổi có rủi ro cao. Dù cách nào cũng cần: ai được đổi alias, rollback bằng cách đổi alias về version trước, và
kiểm sau deploy rằng model đang phục vụ đúng là version vừa duyệt.

## Secrets được xử lý thế nào để không lộ vào log?

Truyền qua `env:` của đúng bước cần, không nhúng vào dòng lệnh, và không bao giờ in ra. Runner che giá trị khi nó xuất hiện nguyên văn, nhưng một bản cắt, đảo hay base64
thì lọt, nên che log chỉ là lưới đỡ. Tôi kiểm bằng cách đọc log của lần chạy thật (và có test grep log, như bài tập). Workflow từ fork không nhận secrets; tôi không
"sửa" việc đó bằng `pull_request_target` rồi checkout mã của PR. Và thiếu secret thì bước deploy phải đỏ chứ không âm thầm bỏ qua.

## OIDC giải quyết vấn đề gì so với lưu khoá cloud thành secret?

Khoá dài hạn trong secrets không hết hạn, khó xoay vòng, và lộ một lần là dùng được từ bất kỳ đâu. Với OIDC, job xin token ngắn hạn từ GitHub (cần `id-token: write`) và cloud
được cấu hình tin GitHub theo điều kiện (repo, nhánh, environment) để đổi lấy credential tạm. Không có khoá nào để lộ, quyền gắn với danh tính workflow, cloud audit được. Phải trả
một lần cấu hình quan hệ tin cậy, và nếu điều kiện cấu hình lỏng (mọi nhánh) thì lợi ích giảm.

## Cache và artifact khác nhau thế nào? Chỗ nào dùng cái nào?

Cache là tối ưu best-effort theo khoá (thường hash lockfile): có thể mất, có giới hạn dung lượng; chỉ dùng cho thứ tái tạo được như dependency, và pipeline phải đúng khi cache trống.
Artifact là thứ job này đưa ra để job sau nhận, có tên và thời hạn giữ. Model và dữ liệu thì tôi muốn đi qua registry hoặc DVC remote có version và lineage hơn là artifact của CI, vì
chúng sống lâu hơn pipeline và cần truy ngược. Không bao giờ để đúng/sai của một kết quả phụ thuộc vào cache.

## `act` dùng để làm gì và bạn không tin nó ở điểm nào?

Dùng để lặp nhanh: chạy workflow trên máy trong vài giây, bắt lỗi cấu trúc và lỗi mã thoát trước khi commit. Tôi không tin nó ở những chỗ khác runner thật: image khác, các job chung một thư mục
(`--bind`) nên lỗi quên đưa artifact ra không lộ, `paths` và `branches` không được đánh giá như máy chủ, không có OIDC hay environment có reviewer. Quy tắc của tôi: `act` xanh nghĩa là
"cấu trúc và mã thoát đúng", không nghĩa là "chạy được trên GitHub"; một lần chạy thật vẫn cần.

## Sự cố: pipeline xanh nhưng model được deploy không phải model vừa train. Bạn điều tra thế nào?

Không đoán, đi theo bằng chứng. Một: lấy định danh model ở hai đầu của cùng một lần chạy (dòng log của job train, thứ đang nằm ở môi trường đích) và xác nhận chúng khác nhau. Hai: dựng lại bằng
`act` hoặc chạy lại với các điều kiện khác nhau để xem lỗi lúc đúng lúc sai phụ thuộc vào cái gì. Ba: đọc đúng bước quyết định "job deploy nhận thứ gì, bằng
cách nào" thay vì đọc cả pipeline. Sau khi sửa, tôi thêm hai thứ: bước kiểm ở đầu ra (so định danh thứ vừa deploy với thứ vừa train, đỏ nếu lệch) và một test hồi quy tái hiện đúng điều kiện đã gây lỗi. Và hỏi thêm: vì sao
không có tín hiệu nào đỏ, tức lớp giám sát nào còn thiếu.

## Bạn chọn GitHub Actions, GitLab CI, Jenkins hay CML cho một đội ML? Vì sao?

Bắt đầu từ ràng buộc: code ở đâu, đã có runner và quyền truy cập nào, dữ liệu có được rời mạng không, cần GPU không. Code đã ở GitHub thì GitHub Actions (runner tự host cho GPU và dữ liệu nội bộ);
công ty đã dùng GitLab với runner riêng thì GitLab CI, các khái niệm chuyển gần như một-một; Jenkins khi đã có sẵn và cần mạng kín, chấp nhận gánh vận hành. CML không phải hệ CI mà là lớp
bổ sung để đăng bảng, biểu đồ so sánh model vào PR. Điều tôi chấp nhận mất khi chọn công cụ sẵn có: vài tính năng "mới" hơn. Điều tôi không làm: chuyển cả hệ thống chỉ vì tên công cụ.

## Làm sao bạn xử lý test ML bị flaky (lúc xanh lúc đỏ) trong CI?

Phân biệt hai lớp. Test của code (hàm tiền xử lý, schema, hợp đồng đầu vào đầu ra) phải xác định: seed cố định, dữ liệu fixture nhỏ, không phụ thuộc thời gian hay mạng; flaky ở đây
là bug. Test trên chất lượng model có nhiễu thật nên không viết dạng `assert mae == 123.4`; dùng ngưỡng có biên, nhiều seed, hoặc chuyển nó thành cổng promotion ở lớp CT thay vì unit test.
Tôi không "retry cho tới khi xanh" vì đó là che lỗi, và chỉ cách ly test flaky có ghi chú, người chịu trách nhiệm và hạn sửa.

## Thiết kế hệ thống: đội 5 người có dịch vụ ETA, train đầy đủ cần GPU 40 phút, dữ liệu mới về hằng tháng. Bạn thiết kế pipeline CI/CD/CT như thế nào?

Ba lớp. CI trên mọi PR đụng code: lint, test, build image, chặn merge, vài phút. CT: train mẫu trên CPU khi PR đổi `params.yaml`, `data.dvc` hay `train.py` (chặn merge, 4 đến 6 phút); train đầy
đủ trên runner tự host có GPU theo lịch hằng tuần và `workflow_dispatch`, kết thúc bằng cổng promotion: trượt thì dừng và ghi lý do lên version, đạt thì đăng ký version và đổi alias.
CD kích hoạt khi alias đổi, chạy smoke test và canary, cần reviewer cho môi trường production; rollback là đổi alias về version trước. Chỗ nối: định danh (digest, commit sha, `model_id`) kiểm ở cả hai đầu,
`concurrency` để hai lần đổi alias không chồng nhau. Bảo mật: OIDC, `permissions` tối thiểu, fork không nhận secrets và không chạy trên runner tự host. Cái giá tôi nêu ra: runner GPU là bề mặt tấn công và là
chi phí lớn nhất, nên có `timeout-minutes` và cảnh báo khi lịch không chạy.

## Vì sao bạn ghim version công cụ trong CI và ghim action theo commit sha?

"Xanh trên máy tôi" chỉ so được với "xanh trên CI" khi công cụ cùng phiên bản (ruff, pytest, uv, Python), nên tôi ghim chúng và dùng lockfile có hash. Action của bên thứ ba ghim theo commit sha đầy đủ vì tag và nhánh
(`@main`, `@v1`) thay đổi được: chủ action đẩy mã mới thì pipeline chạy mã mới mà không ai review, trong một pipeline có giữ secrets. Dependabot nâng version có review. Đổi lại phải duy trì bản ghim; tôi chấp nhận cái giá đó.

## Khi pipeline huấn luyện của bạn tốn quá nhiều chi phí runner, bạn cắt ở đâu trước?

Đo trước: job nào, bao nhiêu phút, bao nhiêu lần chạy mỗi tuần. Thường cắt theo thứ tự: path filter để không chạy khi đầu vào không đổi; train mẫu thay cho train đầy đủ trên PR; `concurrency` với
`cancel-in-progress` cho CI để huỷ lần chạy cũ khi có push mới (nhưng không bao giờ huỷ deploy); cache dependency theo hash lockfile; `timeout-minutes` để job treo không đốt GPU; chuyển việc nặng sang runner tự host
khi tổng chi phí SaaS vượt chi phí vận hành. Không cắt cổng promotion hay bước kiểm đầu ra: đó là tiền mua độ tin cậy.
