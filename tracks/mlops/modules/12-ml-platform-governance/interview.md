# Câu hỏi phỏng vấn: nền tảng ML, governance và chi phí

## "Tái lập được một model" nghĩa là gì, và bạn kiểm bằng cách nào?

Là từ một model trong registry, truy ngược được code, dữ liệu, cấu hình và ngẫu nhiên đã sinh ra nó, và dựng lại được cùng kết quả (hoặc giải thích được độ lệch). Tôi kiểm ở hai mức. Mức rẻ: audit tự động trên metadata của run (commit đủ 40 ký tự và cây sạch, data version là định danh nội dung chứ không phải `latest`, hash lockfile, seed), trả danh sách *thiếu gì* để sửa. Mức đắt nhưng đáng tin: dựng lại thật định kỳ trên model production rồi so dự đoán với artifact gốc. Mức đầu bắt thiếu sót; mức sau bắt thứ mà checklist không nghĩ tới.

## Sự cố: model production không tái lập được dù đội đã "log đủ mọi thứ". Bạn điều tra thế nào?

Tôi không đào theo phản xạ vào seed hay dữ liệu. (1) Tái hiện triệu chứng có số: lệch bao nhiêu, ở đâu, lặp lại được trong một lần chạy không (nếu hai lần giống nhau thì không phải ngẫu nhiên giữa các lần). (2) Liệt kê từng đầu vào mà run đã ghi và xác nhận cái nào trùng thật bằng cách so giá trị, không bằng cách tin tag. (3) Hỏi ngược lại: *điều gì quyết định kết quả mà không có trong danh sách đó*? Mọi thứ chưa được ghi đều là ứng viên. (4) So bản dựng lại với bản gốc ở từng bước trung gian để khoanh vùng bước đầu tiên lệch. (5) Sửa bằng cách ghi thứ còn thiếu vào run và dựng lại từ chính thứ đã ghi, không dựng lại từ thứ "hiện tại"; rồi thêm vào audit một kiểm tra bắt lớp lỗi này, và một job dựng lại định kỳ.

## Audit log append-only hoạt động ra sao? Nó chống được gì và không chống được gì?

Mỗi dòng chứa hash của dòng trước, nên sửa một dòng làm hỏng hash dòng đó và `prev_hash` của dòng sau; kẻ sửa phải tính lại cả phần đuôi. Nó chống sửa hay xoá giữa chừng và đổi thứ tự. Không chống: (a) cắt các dòng cuối (chuỗi còn lại vẫn hợp lệ), nên phải neo hash đầu log ở nơi khác; (b) kẻ ghi được vào hệ thống nơi neo; (c) thao tác ghi thẳng vào registry không qua ứng dụng, tức không có dòng nào. Muốn chặn (c) thì khoá quyền, log chỉ làm vi phạm lộ ra.

## Làm sao trả lời kiểm toán "ai đã đưa version 3 lên production và dựa trên số liệu nào"?

Cần ba thứ đã được ghi trước đó: audit log có người, lúc nào, alias cũ sang mới và lý do; version trỏ về `run_id` có metric và lineage; model card đã được duyệt. Truy vấn log theo `alias = champion`, `to_version = 3` cho ra danh sách (có thể nhiều người nếu model từng bị rollback rồi promote lại), mỗi dòng nối tới run và metric. Nếu một trong ba thứ không được ghi lúc đó, không có cách bù về sau; đó là lý do bài toán này thuộc thiết kế, không phải điều tra.

## Vì sao tách quyền giữa người train và người duyệt, và thực thi nó ở đâu?

Vì người train có động cơ và điểm mù: họ tin model của mình. Tách quyền chỉ có nghĩa khi **bị chặn bằng cơ chế**: CI từ chối nếu approver trùng `train_user`, alias production chỉ được ghi bởi tài khoản dịch vụ của CI. Một quy ước trong wiki không phải kiểm soát. Giá phải trả là thời gian chờ duyệt, nên tôi dùng hai người duyệt chỉ ở tầng rủi ro cao và để rollback không cần duyệt.

## Bạn thiết kế governance cho ba đội: tín dụng chịu thanh tra, gợi ý sản phẩm và nghiên cứu như thế nào?

Theo tầng rủi ro, tính từ hậu quả khi sai. Tín dụng (cao): hai người duyệt độc lập, audit tái lập chặn tự động, model card đầy đủ, retention nhiều năm gồm cả dữ liệu huấn luyện, quyền ghi alias chỉ qua CI. Gợi ý (trung bình): một approver qua pull request, drift và proxy chất lượng, rollback nhanh. Nghiên cứu (thấp): không có production, tự đăng ký staging, trần chi phí cứng. Mỗi dòng nói ai thực thi và cái giá. Một quy trình cho cả ba hoặc làm chậm nghiên cứu hoặc bỏ hở tín dụng.

## Chi phí ML nằm ở đâu? Bạn ước tính ngân sách quý tới như thế nào?

Tách train (trả theo lần chạy, ngắt được nếu có checkpoint, dùng spot) khỏi serve (trả theo giờ máy bật, bất kể có request). Với serve, tôi tính `giá × replica × giờ tính tiền` rồi trừ ra phần nhàn rỗi `× (1 - mức sử dụng)`; ở đội nhỏ phần này thường lớn nhất. Cộng các khoản hay quên: NAT, load balancer, log, lưu trữ artifact, egress, và giờ nhân công vận hành. Đòn bẩy: co về 0 (đổi bằng khởi động nguội), nhỏ máy, cam kết dài hạn (đổi bằng linh hoạt). Kết quả là một khoảng, kèm giả định giá, rồi đặt budget alarm.

## Scale-to-zero có phải lúc nào cũng nên bật không?

Không. Nó đưa tiền nhàn rỗi về gần 0 nhưng request đầu sau lúc rảnh chịu khởi động nguội (tải model, có thể hàng chục giây). Hợp với tải thưa, batch, nội bộ chịu được chờ; không hợp với API có SLO độ trễ chặt hay lưu lượng đều. Giữa hai thái cực: giữ một replica nhỏ làm nền, co phần còn lại theo tải. Quyết định dựa trên p95 yêu cầu và đồ thị lưu lượng, không dựa trên giá.

## SageMaker, Vertex AI và Azure ML khác nhau thế nào, và bạn chọn giữa chúng ra sao?

Về khái niệm chúng tương đương (registry, endpoint online, pipeline, tracking), khác ở tích hợp và cách tính tiền. Tôi chọn theo nơi dữ liệu đã nằm (egress và độ trễ), kỹ năng sẵn có của đội, và hệ sinh thái (IAM, mạng, công cụ giám sát công ty đang dùng), hiếm khi theo một tính năng đơn lẻ. Trước khi cam kết: ước tính chi phí 24 tháng gồm nhân công, thử một model thật qua cả ba nếu chênh lệch lớn, và đo chi phí rời đi.

## Khi nào tự dựng nền tảng, khi nào dùng dịch vụ cloud? Bạn bảo vệ quyết định bằng gì?

Bằng một ma trận có trọng số đặt **trước** khi chấm điểm, chi phí 24 tháng gồm nhân công, và điểm hoà vốn tính bằng số. Đội nhỏ, ít kỹ sư nền tảng, dữ liệu đã trên cloud: dịch vụ quản lý thường thắng về tốc độ và vận hành, thua về chi phí dài hạn. Khi số model và hoá đơn vượt một ngưỡng cụ thể, tự dựng hoặc lai hoà vốn. Tôi ghi **điều kiện đổi hướng có số** (số model, tiền mỗi tháng, độ trễ) và giữ định dạng mở để đường rút lui rẻ.

## Budget alarm có bảo vệ bạn khỏi hoá đơn bất ngờ không?

Không hoàn toàn. Nó chỉ báo (email hay thông báo), không dừng tài nguyên, và dữ liệu chi phí trễ hàng giờ tới ngày; một endpoint GPU quên tắt có thể đốt hàng trăm USD trước khi cảnh báo tới. Nó là một lớp trong nhiều lớp: tag chủ sở hữu và `ttl`, script dọn có dry-run, trần chi phí cứng ở môi trường thử nghiệm, thói quen "dọn trước khi ngủ", và review hằng tuần các tài nguyên tính tiền theo giờ.

## Vì sao script dọn lab chỉ động tới tài nguyên có tag của lab, và vì sao mặc định dry-run?

Dọn theo tên, theo loại hay theo vùng sẽ xoá nhầm tài nguyên của người khác trong cùng tài khoản: thiệt hại không đảo ngược được. Tag do chính lab đặt lúc tạo là bằng chứng sở hữu mạnh nhất; thứ trông giống lab nhưng thiếu tag chỉ được cảnh báo. Dry-run mặc định khiến người chạy lúc mệt phải đọc kế hoạch trước; lỗi một bước không dừng cả script (dừng giữa chừng có thể bỏ lại thứ đắt nhất) và thoát mã khác 0 để biết còn việc.

## Thiết kế hệ thống: một nền tảng ML dùng chung cho 4 đội, 12 model production, hai kỹ sư nền tảng. Bạn dựng gì trước?

Theo thứ tự rủi ro, không theo công nghệ. Trước hết: tracking và registry chung có backend Postgres, lineage đầy đủ ở mọi run (commit, data version, lockfile, seed), và audit tái lập tự động làm cổng. Thứ hai: quyền theo prefix tên model và alias production chỉ ghi qua CI, audit log hash chain có anchor. Thứ ba: giám sát chi phí (tag, budget theo đội, báo cáo hằng tuần các tài nguyên chạy theo giờ). Sau đó mới tới tự động hoá pipeline và serving. Hai người không duyệt tay được 12 model, nên mọi kiểm soát phải là kiểm tra tự động; thứ cần người thì dành cho tầng rủi ro cao. Đo bằng số lần break-glass và thời gian chờ duyệt.

## Phần data engineering nào bạn dùng lại trong ML, và ML thêm gì?

Batch idempotent và backfill cho bảng training, Spark khi dữ liệu vượt một máy, Kafka hay Flink cho feature thời gian thực, và governance dữ liệu (quyền, lineage, PII). ML thêm hai yêu cầu: bảng training phải tái lập theo thời điểm (không rò tương lai), và phiên bản dữ liệu phải đi cùng từng run để audit truy ngược được. Tôi không dạy lại Spark hay Kafka ở đây mà trỏ về module DE gốc.
