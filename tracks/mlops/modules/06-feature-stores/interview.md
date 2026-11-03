# Câu hỏi phỏng vấn: Feature store và training-serving skew

## Training-serving skew là gì, và nó khác drift ở điểm nào?

Skew là feature của cùng một thực thể tại cùng một thời điểm khác nhau giữa lúc train và lúc serve; lỗi nằm ở đường tính, và
xuất hiện ngay từ ngày đầu. Drift là thế giới đổi theo thời gian nên model cũ dần lỗi thời. Phân biệt vì cách chữa khác nhau: skew sửa
mã hoặc quy trình, train lại không giúp vì model mới học đúng trên đường offline sai lệch; drift cần dữ liệu mới. Gợi ý nhanh: tệ ngay
từ đầu với dữ liệu nhìn giống train là nghi skew; tệ dần theo tuần là nghi drift.

## Kể các nguồn gây skew và cách chặn từng nguồn.

Code tiền xử lý ở hai nơi (chặn bằng một hàm chung hoặc một định nghĩa feature duy nhất), dữ liệu khác thời điểm (point-in-time join
và test không rò rỉ), default khác nhau (khai báo một chỗ, thêm cột cờ "thiếu", đo tỉ lệ dùng default), nguồn dữ liệu khác nhau (cùng
một nguồn cho cả hai đường) và phiên bản logic khác nhau (đánh phiên bản feature). Kiểm tra chung cho mọi nguồn: so feature của
cùng thực thể giữa hai đường, tự động.

## Point-in-time correctness là gì, và vì sao join theo khoá với giá trị mới nhất là sai?

Mỗi mẫu train chỉ được dùng giá trị feature mà hệ thống đã biết tại thời điểm sự kiện. Join giá trị mới nhất đưa thông tin tương lai vào mẫu
quá khứ nên offline đẹp giả, production tệ. Cài đặt bằng `merge_asof` backward theo khoá, với `feature_ts` là lúc giá trị khả dụng
(không phải lúc nó mô tả) và `tolerance` bằng TTL của online. Test đáng có: mọi dòng train có `feature_timestamp <= event_ts`.

## Feast gồm những phần nào? Điều gì xảy ra khi bạn chạy `apply` rồi `materialize-incremental`?

Entity (khoá nối), FeatureView (nhóm feature từ nguồn, có schema, ttl), nguồn, FeatureService, registry, offline store và online
store. `apply` đăng ký định nghĩa và tạo bảng online; `materialize-incremental` chép giá trị mới nhất của mỗi thực thể kể từ
lần chạy trước sang online store. Online store không tự đọc nguồn, nên cần lịch chạy và cảnh báo trễ. Lần chạy đầu lấy từ `now - ttl`, nên
ttl quá ngắn so với tuổi dữ liệu thì online rỗng.

## Lúc 3 giờ sáng bạn nhận alert "tỉ lệ dùng default tăng vọt" từ dịch vụ dùng Feast. Bạn làm gì?

Giả thuyết đầu: online store thiếu dữ liệu. Kiểm lần materialize gần nhất (trễ hay thất bại?), kết nối Redis, TTL có làm giá trị hết hạn
không, và job tính feature phía trên còn chạy không. Giảm nhẹ: dịch vụ đã có default nên vẫn trả lời, bật cờ chất lượng thấp nếu cần. Sau đó chạy
lại materialize, kiểm tỉ lệ default về bình thường. Hậu kiểm: cảnh báo trễ materialize để lần sau bắt từ gốc, không chờ metric ở dịch vụ.

## Sự cố: model tốt trên số đo offline nhưng dự đoán sai khi phục vụ, không có exception. Bạn chẩn đoán thế nào?

Không bắt đầu từ model. Lấy tập chuyến thật, phát lại qua đường online, so dự đoán và so feature từng cột với đường offline cho cùng
chuyến. Cột lệch đầu tiên chỉ ra chỗ cần đọc mã. Hình dạng của sai lệch (đồng loạt hay rải rác, ở mọi nơi hay ở một vùng giá trị) là manh mối. Sau khi sửa, thêm test parity vào CI và log feature online để so định kỳ, vì chỉ số sức khoẻ dịch vụ không bao giờ bắt được lỗi này.

## Vì sao bạn chọn Feast thay vì Tecton hay Hopsworks cho đội của mình?

Phụ thuộc ràng buộc. Feast hợp khi nhiều model dùng chung feature, độ tươi tính theo giờ, đội có người vận hành Redis và lịch
materialize; mã nguồn mở nên không bị khóa nhà cung cấp. Tecton hợp khi cần streaming feature, SLA và kiểm toán và có ngân sách; Hopsworks
khi muốn cả nền tảng trên hạ tầng riêng. Câu trả lời tốt nêu hai ràng buộc cụ thể và một điều bạn chấp nhận mất (ở Feast: tự lo vận hành).

## Khi nào bạn nói "đừng mua feature store"?

Model chạy theo lô với feature tính bằng SQL từ kho; feature đến từ chính thân yêu cầu; một model một đội; feature tổng hợp theo
tháng chia sẻ qua dbt. Skew do viết lại ở hai nơi chữa bằng hàm dùng chung và test parity. Feature store có chi phí: thêm điểm sự cố (online store),
thêm vận hành, thêm khái niệm. Tôi chỉ đề xuất khi có nhu cầu tra online, nhiều model dùng chung, hoặc point-in-time ở quy mô mà SQL tự viết không còn gọn.

## Thiết kế hệ thống: ba model dùng chung feature theo zone, hai model phục vụ online dưới 100 ms. Bạn thiết kế thế nào?

Một job tính feature theo giờ ghi vào offline store (Parquet hoặc bảng trong kho); Feast với registry trong Git và `apply` trong CI;
`materialize-incremental` mỗi giờ sang Redis; train lấy qua `get_historical_features` (point-in-time), serve đọc online qua SDK hoặc
feature server. Chỉ đưa lên online những feature thật sự cần online. Chống skew bằng test point-in-time, parity mỗi đêm (lấy mẫu thực thể
so online với offline), default khai báo một chỗ. Vận hành: cảnh báo trễ materialize, TTL theo chu kỳ cập nhật, Redis có persistence và
giới hạn bộ nhớ, staging riêng. Điều tôi nói thẳng: feature cần tươi 5 phút không phù hợp với lô theo giờ, cần streaming hoặc tính ở dịch vụ.

## `ttl` của feature view làm gì, và đặt bao nhiêu?

Offline: giá trị cũ hơn ttl so với thời điểm hỏi bị bỏ. Online: lần materialize đầu lấy từ `now - ttl`, và giá trị quá hạn không
được trả. Đặt theo chu kỳ cập nhật, thường vài lần chu kỳ (ví dụ 3 giờ cho feature theo giờ): đủ rộng để chịu một lần job trễ, đủ hẹp để không phục vụ số cũ vô hạn.
Quan trọng hơn: dùng cùng ngưỡng cho offline (`tolerance`) để train và serve thấy cùng tập giá trị.

## Online store chết giữa giờ cao điểm. Dịch vụ nên làm gì?

Dịch vụ không được sập theo. Đặt timeout ngắn cho lần đọc, rơi về default tường minh, đánh dấu phản hồi là chất lượng thấp và đếm tỉ lệ dùng default; với model
nhạy, có thể dùng cache cục bộ cho vài phút. Phía hạ tầng: Redis có persistence và replica, cảnh báo sức khoẻ, diễn tập sự cố. Trả lời cũng nên nêu rõ rằng
feature store là điểm sự cố mới mà bạn đã đồng ý nhận khi chọn nó.

## Làm sao biết online và offline thực sự bằng nhau?

Test parity: lấy mẫu thực thể, hỏi online và `get_historical_features` tại cùng thời điểm, so từng cột với ngưỡng (số thực thì `isclose`, NaN bằng NaN).
Báo cáo theo loại lệch: null lệch (default), giá trị lệch nhỏ (làm tròn, kiểu số), giá trị lệch lớn đồng loạt (biến đổi khác nhau), khoá thiếu (độ phủ).
Chạy trong CI trên dữ liệu thật mẫu, và chạy mỗi đêm trên production; chặn promotion model khi vượt ngưỡng.

## Làm sao đổi định nghĩa một feature đang được ba model dùng mà không vỡ production?

Không sửa tại chỗ. Tạo phiên bản mới (`zone_avg_speed_1h_v2`) cùng tên ngữ nghĩa, backfill lịch sử vào offline store, materialize song
song, rồi chuyển từng model sang v2 theo quy trình promotion của nó (train lại, kiểm parity). Giữ v1 cho tới khi model cuối cùng chuyển
xong. Tập train cũ ghi phiên bản feature để tái lập, và registry đổi qua pull request có người duyệt.
