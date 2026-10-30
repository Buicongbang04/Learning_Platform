# Lời giải: kiểm lại "insight" do LLM viết và hồ sơ dữ liệu an toàn

## `actual_values`

Mỗi khoá là một dòng pandas, đọc đúng data dictionary:

```python
year = pd.to_datetime(day["dteday"]).dt.year
by_year = day.groupby(year)[["cnt", "casual"]].sum()
best_weekday = day.groupby("weekday")["cnt"].mean().idxmax()   # mã theo dữ liệu, không theo "lẽ thường"
mean_temp_c = (day["temp"] * 41).mean()                        # temp chuẩn hoá, chia cho 41
```

Lấy năm từ `dteday` thay vì cột `yr` (0/1) để không phải nhớ thêm một mã nữa; `pd.to_datetime` chấp nhận cả chuỗi lẫn
datetime.

## `verify`

Duyệt `zip(claim_id, claimed)` để giữ đúng thứ tự, tra `actual.get(claim_id, NaN)`, tính sai số tương đối (tuyệt đối khi
giá trị thật bằng 0) và `ok` kiểu `bool`. Claim không có giá trị thật là **không đạt**: trong quy trình thật, một con số
không kiểm được không được gửi đi.

## `llm_safe_profile`

- Kiểm tên trong `sensitive` trước: gõ sai `"Customer_ID"` thay vì `"Customer ID"` mà lờ đi thì cột thật sẽ lộ. Lỗi phải ồn.
- Nhận diện theo **token** của tên cột (`re.split(r"[^0-9a-z]+", name.lower())`), không theo chuỗi con: `"paid"` chứa `"id"`.
- `unique` dùng `dropna().nunique()`, `example` là `str` của giá trị khác thiếu đầu tiên hoặc `""`.

Hồ sơ không thay được data dictionary: LLM vẫn cần biết `weekday = 0` là Chủ nhật và `temp` đã chuẩn hoá. Gửi hồ sơ **kèm**
mô tả cột viết tay, đúng là thứ còn thiếu khiến chatbot của đồng nghiệp sai.

## Kết quả trên dữ liệu thật

| Claim | Chatbot nói | Thật | Đạt | Vì sao sai |
| --- | --- | --- | --- | --- |
| `yoy_growth` | 64.9% | 64.88% | có | |
| `best_weekday` | Thứ Bảy (6) | 5 = thứ Sáu (4 690 lượt/ngày) | không | Hiểu `weekday` bắt đầu từ thứ Hai: 4 690 là số thật của mã 5 |
| `summer_mean` | 5 644 | 4 992 | không | 5 644 là TB của `season = 3`; gắn nhầm nhãn mùa |
| `mean_temp_c` | 0.50 °C | 20.3 °C | không | Quên nhân 41: 0.495 là TB của `temp` chuẩn hoá |
| `casual_growth` | 68.4% | 50.8% | không | 68.4% là tăng trưởng của `registered` |
| `peak_hour_mean` | 461.5 | 461.45 | có | |
| `peak_day_count` | 8 714 | 8 714 | có | |
| `temp_corr` | 0.63 | 0.6275 | có | |

Bốn claim sai đều là **số thật gắn nhầm nhãn, mã hoặc đơn vị**. Chúng nguy hiểm hơn số bịa vì trông hợp lý và khớp "đâu
đó" trong dữ liệu. Không phép kiểm "số có vẻ đúng không" nào bắt được chúng; chỉ tính lại theo data dictionary mới bắt được.

Bốn câu hỏi cuối notebook:

1. Nguyên nhân gốc: không đọc data dictionary (mã thứ, mã mùa, chuẩn hoá nhiệt độ) và nhầm cột.
2. "Tăng nhiệt độ sẽ tăng lượt thuê" biến tương quan gộp hai năm thành nhân quả; trong mùa nóng tương quan gần 0 hoặc âm
   (module 08, phần 4).
3. 17h là đỉnh của trung bình mọi ngày, do ngày làm việc chiếm đa số; cuối tuần đỉnh rơi vào buổi trưa. Một câu đúng về
   trung bình có thể sai cho từng nhóm.
4. Hồ sơ đủ để LLM biết có cột `weekday`, `cnt`, kiểu số, 7 giá trị khác nhau; nó cần thêm mô tả "0 = Chủ nhật" để đặt
   nhãn đúng.

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `failed-claims` | c | 4 claim không đạt (bảng trên) |
| `best-weekday` | a | Mã 5 = thứ Sáu, 4 690 lượt/ngày. Thứ Bảy (mã 6) khoảng 4 550, Chủ nhật 4 229 thấp nhất |
| `temp-celsius` | d | `temp * 41` trung bình 20.3 °C. 0.50 là giá trị chuẩn hoá; 23.7 là nhiệt độ cảm nhận (`atemp * 50`), một cột khác |
| `swapped-growth` | b | Lượt thành viên 995 851 → 1 676 811, +68.4%. Tổng lượt +64.9%; khách vãng lai +50.8% |
| `root-cause` | c | Mọi số sai đều là số thật của dữ liệu, gắn nhầm. (a) sai: không số nào ngẫu nhiên; (b) dữ liệu không lỗi; (d) sai số làm tròn nằm trong 1% |
| `corr-wording` | a | Câu mô tả, đúng phạm vi "xét cả hai năm". (b) biến hệ số tương quan thành độ dốc nhân quả; (c) nhầm r với r² (0.63² ≈ 0.39); (d) sai trong mùa hè (module 08) |
| `what-to-send` | b | Hồ sơ cột đã che định danh đủ cho việc viết SQL. (a), (c) gửi dữ liệu khách ra công cụ chưa duyệt; (d) mã khách vẫn là dữ liệu định danh |
