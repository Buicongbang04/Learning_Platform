# Câu hỏi phỏng vấn: FDE là gì

## Forward Deployed Engineer là gì? Khác Software Engineer sản phẩm ở đâu?

FDE là kỹ sư phần mềm làm việc ở phía khách: đưa sản phẩm của công ty vào hạ tầng, dữ liệu và quy trình của **một**
khách cụ thể và chịu trách nhiệm tới khi nó tạo ra kết quả ở đó. Palantir tóm khác biệt bằng hai cụm: kỹ sư sản phẩm
(Dev) tập trung "một năng lực, nhiều khách", FDE (Delta) "một khách, nhiều năng lực".

Hệ quả thực tế: FDE viết code chạy trên môi trường không do mình kiểm soát (proxy, không root, OS cũ), có người dùng ngồi
ngay cạnh, và thường phải tự quyết nhiều thứ nhỏ mà ở đội sản phẩm có người khác quyết (scope, thứ tự, giao tiếp). Kỹ
sư sản phẩm tối ưu cho mọi khách; FDE tối ưu cho khách trước mặt nhưng có trách nhiệm không để sản phẩm phân mảnh, và mang
về những gì nhiều khách cùng cần.

## Kể lại nguồn gốc vai FDE. Delta và Echo ở Palantir là gì?

Palantir làm vai này nổi tiếng. Theo blog của họ, Dev phát triển các nền tảng (Foundry, Gotham), Delta (Forward Deployed
Software Engineer) triển khai nền tảng cho khách, nhúng vào đội của khách để cấu hình và mở rộng phần mềm có sẵn cho bài
toán khó của họ. Echo (Deployment Strategist) giữ phía nghiệp vụ: hiểu tổ chức của khách, chọn bài toán, quản lý quan
hệ và dẫn dự án; một dự án thường có cả Echo và Delta, ranh giới giữa hai vai không cứng.

Điều đáng nói trong phỏng vấn không phải cái tên mà là logic: sản phẩm chung + kỹ sư đặt ở chỗ có vấn đề + cặp kỹ thuật
và nghiệp vụ + vòng phản hồi về đội sản phẩm. Các công ty AI hiện nay tuyển FDE vì cùng lý do: model mạnh nhưng giá trị
chỉ đến khi có người nối nó vào dữ liệu và quy trình của khách.

## FDE khác Solutions Engineer (presales) thế nào? Khi nào hai vai chồng nhau?

SE làm việc **trước** hợp đồng: demo, POC ngắn trên dữ liệu mẫu, trả lời câu hỏi kỹ thuật và security questionnaire,
thành công đo bằng deal ký. FDE làm việc **sau** khi ký: đưa sản phẩm chạy trên hạ tầng và dữ liệu thật, đo bằng việc
khách dùng thật và mở rộng.

Chồng nhau ở hai chỗ: POC lớn trước ký (khách đòi chạy trên dữ liệu thật của họ) thường kéo FDE vào sớm; và ở công ty
nhỏ một người kiêm cả hai. Rủi ro của chồng vai là lời hứa presales ("chạy thử trong tuần đầu") trở thành ràng buộc cho
FDE mà không ai kiểm tính khả thi; cách xử lý là FDE tham gia đọc thông tin môi trường **trước** khi hứa ngày.

## FDE khác consultant thế nào? Dấu hiệu nào cho thấy một FDE đang "trôi" thành consultant?

Consultant làm đúng scope khách thuê và bàn giao; sản phẩm của họ là dự án. FDE đại diện cho một sản phẩm; thành công là
sản phẩm chạy được ở khách **và** những gì học được ở đó làm sản phẩm tốt hơn cho khách sau.

Dấu hiệu trôi: fork code riêng cho khách ngày càng lớn và không ai merge về; mọi yêu cầu của khách đều được làm, không
có won't; không có báo cáo phản hồi nào gửi về product; tính năng khách xin được làm thẳng trong nhánh của khách thay
vì sau feature flag. Cách chữa: fork tối thiểu, mỗi tuỳ biến hỏi "nhiều khách cần không", và đưa yêu cầu đã gộp về PM.

## Một tuần đầu tại khách của bạn thường trông thế nào?

Trước khi đến: xin quyền truy cập, người liên hệ IT, cửa sổ bảo trì, dữ liệu được duyệt; đọc thông tin máy như một
preflight; chốt với sponsor "chạy được" nghĩa là gì bằng con số.

Trong tuần: ngày đầu khảo sát máy không thay đổi gì và ngồi cạnh người dùng xem workflow thật; giữa tuần làm việc với IT
về change plan và rollback, diễn tập cài trên lab cùng ràng buộc, dựng bộ đánh giá từ câu hỏi thật của khách; cài trong
cửa sổ bảo trì; cuối tuần đo kết quả, demo cho sponsor, gửi status và danh sách khoảng cách. Status ngắn cuối mỗi ngày,
và chặn quá nửa ngày là báo ngay. Điểm mấu chốt khi trả lời: lịch xếp quanh ràng buộc của khách, không phải quanh việc
của mình.

## Khách nói: "Máy chủ đã sẵn sàng, có Docker rồi, anh cứ đến cài." Bạn làm gì trước khi đến?

Không tin "sẵn sàng" mà không có bằng chứng. Gửi khách một script khảo sát chỉ đọc (không cần root, không cần mạng) hoặc
danh sách lệnh để IT chạy và gửi lại output: OS và phiên bản, CPU/RAM, đĩa trống, `docker version` (phần **server**, vì
`docker --version` chỉ là client), có plugin compose không, user có quyền socket không, đường ra internet (thẳng, qua
proxy, hay không có), proxy có soi HTTPS không.

So output với yêu cầu tối thiểu của sản phẩm. Mỗi chỗ lệch thành một việc khách cần làm trước (mở rộng đĩa, cấp CA
proxy, cho phép mang bundle vào) có người và hạn, hoặc một quyết định đổi cách cài (bundle offline, chạy không compose).
Chỉ hứa ngày cài khi các chỗ lệch đã có hướng xử lý.

## Khách nói: "Sales hứa chạy thử được trong tuần đầu." Môi trường không cho phép. Bạn nói gì?

Không im lặng làm cố, cũng không đổ lỗi sales trước mặt khách. Đầu tiên làm rõ "chạy thử" nghĩa là gì với sponsor: dịch
vụ lên, hay người dùng hỏi câu thật nhận câu trả lời đúng. Sau đó đưa lựa chọn có con số: "Đĩa 8 GB không đủ cho bản
đầy đủ. Phương án A: anh Tuấn mở rộng đĩa trước thứ Hai, thứ Sáu chị Lan hỏi được 30 câu thật. Phương án B: không mở
rộng, chúng tôi chạy bản thu nhỏ với 50 tài liệu để chứng minh luồng, bản đầy đủ lùi sang tuần 2."

Báo tin này **sớm**, bằng văn bản, kèm điều khách cần làm. Nội bộ thì báo sales và quản lý để lần sau đọc môi trường
trước khi hứa.

## Ba khách cùng xin một tính năng. Bạn là FDE ở một khách. Bạn làm gì?

Không tự làm tính năng chung trong nhánh của khách mình. Gom bằng chứng: khách nào cần, cần để làm gì (workflow thật,
không phải giải pháp khách tự nghĩ), workaround hiện tại tốn gì, mức khẩn cấp. Gửi PM một yêu cầu đã gộp thay vì ba
ticket rời.

Nếu khách mình cần ngay cho pilot: làm phiên bản tối thiểu sau feature flag hoặc ngoài lõi (script, connector), nói rõ
với khách đây là giải pháp tạm và lộ trình của tính năng chung do product quyết. Như vậy khách không bị chặn và sản phẩm
không phân mảnh.

## Khách hỏi: "Làm sao tôi biết trợ lý AI không bịa trước khi mở cho 40 người dùng?" Bạn trả lời thế nào?

Đây là câu hỏi cần bằng chứng, không cần thuyết phục. Đề xuất: khách (người dùng chuyên môn) viết 30–50 câu hỏi thật kèm
tài liệu và đáp án đúng; chạy bộ eval trên chính tài liệu của khách, đo tỉ lệ trả lời đúng, tỉ lệ trích dẫn đúng đoạn
gốc, tỉ lệ từ chối khi tài liệu không có câu trả lời; thống nhất ngưỡng nghiệm thu **trước** khi chạy. Kết quả trình bày
cả ca sai, kèm cách giảm rủi ro (bắt buộc trích dẫn, từ chối khi không đủ căn cứ, kênh báo câu trả lời sai).

Không hứa "không bao giờ bịa". Hứa một con số đo được trên dữ liệu của họ và cách giám sát sau khi mở rộng (module 09).

## Bạn sẽ chuẩn bị lab thế nào để tái hiện lỗi của một khách mà bạn không truy cập được máy?

Dựng môi trường giống máy khách ở các điểm quan trọng: cùng OS và phiên bản, cùng runtime, cùng ràng buộc mạng (không
egress, chỉ qua proxy, proxy soi HTTPS với CA riêng), cùng quyền (không sudo), cùng giới hạn đĩa. Trong track này đó là
VM QEMU/KVM từ golden image theo hồ sơ khách, overlay mới mỗi lần để luôn bắt đầu từ trạng thái sạch.

Quy trình: đọc output/log khách gửi, lập giả thuyết, tái hiện ở lab với đúng ràng buộc đó, sửa và kiểm ở lab, rồi gửi
khách bản sửa kèm lệnh xác minh. Nếu không tái hiện được, ràng buộc của lab đang khác máy khách ở đâu đó; đó là thông
tin cần hỏi thêm.

## Vì sao một công ty AI cần FDE nếu sản phẩm đã có API và tài liệu tốt?

Vì phần khó của triển khai AI doanh nghiệp nằm ngoài API: dữ liệu nằm ở hệ thống cũ và định dạng bẩn, quyền truy cập theo
phòng ban, yêu cầu bảo mật và data residency, quy trình làm việc mà model phải vừa vào, và câu hỏi "có đáng tiền không".
Các bài phân tích (a16z, The Pragmatic Engineer) mô tả FDE là cách công ty AI đổi một phần biên lợi nhuận lấy việc khách
thật sự dùng và gắn bó, đồng thời lấy về dữ liệu hiện trường để cải tiến sản phẩm.

Câu trả lời tốt có cả mặt trái: FDE đắt, không scale như self-serve, và nếu không có vòng phản hồi về sản phẩm thì công
ty biến thành công ty dịch vụ. Nên FDE đáng giá khi mỗi khách đủ lớn và bài học từ khách quay về sản phẩm.

## Kể một lần bạn phải làm việc với yêu cầu mơ hồ. Bạn đã làm gì?

Câu hành vi; trả lời theo STAR nhưng nhấn vào **cách làm rõ** chứ không chỉ kết quả. Cấu trúc tốt: yêu cầu ban đầu là gì
và mơ hồ ở đâu; bạn hỏi ai, hỏi gì (câu hỏi mở về mục tiêu và quyết định, không phải "anh muốn tính năng gì"); bạn quan
sát workflow thật hay dữ liệu thật thế nào; bạn đề xuất gì trước (bản nhỏ nhất kiểm được giả định); kết quả có số; điều
bạn làm khác nếu làm lại.

Với người chuyển từ DA/DS, chất liệu tốt là một lần câu hỏi của stakeholder ("vì sao doanh số giảm") hoá ra cần định
nghĩa lại chỉ số trước khi phân tích. Tránh câu chuyện mà bạn chỉ làm đúng điều được bảo.

## Bạn chuẩn bị cho vòng phỏng vấn FDE thế nào? Vòng nào hay bị coi nhẹ?

Các dạng vòng hay gặp: coding (DSA), system design có ràng buộc của khách, decomposition (chia bài toán mơ hồ thành phần
làm được, nói to giả định), nhập vai với khách, take-home hoặc trình bày dự án, và hành vi. Chuẩn bị: DSA đều đặn mỗi tuần
từ sớm; system design luyện với ràng buộc on-prem, air-gapped, phân quyền; decomposition luyện bằng cách nói to khi chia
việc; một dự án thật cài được trên môi trường lạ để làm bằng chứng.

Vòng hay bị coi nhẹ là coding: người hướng tới FDE thường nghĩ "vai làm với khách" nên bỏ DSA, trong khi nhiều quy trình
mở bằng vòng này và loại sớm. Vòng thứ hai hay bị coi nhẹ là nhập vai: biết kỹ thuật nhưng không nói "không" được, không
báo được tin xấu.

## Khi nào một yêu cầu của khách nên bị từ chối dù bạn làm được?

Khi làm nó gây hại lớn hơn lợi: tạo fork không duy trì được; vi phạm chính sách bảo mật hay dữ liệu (đưa dữ liệu khách ra
ngoài để "debug cho nhanh", tắt kiểm chứng chỉ `verify=False` để qua proxy); đẩy rủi ro sang người khác (sửa trực tiếp
trên production ngoài cửa sổ bảo trì); hay ăn vào thời gian của mục tiêu đo được đã chốt mà không ai quyết đánh đổi.

Từ chối kèm lý do và phương án: "Tắt kiểm chứng chỉ thì qua được hôm nay nhưng mọi kết nối sẽ không còn được bảo vệ, và
đội an ninh của anh sẽ chặn khi audit. Cách đúng là thêm CA của proxy vào trust store; tôi cần file CA và 30 phút trong
cửa sổ tối thứ Năm." Từ chối tốt luôn đưa khách một đường đi tiếp.
