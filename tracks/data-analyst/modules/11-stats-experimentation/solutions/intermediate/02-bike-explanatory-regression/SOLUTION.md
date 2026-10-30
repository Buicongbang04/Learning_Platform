# Lời giải: regression để giải thích thời tiết và lượt thuê

## Cách làm

1. **`prepare`**: `assign` các cột đơn vị business và nhãn. Đổi sang °C, %, km/h trước khi fit để hệ số đọc thẳng
   được ("mỗi °C"), không phải "mỗi đơn vị chuẩn hoá 0-1".
2. **`fit_explanatory`**: `smf.ols(...).fit(cov_type="HC3")`. Hệ số OLS không đổi giữa các loại sai số chuẩn; chỉ
   khoảng tin cậy và p đổi. HC3 chịu được phương sai sai số không đều (ngày đông khách dao động nhiều hơn ngày
   vắng); HAC chịu thêm tự tương quan theo thời gian.
3. **`effect_table`**: hệ số × số đơn vị, nhân cả hai đầu khoảng tin cậy. Trưởng vận hành nghĩ theo "ấm hơn 5°C",
   "gió mạnh hơn 10 km/h", không theo "mỗi 1°C".
4. **`coef_path`**: fit lần lượt từng công thức, lấy hệ số của biến quan tâm. Cách nhanh nhất để thấy hệ số nhạy
   với biến kiểm soát tới đâu.
5. **`turning_point`**: đạo hàm của β₁x + β₂x² bằng 0 tại x* = −β₁ / (2β₂).

## Kết quả trên bộ thật

Model đầy đủ, n = 731, R² = 0.823, HC3:

| Yếu tố (giữ các yếu tố khác cố định) | Thay đổi lượt thuê/ngày | CI 95% |
| --- | --- | --- |
| Ấm hơn 5°C | **+623** | [+539; +707] |
| Ẩm hơn 10 điểm % | −133 | [−188; −78] |
| Gió mạnh hơn 10 km/h | −417 | [−554; −281] |
| Trời mù (so với quang) | −427 | [−567; −287] |
| Mưa/tuyết nhẹ (so với quang) | **−1 917** | [−2 417; −1 417] |
| Ngày lễ | −624 | [−1 126; −122] |
| Ngày làm việc | +118 (p = 0.12) | [−31; +268] |
| Năm 2012 so với 2011 | +2 014 | [+1 888; +2 139] |

Lượt thuê trung bình 4 504/ngày: mưa nhỏ lấy đi khoảng 43%.

**Đường đi của hệ số nhiệt độ** (lượt/°C): chỉ nhiệt độ 162.0 → + năm 155.4 → + mùa **130.2** → + thời tiết 125.3
→ đầy đủ 124.6. Mùa là biến gây nhiễu chính: nó liên quan tới cả nhiệt độ và lượt thuê (ánh sáng ban ngày, thói
quen theo mùa). Model một biến gán cho nhiệt độ cả phần của mùa.

**Mùa**: mã 1 (`spring` theo Readme UCI) thực tế phủ 21/12-20/3, giai đoạn lạnh và tối nhất. Hệ số
`winter` (+1 546) nghĩa là: ở **cùng nhiệt độ** và cùng thời tiết, giai đoạn mã 4 (23/9-20/12) đông khách hơn
giai đoạn mã 1. Không phải "mùa đông đông khách": mùa đông lạnh hơn, và hệ số nhiệt độ đã trừ phần đó.

**Giả định**: Durbin-Watson = 1.09 (2 là không tự tương quan): ngày thiếu khách hơn model dự kiến thường đi liền
nhau (sự kiện, đợt thời tiết kéo dài). HAC 7 ngày tăng sai số chuẩn nhiệt độ từ 8.6 lên 14.8 (CI cho +5°C thành
khoảng +478 tới +768), nhưng mọi kết luận về thời tiết vẫn đứng vững. Ngày lễ HAC: CI [−1 062; −186].

**Phi tuyến**: thêm nhiệt độ bình phương, R² lên 0.851, đỉnh ở **27.6°C**; 22% số ngày nóng hơn mức này. "Ấm thêm
5°C thêm ~620 lượt" là trung bình trên cả năm: đúng cho ngày xuân, thu; sai cho ngày hè vốn đã nóng (module 08 đã
thấy tương quan gần 0 trong mùa 3).

**Vì sao thời tiết diễn giải gần như nhân quả được**: thời tiết không bị ai chọn theo lượt thuê, nên ít nguy cơ
nhân quả ngược hay biến gây nhiễu ẩn (ngoài mùa, năm đã kiểm soát). Một biến như "số trạm mở mới" thì công ty chọn
mở ở nơi và lúc nhu cầu đang tăng: hệ số của nó trộn quyết định với tác động.

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `temp-effect` | c | 124.6 × 5. Phương án a là 162 × 5 (model một biến), b là hệ số mỗi 1°C, d là hệ số năm 2012 |
| `omitted-variable` | a | Thêm mùa giảm 25.1 lượt/°C, lớn nhất |
| `why-biased` | b | Omitted variable bias: biến bị bỏ sót liên quan tới cả x và y |
| `season-sign` | c | Đọc theo mã thực tế và "ở cùng nhiệt độ" |
| `workingday` | a | +118, p = 0.12. Phương án c là chênh lệch thô ở Basic 03; d là hiệu ứng riêng của khách thành viên |
| `autocorrelation` | b | DW < 2: tự tương quan dương làm sai số chuẩn HC3 quá lạc quan |
| `turning-point` | d. 27.6°C | 20.3 là nhiệt độ trung bình, 35.3 là cao nhất, 41 là hệ số chuẩn hoá |
| `explain-vs-predict` | d | Model giải thích chọn biến theo nghiệp vụ (biến gây nhiễu cần kiểm soát), không theo p-value hay R². Biến trễ của `cnt` sẽ "hút" một phần ảnh hưởng của thời tiết và làm hệ số khó đọc |

## Ba câu cho trưởng vận hành (mẫu)

"Mưa nhỏ là yếu tố lớn nhất: giảm khoảng 1 900 lượt/ngày (1 400-2 400), gần một nửa ngày bình thường, nên ngày
dự báo mưa có thể rút bớt xe và người. Mỗi 5°C ấm hơn thêm khoảng 620 lượt (540-710) cho tới khoảng 28°C; nóng hơn
nữa thì không thêm. Gió mạnh hơn 10 km/h giảm khoảng 420 lượt; độ ẩm ảnh hưởng nhỏ (khoảng 130 lượt mỗi 10 điểm)."
