# Câu hỏi phỏng vấn: Training pipeline và orchestration

## "Tái lập được" nghĩa là gì với một lần train, và bạn chứng minh nó thế nào?

Chạy lại với cùng đầu vào cho ra cùng artifact, và có bằng chứng. Tôi ghim ba chân: code (git commit, cây sạch), dữ liệu (hash nội
dung) và ngẫu nhiên cùng môi trường (seed tường minh, phiên bản python/numpy/sklearn hoặc digest image). Bằng chứng là hash của
artifact trong một manifest: chạy lại từ manifest rồi so hash. Nếu hash khác, manifest giúp tôi biết khác ở chân nào thay vì
đoán. Thực dụng: tái lập từng bit cho model quan trọng, "trong dung sai" cho phần còn lại.

## Seed đã đặt mà kết quả vẫn lệch giữa hai lần chạy. Bạn nghĩ tới những nguyên nhân nào?

Seed chỉ đặt ở chỗ này mà chỗ khác dùng trạng thái toàn cục; song song nhiều luồng hoặc GPU cộng số thực theo thứ tự không cố
định; dữ liệu đổi thứ tự dòng hoặc kiểu cột; khác phiên bản thư viện; hoặc một bước đọc dữ liệu không tất định (query không có
`ORDER BY`). Cách tìm: giảm song song về 1, băm dữ liệu vào, so từng bước (hash sau chuẩn hoá, sau chia tập, sau train) tới bước
đầu tiên lệch.

## Vì sao khoá cache theo đường dẫn tệp là một cái bẫy? Khoá đúng gồm những gì?

Đường dẫn là cùng một chuỗi dù nội dung đã đổi, nên cache trúng và trả kết quả của dữ liệu cũ, không lỗi, không cảnh báo. Khoá
đúng gồm mọi thứ làm đầu ra đổi: hash nội dung dữ liệu (hoặc hash do nguồn cung cấp như `dvc.lock`, ETag), tham số, seed, và phiên
bản code nếu code hay đổi. Cache là tối ưu, không phải tái lập: nó còn có thể che việc pipeline không tái lập.

## Retry nên đặt ở bước nào, cho loại lỗi nào, và khi nào nó gây hại?

Ở bước có lỗi tạm thời (đọc qua mạng, gọi API), với danh sách lỗi cho phép (kết nối, timeout), backoff và jitter. Không đặt ở bước
train (lỗi mã hay dữ liệu sẽ lỗi lại y hệt) và không ở cả flow (lặp việc đã xong). Gây hại khi thử lại lỗi vĩnh viễn (che lỗi thật,
tốn thời gian) hoặc khi bước không idempotent: thử lại tạo trùng bản ghi hay trùng version. `retries=2` là 3 lần gọi, đếm cho đúng.

## Bạn chọn Prefect thay vì Airflow cho pipeline training. Vì sao, và bạn chấp nhận mất gì?

Ràng buộc: nhóm nhỏ không có người trực riêng, cần tham số hoá theo tháng và backfill linh hoạt, chạy thử trên laptop không cần
scheduler và metadata DB, đội DS viết Python thuần. Prefect khớp cả bốn. Tôi chấp nhận mất hệ sinh thái operator lớn của Airflow và
thêm một hệ thống nữa nếu công ty đã vận hành Airflow cho ELT. Nếu công ty có Airflow và đội vận hành sẵn, chạy pipeline ML ở đó
cũng là lựa chọn tốt; tôi sẽ nêu điều kiện cụ thể để đổi.

## Kubeflow Pipelines, ZenML, Metaflow: khi nào bạn chọn từng cái?

Kubeflow Pipelines khi đã có Kubernetes và vận hành nó, nhiều job GPU, cần component container hoá và cô lập; trước đó chi phí
vận hành cụm lớn hơn giá trị. ZenML khi muốn lớp trừu tượng "stack" để đổi orchestrator hay artifact store mà không viết lại
pipeline. Metaflow khi đã ở AWS và nhóm DS thích decorator. Tôi bắt đầu từ ràng buộc (ai vận hành, chạy ở đâu, đơn vị công việc),
không từ tính năng.

## Backfill là gì và những gì có thể sai khi chạy nó?

Chạy lại pipeline cho quá khứ sau khi sửa lỗi hay dữ liệu về muộn. Nó ghi đúng vào nơi kết quả đang nằm, nên lỗi ở đây ghi đè cái
đúng bằng cái sai. Biện pháp: tham số hoá theo tháng logic (không theo đồng hồ), khoá ghi chứa tháng, idempotent, mặc định không
ghi đè, báo cáo tháng nào xong hay lỗi, và đối soát số liệu mới với cũ trước khi thay. Bất biến đáng test: kết quả một tháng không
phụ thuộc thứ tự và không phụ thuộc các tháng khác trong đợt.

## Sự cố: chạy backfill ba tháng xong, số liệu của hai tháng cũ trên dashboard giống hệt tháng đầu, dù dữ liệu nguồn khác nhau. Bạn làm gì?

Việc đầu tiên là dừng ghi thêm và khôi phục số đúng từ bản sao lưu hoặc chạy lại từng tháng, vì số sai đã ghi đè số đúng. Sau đó
điều tra bằng bằng chứng. Một: các con số giống nhau tới chữ số cuối là dấu hiệu "cùng đầu vào" chứ không phải "cùng phân phối",
nên kiểm đầu vào của từng tháng (số dòng, hash) ở từng bước. Hai: so lần chạy một tháng với lần chạy nhiều tháng để xem điều gì
khác nhau ngoài dữ liệu. Ba: tìm bước đầu tiên mà số dòng không khớp tệp nguồn, rồi đọc đúng đoạn mã ở bước đó. Sau khi sửa: thêm
test bất biến (kết quả không phụ thuộc thứ tự), kiểm đối soát số dòng tự động ở cuối mỗi lần chạy, và cổng "tháng nào đổi quá X%
so với bản cũ".

## Khi nào pipeline nên train lại? Nêu ba loại trigger và điểm yếu của mỗi loại.

Lịch: dễ vận hành, bắt tụt hậu âm thầm, nhưng train khi không cần. Dữ liệu mới: phản ứng với dữ liệu thật, nhưng hash đổi vì sửa
nhỏ và nhãn về muộn. Cảnh báo (drift, MAE): phản ứng với vấn đề thật, nhưng có báo động giả và không nói nguyên nhân. Cả ba chỉ là
lý do để xem xét; mỗi trigger đi qua cổng kiểm chất lượng dữ liệu, đủ nhãn, hiệu năng thật, rồi mới quyết định train.

## Vì sao không retrain mỗi khi có cảnh báo drift?

Drift của đầu vào không đồng nghĩa dự đoán sai: mùa vụ, kỳ nghỉ lễ làm phân phối đổi mà MAE trên nhãn thật không đổi. Nếu nguyên
nhân là dữ liệu hỏng, retrain dạy model học cái hỏng. Nếu nguyên nhân ngoài model, retrain không sửa và cảnh báo vẫn bắn, dẫn tới
vòng lặp. Mỗi lần train tốn tiền và mang rủi ro đưa model kém vào production. Tôi kiểm hiệu năng trên nhãn đã về trước, và coi
thất bại của lần retrain trước là thông tin để chuyển sang điều tra.

## Trigger "dữ liệu mới" nên dùng tín hiệu nào, và những cạm bẫy là gì?

Hash nội dung (hoặc hash do nguồn cung cấp: `dvc.lock`, ETag, snapshot id), không dùng mtime hay tên tệp. Thêm ngưỡng "đủ dòng
mới đã có nhãn" để khỏi retrain vì một dòng, và không ghi mốc khi bỏ qua để dữ liệu tích luỹ tới ngưỡng. Ghi trạng thái "đã train"
chỉ sau khi train thành công, nếu không train hỏng thì hệ thống tin là đã xong. Có `force` cho trường hợp đổi code mà dữ liệu không đổi.

## Bạn test một flow Prefect thế nào mà không cần server hay mạng?

Dùng `prefect_test_harness()` để có server tạm trong tiến trình test, tự dọn. Bơm lỗi bằng một đối tượng loader giả đếm số lần gọi
và ném lỗi tạm thời đủ số lần, rồi kiểm số lần gọi và kết quả cuối. Cache kiểm bằng đếm lần thân task chạy. Đặt thư mục lưu kết quả
vào thư mục tạm để cache không rò giữa các lần chạy test. Test hành vi, không đọc log.

## Thiết kế hệ thống: 6 model ETA cần train hằng tuần, một số có thể cần train theo dữ liệu mới hoặc cảnh báo. Bạn dựng pipeline thế nào?

Một flow tham số hoá theo model và tháng logic; deployment theo lịch tuần cho mỗi model, cộng trigger dữ liệu mới và cảnh báo đi qua
cùng một cổng quyết định (dữ liệu sạch, đủ nhãn, hiệu năng thật xấu đi hoặc model quá tuổi), có cooldown và trần số lần retrain.
Bước đọc dữ liệu có retry cho lỗi tạm thời; bước train cache theo hash dữ liệu và tham số. Mỗi lần chạy ghi manifest (hash dữ liệu,
seed, hash artifact) và lineage vào MLflow, rồi đi qua cổng promotion của module 04; model không tự lên production. Backfill
idempotent, khoá theo tháng, có đối soát. Giám sát chính pipeline: không chạy trong hai chu kỳ thì báo. Điều kiện đổi công cụ nêu
bằng số (số pipeline, số job GPU).

## Cache giúp tiết kiệm nhưng cũng có rủi ro gì với một pipeline training?

Nó có thể che việc code đổi (khoá theo đối số vẫn trúng và trả kết quả của logic cũ), che việc pipeline không tái lập, và khi trúng
thì thân task không chạy nên tác dụng phụ (tệp ghi ra) không được tạo lại; cache còn trả metrics cho một model đã bị xoá. Cách
giảm: đưa phiên bản code vào khoá hoặc đặt `cache_expiration`, trả về đường dẫn kèm hash thay vì model lớn, kiểm đầu ra còn tồn tại.

## Làm sao biết một pipeline CT đang khoẻ?

Đo chính nó: lần chạy gần nhất khi nào, bao nhiêu trigger bị bỏ qua so với train và vì sao, thời gian và chi phí mỗi lần, tỉ lệ
retrain có cải thiện qua cổng promotion, và alert khi pipeline không chạy trong hai chu kỳ lịch. Một pipeline CT hỏng im lặng
nguy hiểm hơn một pipeline hỏng ồn ào vì model cũ dần mà không ai biết.
