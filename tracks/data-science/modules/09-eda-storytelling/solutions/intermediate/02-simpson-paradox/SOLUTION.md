# Lời giải: Simpson's paradox trong dữ liệu Olist thật

Notebook lời giải: `simpson.ipynb` (chạy được toàn bộ khi đã tải Olist thật).

## Cách làm

- `build_orders`: lọc đơn giao xong, dedupe review theo `review_answer_timestamp` mới nhất, inner
  join (bỏ đơn không có review), so nguyên timestamp cho `late`.
- `standardized_rates`: bảng tầng × nhóm, giữ tầng có mặt ở mọi nhóm, trọng số chung cho mọi nhóm
  (mặc định là phân bố tầng của dữ liệu đang xét), chuẩn hoá lại trọng số rồi lấy tổng có trọng số.
  Dùng `reindex` thay `.loc` để tầng kiểu bool không bị hiểu thành mask: bug này cho kết quả sai mà
  không báo lỗi (với tầng `late`, `.loc[[False, True]]` chỉ giữ dòng `True` và adjusted diff thành
  −13.6 điểm thay vì −2.1).
- `simpson_check`: lọc hai nhóm trước, để trọng số chỉ phản ánh hai nhóm đang so.

Chọn trọng số là một quyết định: trọng số của nhóm A trả lời "nếu B có mix như A thì sao", trọng số
gộp trả lời "nếu cả hai có mix chung". Khi kết luận đổi dấu theo trọng số, nói ra.

## Kết quả trên Olist thật

| Tầng | SP | ngoài SP | Tỉ trọng SP | Tỉ trọng ngoài SP |
| --- | --- | --- | --- | --- |
| 0–6 ngày | 7.35% | 7.70% | 46.9% | 12.7% |
| 7–13 | 9.46% | 8.64% | 39.4% | 43.5% |
| 14–20 | 15.45% | 10.63% | 9.5% | 24.7% |
| 21–29 | 40.64% | 21.36% | 3.0% | 12.0% |
| 30+ | 66.80% | 62.49% | 1.3% | 7.1% |
| Gộp | 10.69% | 14.34% | | |

- Theo số ngày giao: crude −3.66 điểm, adjusted +2.92 điểm, 4/5 tầng ngược chiều → `reversal`.
- Theo trễ / đúng hẹn: đúng hẹn 8.58% so với 9.70%, trễ 44.61% so với 58.25%; adjusted −2.12 điểm,
  không đảo chiều.

## Rubric cho phần kết luận

| Tiêu chí | Đạt khi |
| --- | --- |
| Đọc đúng hiện tượng | Nêu crude, adjusted, và cơ chế mix (46.9% so với 12.7% đơn dưới 7 ngày) |
| Không chọn bảng theo ý muốn | Trình bày cả hai cách chia, nói rõ chúng trả lời hai câu hỏi khác nhau |
| Lập luận cơ chế | Khách đánh giá theo lời hứa (ngày hẹn), không theo số ngày tuyệt đối; số ngày giao là mediator khi câu hỏi là tác động của logistics |
| Giới hạn | Dữ liệu quan sát, các bang khác nhau về nhiều thứ khác; tầng nhanh nhất chênh gần 0; tầng chậm của SP ít đơn |
| Ngôn ngữ | Không nói "chứng minh"; phân biệt tương quan và nhân quả |

## Sai lầm hay gặp

- Thấy đảo chiều rồi kết luận "bảng phân tầng mới là sự thật". Phân tầng theo mediator hay collider
  cũng tạo ra "đảo chiều" sai.
- So từng tầng mà không nhìn tỉ trọng mỗi tầng: không giải thích được vì sao gộp lại khác.
- Chọn bin số ngày giao sau khi nhìn kết quả để "đảo chiều đẹp hơn": đó là p-hacking bằng biểu đồ.
  Bin trong bài được cố định trước (theo tuần).
