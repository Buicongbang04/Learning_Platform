# Lời giải: viết memo một trang từ notebook có sẵn

## Cách làm `memo_facts`

```python
df = hour.copy()
df["dteday"] = pd.to_datetime(df["dteday"])
off = df["workingday"] == 0
window = off & df["hr"].isin(WINDOW_HOURS) & df["dteday"].dt.month.isin(WINDOW_MONTHS)
days = df.groupby("dteday")["workingday"].first()
```

Mỗi khoá là một phép chia: tử và mẫu phải cùng tập dòng. Hai bẫy: đếm ngày theo **dòng** (ra tỉ lệ giờ) thay vì theo
`dteday` khác nhau; và lấy trung bình của tỉ lệ từng giờ thay vì tổng `casual` chia tổng `cnt` (giờ đêm ít lượt sẽ có
trọng số bằng giờ trưa đông khách).

| Khoá | Giá trị thật |
| --- | --- |
| `casual_share` | 18.8% |
| `offday_days_share` | 31.6% (231 / 731 ngày) |
| `offday_casual_share` | 51.1% |
| `casual_share_offday` | 31.7% |
| `casual_share_workday` | 13.2% |
| `window_hours_share` | 6.1% |
| `window_casual_share` | 27.6% |
| `casual_share_in_window` | 38.9% |

## Memo mẫu

Xem `MEMO.md` cùng thư mục. Các lựa chọn chính:

- **Headline** là kết luận và hành động, với một tương phản dễ nhớ: "6% số giờ mang 28% lượt của họ".
- **Bối cảnh** chỉ ba câu; câu hỏi viết lại thành quyết định ("tập trung vào lúc nào để gặp nhiều khách vãng lai, ít
  lượt hiển thị lãng phí").
- **Khuyến nghị** có địa điểm (điểm thuê, app), thời gian (ngày nghỉ, 10h-17h, tháng 4-10), người chủ trì, và hình thức
  thử nghiệm có đối chứng (vì chưa biết hiệu quả).
- **Bằng chứng** ba dòng, mỗi dòng một tương phản: phần của ngày nghỉ (31.6% ngày, 51.1% lượt), tỉ trọng theo loại ngày
  (31.7% so với 13.2%, gấp 2.4 lần), độ tập trung của khung (6.1% giờ, 27.6% lượt, 39/100 lượt trong khung).
- **Giới hạn** nói điều quan trọng nhất trước: thời điểm đi không phải xác suất đăng ký.
- **Bước tiếp theo** có người, việc, mốc.

Một memo khác vẫn đạt nếu kết luận khác nhưng có lý lẽ, ví dụ khuyến nghị nhắm khách vãng lai **ngày làm việc** (13.2%
lượt, nhưng có thể là người đi làm, dễ đăng ký hơn) với điều kiện memo nói rõ đánh đổi đó và đề xuất thử nghiệm so sánh
hai nhóm.

## Đáp án trắc nghiệm

| Câu | Đáp án | Giải thích |
| --- | --- | --- |
| `offday-share` | b | 231/731 = 31.6% số ngày; 51.1% lượt khách vãng lai. (a) nhầm với tỉ trọng trong ngày nghỉ (31.7%); (d) nhầm với tỉ trọng ngày làm việc |
| `window-concentration` | a | 27.6% tổng lượt khách vãng lai. 38.9% là tỉ trọng khách vãng lai **trong** khung (mẫu số khác) |
| `reach-ratio` | c | 31.7% / 13.2% = 2.4. (b) 1.6 là 51.1% / 31.6%, phép so khác |
| `offday-peak-hour` | d | 14h, khoảng 140 lượt TB/giờ; vòm buổi trưa 12h-16h. 8h và 17h là đỉnh đi làm của thành viên ngày làm việc |
| `bluf` | c | Người đọc dừng sau dòng đầu vẫn biết nên làm gì. (a), (d) là phụ lục; (b) là câu hỏi, không phải câu trả lời |
| `valid-limitation` | a | Dữ liệu đo khi nào khách vãng lai đi, không đo ai sẽ đăng ký. (b) 17 379 giờ là đủ để mô tả; (c) không cần ML cho câu hỏi mô tả; (d) là khẳng định không có bằng chứng |
| `no-jargon` | d | Memo viết cho người ra quyết định; tên cột là chi tiết kỹ thuật thuộc notebook hoặc phụ lục |

## Rubric nội dung (ngoài test tự động, 10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Headline là kết luận có hành động, con số đúng, người đọc dừng ở đó vẫn biết làm gì | 2 |
| Khuyến nghị cụ thể: lúc nào, ở đâu, ai làm, dạng thử nghiệm | 2 |
| Ba bằng chứng, mỗi cái có tham chiếu (so với gì), không lặp ý | 2 |
| Giới hạn đúng trọng tâm (thời điểm ≠ khả năng đăng ký, thiếu dữ liệu trạm, chưa đo hiệu quả) | 2 |
| Bước tiếp theo có người, việc, mốc; ngôn ngữ không nhân quả quá mức; không thuật ngữ kỹ thuật | 2 |
