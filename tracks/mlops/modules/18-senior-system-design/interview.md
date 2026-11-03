# Câu hỏi phỏng vấn: ML system design và dẫn dắt vận hành

## Service ML của bạn nên có những SLI nào, và vì sao không đủ với khả dụng và độ trễ?

Bốn loại: khả dụng, độ trễ, chất lượng, freshness. Service ML có thể trả 200 trong 20 ms mà vẫn hỏng theo hai cách mà hai SLI đầu không
thấy: dự đoán sai (model cũ, concept drift, lỗi tiền xử lý) và dự đoán dựa trên feature cũ (job materialize dừng). Chất lượng đo bằng tỉ lệ
dự đoán có sai số trong ngưỡng trên các dự đoán đã có nhãn, cửa sổ dài vì nhãn về chậm; freshness đo tuổi feature của từng yêu cầu hoặc tỉ
lệ thời gian feature không cũ quá ngưỡng. Khả dụng và độ trễ đo ở điểm gần người dùng nhất (gateway, load balancer, client), không ở hàm
`predict`.

## Error budget là gì, và bạn dùng nó để quyết định gì?

Là phần không hoàn hảo được phép: `(1 - SLO) x cửa sổ`, ví dụ 99.5% trong 30 ngày là 216 phút. Nó biến tranh luận "nhanh hay ổn định" thành
một con số chung giữa sản phẩm và kỹ thuật. Còn nhiều budget thì được ra tính năng nhanh, thử model rẻ hơn có canary; budget dưới ngưỡng
(vd. 25%) thì đóng băng thay đổi rủi ro và ưu tiên độ tin cậy, ngoại lệ phải có người ký và có hạn. SLO không có chính sách đi kèm chỉ là
con số trang trí.

## Giải thích alert burn rate hai cửa sổ. Với SLO chất lượng bạn chọn cửa sổ thế nào?

Burn rate là tỉ lệ sự kiện xấu chia `(1 - SLO)`; burn 1 là hết budget đúng cuối cửa sổ. Alert khi burn vượt ngưỡng ở cả cửa sổ dài (đủ nặng,
không phải spike) và cửa sổ ngắn khoảng 1/12 (còn đang xảy ra, nên alert tự tắt nhanh sau khi sửa). Với khả dụng: 14.4 trên 1h và 5m để page.
Với chất lượng, nhãn về theo lô và thưa nên cửa sổ 5 phút có lúc rỗng; tôi dùng tầng 6 trên 6h và 30m, tầng 3 trên 1d và 2h, và một alert
riêng khi không có nhãn nào trong 6 giờ, vì khi đó tỉ lệ là 0/0 và alert burn rate im lặng.

## Sự cố: khách phàn nàn ETA lỗi và chậm, nhưng dashboard SLO xanh, log ứng dụng sạch. Bạn làm gì?

Trước hết tin khách và nghi chính SLI. Tôi so mẫu số của SLI với số yêu cầu client gửi (telemetry mobile, log gateway): nếu khác nhau thì
SLI đang bỏ sót yêu cầu. Rồi lấy vài trace mà client ghi nhận thất bại và xem từng span: thường SLI đo ở span bên trong (hàm `predict`) trong
khi gateway đã cắt yêu cầu vì chờ feature store quá timeout, hoặc từ chối trước khi tới ứng dụng. Giảm thiểu: xử lý thành phần chậm (feature
store), giảm timeout ứng dụng dưới timeout gateway. Sửa gốc: đo SLI ở span gốc hoặc ở load balancer; thêm đối soát định kỳ giữa SLI và số
liệu client, lệch quá 1% là alert.

## Sự cố: tỉ lệ lỗi 15% sau một deploy model, on-call đang debug. Bạn điều phối thế nào?

Tuyên bố sự cố và phân vai: người đang debug giữ vai ops, một người khác làm incident commander, một người lo comms cập nhật status page và
kênh nội bộ mỗi 15 phút. IC hỏi ngay "thay đổi nào gần nhất trước lúc lỗi bắt đầu"; nếu là deploy model thì rollback bằng đổi alias trước,
tìm nguyên nhân sau, thay vì restart hay đoán. Ghi mốc bắt đầu, phát hiện, giảm thiểu, hết tác động để tính TTD, TTM và % budget đã tiêu;
severity theo con số đó. Đóng sự cố khi ổn định một khoảng thời gian, giao người viết postmortem có hạn.

## Vì sao incident commander không nên tự debug?

Vì debug chiếm toàn bộ sự chú ý. Người đang đọc log không thấy rằng đội hỗ trợ đang chờ tin, rằng có hai người cùng thử hai thay đổi trên
production, hay rằng đã 30 phút mà chưa ai cân nhắc rollback. IC giữ bức tranh chung và ra quyết định; ops lead làm theo và báo kết quả. Ở
đội nhỏ một người có thể kiêm, nhưng phải nói rõ lúc nào đang đội mũ nào và chuyển IC đi ngay khi có người thứ hai.

## Postmortem không đổ lỗi là gì, và làm sao biết một postmortem tốt?

Là postmortem giả định mọi người đã hành động hợp lý với thông tin họ có, và hỏi hệ thống nào để sự cố xảy ra mà không ai biết. Dùng vai trò
thay tên người. Một postmortem tốt có tác động bằng số, dòng thời gian, chuỗi nguyên nhân là cơ chế thiếu (danh sách secret ghi tay, job nuốt
lỗi 403, không có SLI freshness), và hành động có chủ, hạn, cách kiểm, chia ba loại ngăn chặn, phát hiện, giảm thiệt hại. Dấu hiệu tệ: "cẩn
thận hơn", "theo dõi sát hơn", hay một cái tên trong mục nguyên nhân.

## Một design doc cho hệ thống ML cần có gì? Bạn hỏi gì khi review doc của người khác?

Yêu cầu có số và ngoài phạm vi; SLO nói rõ đo ở đâu; kiến trúc tách online và offline; ít nhất ba phương án gồm hiện trạng và phương án đơn
giản nhất; ước tính dung lượng và chi phí; chế độ hỏng và fallback; rollout và rollback; câu hỏi mở. Khi review tôi hỏi: chỉ số offline có
tương quan với online không, nhãn có thiên lệch do chính hệ thống không, ở đỉnh gấp 5 lần thì cái gì hết trước, thành phần này chết thì luồng
nghiệp vụ dừng hay rơi về fallback, rollback mất bao lâu, ai trực. Mục tiêu là tìm rủi ro, không phải chấm điểm tác giả.

## Thêm cache trước model có giải quyết được SLO p99 không?

Thường là không. Với hit rate h, độ trễ trung bình là `t_cache + (1 - h) x t_model` nên giảm mạnh, nhưng chừng nào tỉ lệ miss còn trên 1%
thì phân vị 99 vẫn nằm trong phân phối của model. Hit 85% làm trung bình giảm 6 lần mà p99 gần như giữ nguyên. Cache hợp khi mục tiêu là chi
phí hay trung bình, hoặc khi hit rate rất cao; với p99 cần làm model nhanh hơn (distill, lượng tử hoá, batching) hay đổi kiến trúc (tính trước).

## Batch hay realtime: bạn quyết định thế nào?

Theo ba biến: số thực thể so với số câu hỏi, độ cũ chấp nhận được, và feature cần tươi tới đâu. Batch trả tiền cho mọi thực thể mỗi lần
làm mới, kể cả không ai hỏi, và cũ tới một chu kỳ; realtime trả tiền cho từng câu hỏi cộng replica bật cả ngày. Gợi ý cho 2 triệu người dùng
làm mới vài lần mỗi ngày thường rẻ hơn ở batch; chấm gian lận cần giao dịch trong 1 phút thì phải realtime dù đắt hơn. Nhiều hệ thống lai:
tính trước phần chậm thay đổi, realtime phần tươi.

## Vì sao chọn Prometheus và `promtool test rules` cho alert SLO thay vì cấu hình alert trên giao diện của một dịch vụ giám sát?

Vì rule là code: nằm trong git, review được, và quan trọng nhất là kiểm được trước khi deploy. `promtool test rules` cho chuỗi thời gian giả
(lỗi 20% kéo dài, nhãn ngừng về, feature ngừng cập nhật) và khẳng định alert bắn hay không ở từng thời điểm; CI chặn một thay đổi làm alert
im lặng. Alert cấu hình bằng tay trên giao diện thường chỉ được kiểm khi sự cố thật xảy ra, tức là quá muộn. Dịch vụ giám sát thương mại vẫn
hợp khi đội không muốn vận hành Prometheus, miễn là cấu hình alert được quản lý như code (Terraform, API) và có cách thử.

## Thiết kế hệ thống: chấm điểm gian lận realtime cho ví điện tử, đỉnh 4 000 giao dịch mỗi giây, quyết định trong 150 ms.

Làm rõ: tỉ lệ gian lận, chi phí lọt và chi phí chặn nhầm, độ trễ nhãn (báo cáo 1-3 ngày, chargeback 30-90 ngày). Chỉ số: recall theo giá trị
gian lận, tỉ lệ chặn nhầm làm guardrail. Baseline: bộ luật hiện tại. Kiến trúc: gateway gọi service chấm điểm có timeout; feature cửa sổ 1 phút
và 1 giờ tính bằng streaming theo event time và push vào online store, feature lịch sử materialize theo giờ; GBM chạy trong process; luật cứng
phủ quyết; log quyết định để join nhãn. Vận hành: SLO khả dụng và độ trễ ở gateway, freshness theo tuổi feature, chất lượng theo nhãn 3 ngày;
fallback về bộ luật khi model hay store lỗi, không bao giờ dừng thanh toán. Điểm senior: nhãn thiên lệch vì giao dịch bị chặn không bao giờ có
chargeback, nên giữ một nhóm holdout nhỏ được cho qua ngẫu nhiên; shadow 2 tuần rồi canary theo tài khoản.

## Thiết kế hệ thống: nền tảng LLM nội bộ cho 30 đội với 16 GPU và một hạn mức API bên ngoài.

Đây là bài nền tảng, không phải chọn model. Một cổng LLM chung: xác thực, hạn mức theo đội, định tuyến (dữ liệu nhạy cảm chỉ tới model tự
host, tác vụ khác có thể ra API ngoài), log và đo chi phí theo đội (GPU-giờ chia theo token cộng hoá đơn API theo khoá). Tự host model mở cỡ vừa,
lượng tử hoá, continuous batching qua vLLM. RAG có chỉ mục riêng từng đội và kiểm quyền theo tài liệu lúc truy xuất; cache ngữ nghĩa theo đội để
không rò rỉ chéo. Guardrail PII và chống prompt injection. Bộ đánh giá theo use case làm cổng khi đổi model hay prompt. SLO: thời gian ra token
đầu, token mỗi giây, tỉ lệ qua guardrail, chất lượng theo bộ đánh giá. Hạn mức và hàng đợi ưu tiên để một đội không đốt hết GPU.

## Bạn đã học xong tầng senior. Điều gì bạn vẫn chưa có so với một kỹ sư senior thật?

Kinh nghiệm bảo chứng: từng trực on-call và bị đánh thức, từng rollback một model lúc 2 giờ sáng, từng bảo vệ một design doc trước người phản
đối, từng nhận hoá đơn GPU bất ngờ và phải giải thích. Module này cho tôi khung và từ vựng để làm những việc đó tốt hơn khi gặp, và để nói về
chúng trong phỏng vấn một cách trung thực: tôi sẽ nói rõ phần nào tôi đã làm thật (trong lab, trong dự án), phần nào là kiến thức, và tôi sẽ
học phần còn lại thế nào.
