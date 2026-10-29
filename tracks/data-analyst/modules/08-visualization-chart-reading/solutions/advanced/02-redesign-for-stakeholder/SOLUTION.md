# Hướng làm: thiết kế lại slide Bike Sharing cho COO

Bài Advanced không có một đáp án duy nhất. Dưới đây là cách viết ba hàm, các con số tham chiếu, một trang
mẫu, các quyết định cần cân nhắc và rubric.

## Ba hàm

- **`yoy_by_month`**: `dates = pd.to_datetime(day["dteday"])`; `cnt.groupby([dates.dt.year, dates.dt.month]).sum()`
  rồi `unstack` năm thành cột; hai năm sắp tăng dần là `prev`, `curr`; `reindex(range(1, 13), fill_value=0)`;
  `growth = curr / prev - 1`; đặt `index.name = "month"`. Không dùng `yr`: hàm phải đúng với bất kỳ hai năm nào.
- **`weather_effect`**: `month = dteday.to_period("M")`; mức nền = TB `cnt` của ngày `weathersit == 1` theo
  `month`; `ratio = cnt / month.map(base)` (tháng không có ngày quang cho `NaN` và bị bỏ khi lấy TB);
  `ratio.groupby(weathersit).mean() - 1`, tên `effect`.
- **`build_page`**: tính số bằng hai hàm trên, vẽ bằng `plt.subplots`, đặt `fig.suptitle`, trả `fig`, không
  gọi `plt.show()` trong hàm.

## Con số tham chiếu

| Con số | Giá trị |
| --- | --- |
| Lượt thuê 2011 / 2012 | 1 243 103 / 2 049 576 (**+64.9%**) |
| Tăng theo tháng | Mọi tháng đều tăng; mạnh nhất tháng 3 (+157%), tháng 1 (+153%); chậm nhất tháng 6 (+41%), tháng 12 (+42%) |
| Đỉnh 2012 | Tháng 9: 218 573 lượt |
| Thành viên (`registered`) | 80.1% lượt năm 2011, 81.8% năm 2012 |
| Thời tiết, so ngày quang cùng tháng | mây/sương **−13.7%**, mưa/tuyết nhẹ **−56.5%** (21 ngày); không có ngày `weathersit = 4` |
| Thời tiết, so thẳng TB hai năm | mây/sương −17%, mưa −63%: phóng đại vì ngày mưa rơi nhiều vào tháng ít khách |
| Ngày thấp nhất | 29/10/2012: 22 lượt (bão Sandy, `weathersit = 3`) |

## Trang mẫu

- **Headline** (suptitle): "Lượt thuê năm 2012 tăng 65% so với 2011; ngày mưa mất hơn một nửa lượt thuê".
- **Chart 1, rộng nhất, bên trái**: line hai năm theo tháng trên cùng trục y từ 0, năm trước màu xám, năm nay
  màu nhấn, nhãn trực tiếp ở cuối đường thay legend. Tiêu đề: "Tháng nào cũng cao hơn năm trước; cả năm +65%".
  Annotation tháng tăng chậm nhất hoặc đỉnh tháng 9.
- **Chart 2, bên phải**: bar ngang `weather_effect` (bỏ dòng ngày quang vì luôn là 0), nhãn phần trăm trên bar,
  một màu. Tiêu đề: "Ngày mưa mất 56% lượt so với ngày quang cùng tháng".
- **Chú thích nguồn** nhỏ ở đáy: bộ dữ liệu, cách tính mức nền.
- **Bỏ**: pie theo mùa (bốn lát 14-32%, khó so; nhãn mùa của UCI lệch một mùa; mùa vụ đã thấy trên chart 1);
  dual axis nhiệt độ (hai thang tuỳ ý, trục trái bắt đầu 30 000 phóng đại biến động; nhiệt độ là cơ chế, không
  phải câu hỏi của COO); bảng số (đưa vào phụ lục hoặc dashboard, có thể tải về).

Một bản tốt hơn nữa có thể thêm chart thứ 3: tỉ trọng thành viên hai năm (nếu COO quan tâm "khách trung thành"),
nhưng chỉ khi headline nhắc đến nó.

## Các quyết định cần cân nhắc

- **Câu hỏi trước, chart sau**: hai câu hỏi của COO quyết định hai chart; mọi chart khác phải giành chỗ bằng cách
  trả lời một câu hỏi.
- **So sánh công bằng**: so cùng tháng năm trước (trừ mùa vụ); với thời tiết, so trong cùng tháng (trừ mùa vụ và
  tăng trưởng). Nói rõ mẫu số trên trục.
- **Tương quan, không phải nhân quả**: ngày mưa ít lượt, nhưng hệ thống còn có thể mất khách vì lý do khác (sự cố,
  ngày lễ). "Mất khách" ở đây là mất trong ngày, không phải mất hẳn.
- **Màu**: một màu nhấn cho điều cần nhìn (năm nay, tác động xấu), xám cho tham chiếu; không cầu vồng.
- **Số trên trang tính từ dữ liệu**: tiêu đề cứng "65%" sẽ sai khi trang được chạy lại trên dữ liệu khác.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Headline là insight | 20 | Suptitle trả lời cả hai câu hỏi, có con số và so với gì; tiêu đề từng chart là kết luận |
| Chart đúng loại | 20 | So cùng kỳ bằng line hai năm (hoặc bar nhóm) chung trục từ 0; tác động thời tiết bằng bar sắp xếp; không pie, không dual axis, không bảng |
| Annotation | 15 | Ít nhất một chú thích tại chỗ giải thích điểm cần nhìn; nhãn trực tiếp thay legend khi được |
| Thứ tự | 15 | Kết luận trước (năm nay so với năm trước), rủi ro/nguyên nhân sau, nguồn và định nghĩa ở đáy |
| Bỏ chart thừa | 15 | Memo nói rõ bỏ gì, vì sao, và phần bị bỏ đi đâu (phụ lục, dashboard) |
| So sánh công bằng | 10 | Hiệu ứng thời tiết trừ mùa vụ (so trong tháng); nêu được vì sao so thẳng phóng đại |
| Memo | 5 | Ngắn, viết cho COO, có mục giới hạn cụ thể |

Từ 70 điểm trở lên là trang đủ gửi COO.

## Sai lầm hay gặp

- Sửa màu và font của slide cũ nhưng giữ nguyên ba chart: vẫn không trả lời câu hỏi.
- Đổi pie thành bar theo mùa với nhãn gốc "Spring/Summer/Fall/Winter" (lệch một mùa).
- Hai panel tách nhau cho 2011 và 2012 với trục y riêng: mắt không so được.
- Headline "Báo cáo Bike Sharing 2011-2012" hoặc headline có số gõ tay.
