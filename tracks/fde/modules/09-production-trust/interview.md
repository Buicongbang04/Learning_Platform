# Câu hỏi phỏng vấn: chứng minh hệ thống không hỏng, không "bịa"

## Khách hỏi "trợ lý của các anh chính xác bao nhiêu phần trăm?". Bạn trả lời thế nào?

Không đưa một con số trước khi hỏi lại "chính xác" nghĩa là gì với họ: trích dẫn đúng chỗ, tìm ra điều khoản, hay dám nói
"không có"? Mỗi câu là một chỉ số riêng, và với pháp chế, câu bịa có trích dẫn trông hợp lệ nguy hiểm hơn câu "không biết".
Đề xuất một bộ eval trên tài liệu của họ, 50–200 câu do chuyên gia của họ gán nhãn (gồm câu không có đáp án), chạy trong
hạ tầng của họ. Kết quả báo bằng số tuyệt đối theo từng chỉ số, kèm giới hạn (cỡ mẫu, cách định nghĩa trùng khớp) và các
ca sai tiêu biểu, không phải một phần trăm trơn.

## Benchmark công khai cho model của bạn rất cao. Vì sao vẫn cần eval trên dữ liệu khách?

Benchmark đo model trên dữ liệu và câu hỏi của người khác. Ở khách, thứ được dùng là cả hệ thống: trích chữ (PDF scan,
bảng), cách cắt đoạn, truy hồi, prompt, model, và tài liệu với từ ngữ của ngành họ. Lỗi thường nằm ở truy hồi (đoạn đúng
không vào prompt) chứ không ở model. Chỉ eval đầu cuối trên dữ liệu khách mới thấy, và đó cũng là thứ khách có thể tự chạy
lại sau mỗi lần nâng cấp.

## Precision của trích dẫn rất thấp nhưng người dùng nói câu trả lời "khá đúng". Bạn làm gì?

Đọc tay các ca bị chấm sai trước khi kết luận. Có ba khả năng: định nghĩa trùng khớp quá chặt, nhãn thiếu, hoặc sản phẩm
trả về nhiều trích dẫn hơn cái nó thật sự dùng (vd. trả mọi đoạn đã đưa vào prompt). Trường hợp cuối là phát hiện cho đội
sản phẩm, không phải lý do để nới định nghĩa. Và "câu trả lời đúng nhưng không trích đúng chỗ" vẫn là vấn đề: người dùng
không kiểm chứng được nó.

## Bạn có nên dùng LLM-judge để chấm ở khách on-prem không?

Được, với điều kiện: judge chạy on-prem (dữ liệu không ra ngoài), thường là model không lớn hơn model chính, nên phải đo
độ khớp của judge với nhãn người trên một tập nhỏ trước khi dùng, và giữ cố định prompt của judge giữa các lần chạy. Phần
xác định được (trích dẫn chạm nhãn, canary, cụm từ chối) nên chấm bằng quy tắc; judge dành cho câu hỏi không có quy tắc
(câu trả lời có khẳng định điều không có trong tài liệu không).

## Khách nói: "đối tác gửi hợp đồng cho chúng tôi qua email, có ai lợi dụng được trợ lý không?". Bạn làm gì?

Vẽ đường đi thật: email → ai lưu → thư mục nào → connector → prompt → câu trả lời đi đâu (màn hình, email gửi ra, wiki).
Rồi red-team dọc đường đó: tài liệu bình thường kèm đoạn tấn công mang canary, nhiều kỹ thuật (ra lệnh, giả hệ thống, link
exfil, chữ ẩn, chia nhỏ), chạy lặp lại được. Báo cáo theo bối cảnh của họ (ai đưa tài liệu vào được, câu trả lời tới đâu,
máy nào ra internet), khuyến nghị hai phía, và nói thẳng rủi ro còn lại. Không hứa "đã chặn được prompt injection".

## Bộ red-team của bạn chạy ra 0/12 tấn công thành công. Bạn kết luận gì?

Không kết luận "an toàn". 12 mẫu, một lần chạy, một model, chấm bằng canary: nó không bắt được tấn công không để lại dấu,
và đổi model hay câu hỏi có thể cho kết quả khác. Kiểm thêm cơ chế: phần tấn công có vào prompt không (nếu có, hệ thống chỉ
đang may), có câu trả lời nào bị hỏng mà không lộ không. Ghi kết quả làm mốc, giữ bộ tấn công trong CI, chạy lại sau mỗi
thay đổi.

## Bạn đặt SLO thế nào khi máy chủ, mạng và Prometheus đều là của khách?

SLI phải viết được bằng tín hiệu sản phẩm tự mang theo (`/metrics`, health endpoint, log) và đo bằng hệ thống mà **cả hai
bên** đọc được, thường là Prometheus của khách. Thêm probe tổng hợp vì bộ đếm request không thấy lúc dịch vụ chết. Mục
tiêu theo phần cứng và giờ dùng của khách, không chép số SaaS. Ghi rõ trách nhiệm và loại trừ, mỗi loại trừ có bằng chứng
khi áp dụng. Thứ gì chưa đo được (vd. độ tươi dữ liệu) thì đo bằng probe và ghi thành yêu cầu sản phẩm, không cam kết suông.

## Vì sao không nên đặt SLO độ trễ bằng `histogram_quantile(0.95, …)`?

Histogram chỉ biết số mẫu trong từng bucket; `histogram_quantile` nội suy tuyến tính trong bucket chứa phân vị, nên con số
có thể lệch nhiều khi bucket rộng (4–8 s). Đặt mục tiêu ở một biên bucket ("95% câu trả lời ≤ 8 s") và tính bằng tỉ lệ
`bucket{le="8"} / count` thì chính xác. Nếu vẫn báo phân vị, nói rõ đó là ước lượng.

## IT khách hỏi: "backup của các anh có dùng được không?". Bạn chứng minh thế nào?

Bằng restore thử, không bằng "tệp có đó". Dump nhất quán khi hệ thống đang chạy (`pg_dump -Fc` trong container), sha256
cạnh tệp, rồi restore vào một database tạm cùng server và so số bản ghi với database đang chạy, không đụng database thật.
Đưa họ RPO/RTO đo được từ lần diễn tập (backup mất bao lâu, restore mất bao lâu, mất dữ liệu từ thời điểm nào). Diễn tập
lặp lại định kỳ, và bản backup ở lại trong hạ tầng của họ.

## Máy khách đĩa nhỏ, bạn phải backup và nâng cấp trong cùng cửa sổ bảo trì. Bạn lên kế hoạch thế nào?

Đo trước: dung lượng trống, kích thước database, kích thước từng thứ lần nâng cấp cần, và mức trống tối thiểu mà giám sát
của khách yêu cầu (database chạy trên cùng đĩa; hết đĩa giữa chừng là sự cố). Rồi tính: chỉ chở phần thật sự đổi (so
manifest, so image ID chứ không chỉ sha256 của tệp tar), stream thay vì chép rồi giải nén, dọn tệp tạm ngay, không đụng
thứ khách yêu cầu giữ. Không đưa dữ liệu khách ra laptop để "lấy chỗ". Kế hoạch là một bảng cộng trừ khách đọc được.

## Nâng cấp xong, người dùng đã ghi dữ liệu mới, rồi phát hiện lỗi. Rollback thế nào?

Rollback khác restore. Nếu migration của bản mới chỉ mở rộng schema (expand), bản cũ chạy được trên schema mới: đổi
artifact về bản cũ, giữ nguyên database, dữ liệu ghi sau nâng cấp còn nguyên. Restore bản backup trước nâng cấp thì mất
toàn bộ dữ liệu đó; chỉ dùng khi dữ liệu hỏng. Điều kiện để rollback nhanh: artifact cũ còn trên máy (máy air-gapped không
pull lại được), cấu hình cũ được giữ, và rollback đã diễn tập trước khi cần.

## "Điểm không quay lại" của một lần nâng cấp là gì và bạn xử lý nó thế nào với khách?

Là bước sau đó bản cũ không chạy được nữa trên dữ liệu: migration xoá hay đổi kiểu cột, chuyển định dạng lưu trữ, đổi
khoá mã hoá. Tách nó ra khỏi bản phát hành đầu (expand/contract), đưa vào một bản sau khi đã chắc không cần quay lại, ghi
rõ trong ghi chú phát hành, và để CAB của khách duyệt nó như một quyết định riêng, có backup đã restore thử làm đường lui
cuối.

## Khách muốn tự chạy acceptance test sau mỗi lần nâng cấp. Bộ test đó cần gì?

Một lệnh, một báo cáo đọc được, mỗi mục một cam kết (sẵn sàng, độ trễ, trích dẫn đúng chỗ, phân quyền), báo **đúng mục
hỏng** kèm chi tiết hành động được, các mục độc lập với nhau, ngưỡng thống nhất và ghi vào biên bản. Phân quyền kiểm cả hai
chiều (không rò rỉ và không cấp thừa). Tài khoản kiểm thử do khách cấp, báo cáo không chứa token hay nội dung tài liệu.
Và bộ test phải được thử trên hệ thống cố ý hỏng trước khi giao: bộ test chưa từng FAIL thì chưa biết nó bắt được gì.

## Sau nâng cấp, acceptance test báo PASS hết nhưng người dùng than chậm. Bạn làm gì?

Xem bộ test đo cái gì: câu hỏi lặp lại được cache của model server phục vụ nhanh hơn thực tế; mẫu đo ít; đo lúc vắng. So
với tín hiệu phía server (`quillo_ask_seconds` theo thời gian, giờ cao điểm), hỏi người dùng câu cụ thể và giờ cụ thể. Nếu
bộ test không bắt được, sửa bộ test (câu hỏi đa dạng, đo trong giờ dùng thật) trước khi sửa hệ thống, rồi ghi lại mốc mới.
