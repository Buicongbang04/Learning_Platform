# Lời giải: sự cố phục vụ lệch offline

**Nguyên nhân.** App gửi `distance_km` (kilomet, theo `API.md`); model học trên `trip_distance` của TLC, tính bằng dặm. Đường online
phải đổi km sang dặm (chia cho 1.609344) nhưng `featurize` **nhân** với 1.609344, nên model nhận khoảng cách gấp 2.59 lần giá trị
thật. Khoảng cách là feature mạnh nhất của giá cước, nên chuyến dài (khoảng cách lớn, cây quyết định ở vùng giá cao) lệch nhiều
nhất, chuyến ngắn lệch ít. Chia và nhân đều trông "có đổi đơn vị", nên review bằng mắt dễ bỏ qua.

**Vì sao không có alert.** Mọi chỉ số sức khoẻ dịch vụ (HTTP 200, độ trễ, CPU) đều bình thường; chỉ chất lượng dự đoán sai, mà
chất lượng chỉ đo được khi có nhãn, tức là chậm hàng ngày hoặc hàng tuần. Skew im lặng là loại lỗi tốn nhất vì hết thời gian
phát hiện.

**Cách tìm.** So feature của cùng chuyến ở hai đường: cột `trip_distance` lệch hệ số không đổi 2.59, các cột còn lại bằng nhau.
Hệ số không đổi ngay lập tức gợi ý một phép đổi đơn vị sai chứ không phải nhiễu hay default.

**Cách sửa trong `service.py`.** Hai phần:

1. Sửa phép đổi: `distance_km / KM_PER_MILE`, đặt hằng số có tên ở một chỗ.
2. Quan trọng hơn: `featurize` dựng một dòng có đúng cột đầu vào của đường offline (`pickup_ts`, `trip_distance` theo dặm,
   `zone_id`) rồi **gọi `build_features`**. Mọi biến đổi còn lại (giờ, cuối tuần, default zone) chỉ tồn tại một lần. Đường online
   chỉ làm phần của riêng nó: đổi từ hợp đồng API sang cột đầu vào chung.

**Phòng ngừa.**

- Test parity trong CI: phát lại N chuyến thật qua cả hai đường, so feature từng cột (như `skew_report`), chặn deploy nếu lệch.
- Hợp đồng đầu vào có kiểu **và** đơn vị, ghi trong tên trường (`distance_km`) và kiểm khoảng hợp lý ở biên dịch vụ.
- Log feature online để so định kỳ với offline cho cùng thực thể.

**Lưu ý test.** Test dùng `GradientBoostingRegressor` (ngưỡng cắt ở trung điểm giữa các giá trị) để phép đổi qua lại `km`
rồi `dặm` không làm nhảy nhánh vì sai số dấu phẩy động; model dựa trên ngưỡng bằng đúng giá trị dữ liệu (như histogram boosting) sẽ nhạy với sai số 1e-16 ở
đúng chỗ đó, một lý do nữa để ghi log feature online thay vì tin vào phép đổi qua lại.
