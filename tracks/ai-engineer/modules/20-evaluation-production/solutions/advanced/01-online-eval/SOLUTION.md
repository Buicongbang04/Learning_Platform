# Hướng làm: eval online, A/B, interleaving và drift

Bài không có code lời giải cho phần thiết kế: cách dựng thứ hạng, mô phỏng và báo cáo là của bạn. Dưới đây là các quyết
định cần cân nhắc, kết quả của một bản tham chiếu để so, và rubric chấm `REPORT.md`. Sáu hàm được chấm có đặc tả đầy đủ
trong notebook.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Hệ thống B | cùng retriever dense `bge-m3`, câu hỏi cắt còn 15 từ đầu | một lỗi cấu hình thật hay gặp (`max_length`, cắt theo token); chỉ ảnh hưởng câu dài nên khác biệt vừa phải, đúng cỡ khó phát hiện |
| Người dùng mô phỏng | một câu hỏi lấy có hoàn lại từ 300 câu ghim, click theo cascade (0.9 / 0.1 / dừng 0.8) | đơn giản, tham số đọc được; mọi kết luận về số người dùng **phụ thuộc** mô hình này |
| Thước đo A/B | tỉ lệ phiên có click vào một điều luật đúng, z-test hai tỉ lệ | thước đo nhị phân mỗi người dùng, khớp công thức `ab_sample_size` |
| Thước đo interleaving | đội nhiều click hơn trong lượt; kiểm định dấu bỏ lượt hoà | đúng cách dùng chuẩn của team-draft |
| Kiểm định | một phía theo chiều "A tốt hơn" khi đếm phát hiện (p < 0.05 hai phía và đúng chiều) | câu hỏi vận hành là "có thấy hồi quy không" |
| Số thí nghiệm | 300 mỗi mức người dùng | sai số chuẩn của power cỡ 0.03, đủ để đọc hình dạng đường |
| Drift | tỉ lệ ký tự mang dấu tiếng Việt của câu hỏi, và số từ; PSI với 20 bin đều cho tỉ lệ dấu | rẻ, không cần model, bắt đúng loại thay đổi; số từ là đối chứng không đổi |

Lỗi hay gặp: dùng chung một RNG cho chọn câu hỏi và click rồi đổi thứ tự gọi giữa hai phương pháp (kết quả không tái lập);
quên bỏ lượt hoà trong kiểm định dấu; đếm "phát hiện" cả khi B thắng có ý nghĩa; so `ab_sample_size` (mỗi nhóm) với tổng số
người dùng của mô phỏng (hai nhóm) mà không nhân đôi; lấy mẫu câu hỏi không hoàn lại khi số người dùng vượt 300.

## Kết quả tham chiếu

PC của track, Python thuần trên một lõi CPU (`nice`), khoảng 10 phút cho cả mô phỏng; embed câu hỏi qua Ollama `bge-m3`.

**Offline** (300 câu ghim): MRR@10 của A 0.708, của B 0.665; hit@1 0.603 so với 0.547; bootstrap theo cặp cho hiệu MRR
[0.017, 0.073]. Thứ hạng top-10 khác nhau ở 199 câu nhưng chỉ 65 câu có hạng của điều luật đúng thay đổi (44 tệ đi, 21 tốt
lên).

**Online mô phỏng**: tỉ lệ thành công thật (200 000 người dùng) A 0.814, B 0.786; `ab_sample_size` cho khoảng 3 129 người
mỗi nhóm, tức khoảng 6 260 người tổng. Trên 100 000 lượt interleaving: A thắng 45.3%, B thắng 39.2%, hoà 15.4%.

| Tổng số người dùng | Power A/B | Power interleaving |
| --- | --- | --- |
| 100 | 0.06 | 0.08 |
| 200 | 0.09 | 0.12 |
| 400 | 0.12 | 0.21 |
| 800 | 0.17 | 0.44 |
| 1 600 | 0.29 | 0.69 |
| 3 200 | 0.54 | 0.92 |
| 6 400 | 0.88 | 1.00 |

**Drift**: MRR@10 khi gõ không dấu: 0.076 (từ 0.708). Tỉ lệ ký tự mang dấu trung bình 0.30 ở câu hỏi test. PSI của đặc
trưng này giữa 2 432 câu hỏi train và 300 câu test: 0.003; giữa câu test và bản không dấu: 17.1 (mọi câu dồn về bin 0). PSI
của số từ: 0.030 (train so với test) và 0 (không dấu không đổi số từ).

## Đọc kết quả

- **Offline bắt được lỗi này** với 300 câu, nhờ so theo cặp. Đây là chỗ rẻ nhất để chặn nó.
- **Interleaving cần ít người dùng hơn A/B khoảng 2 tới 4 lần** để đạt power 0.8 ở đây (nội suy giữa các mức: khoảng 2 000 tới
  2 500 người so với khoảng 5 500 tới 6 300), không phải "10 tới 100 lần". Lý do: hai hệ thống giống nhau ở phần lớn câu (câu ngắn dưới 15 từ cho cùng thứ hạng),
  lượt hoà chiếm 15%, và A chỉ thắng B 45 so với 39. Lợi thế lớn của interleaving trong tài liệu đến từ hệ thống search có
  phương sai giữa người dùng rất lớn; mô phỏng này lấy người dùng từ chỉ 300 câu hỏi nên phương sai giữa người dùng đã nhỏ.
- `ab_sample_size` khớp mô phỏng: khoảng 6 260 người tổng cho power 0.8, mô phỏng cho 0.88 ở 6 400.
- **Drift do người dùng phá hệ thống mạnh hơn mọi lỗi code ở đây**: gõ không dấu đưa MRR từ 0.708 xuống 0.076. Một đặc trưng
  một dòng code (tỉ lệ ký tự có dấu) với PSI bắt được ngay; số từ không đổi nên PSI của nó gần 0: chọn đặc trưng theo loại thay
  đổi bạn lo, và có một đặc trưng đối chứng.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Offline | 15 | MRR và hit của hai hệ thống, hiệu có khoảng tin cậy theo cặp, giải thích vì sao so theo cặp |
| Mô phỏng | 25 | Hai phương pháp trên cùng lưới số người dùng, đủ thí nghiệm mỗi mức, so với `ab_sample_size`, tái lập được (seed) |
| Diễn giải | 20 | Giải thích lợi thế của interleaving ở đây lớn hay nhỏ và vì sao; nêu giả định của mô hình click và kết luận nào nhạy với nó |
| Drift | 15 | MRR không dấu, ít nhất một đặc trưng có PSI ở hai tình huống (bình thường, drift), ngưỡng có lý do |
| Báo cáo | 10 | Khuyến nghị có số ở đầu, bảng, giới hạn |

Đạt từ 70 điểm. Báo cáo kết luận "interleaving tốt hơn A/B 10 tới 100 lần" chỉ dựa vào tài liệu mà không khớp số đo của chính
mình không quá 50 điểm.
