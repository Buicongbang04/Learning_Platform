# Lời giải: phát hiện feedback loop

`feedback.py` cạnh tệp này là lời giải chạy được.

## Ý chính

- **Model quyết định dữ liệu nó nhìn thấy.** Giao dịch bị chặn không có nhãn, nên tỉ lệ gian lận trên dữ liệu có nhãn (`naive`) thấp
  hơn thật và càng thấp khi model chặn càng nhiều. Trong mô phỏng, tỉ lệ thật khoảng 0.12, `naive` đi từ khoảng 0.10 xuống 0.05 qua 4
  vòng. Huấn luyện lại trên dữ liệu đó, model học rằng vùng rủi ro cao "ít gian lận" (vì gần như không thấy mẫu nào), một vòng lặp tự
  củng cố.
- **Exploration cộng propensity sửa được.** Cho qua ngẫu nhiên một phần nhỏ (`epsilon`) giao dịch bị chặn và **ghi xác suất đó lúc
  quyết định**. Ước lượng Horvitz–Thompson `sum(y / p) / N` không chệch cho tỉ lệ của toàn bộ giao dịch. Không có exploration
  (`p = 0` ở vùng bị chặn) thì không phương pháp nào phục hồi được, vì dữ liệu không chứa thông tin về vùng đó.
- **"Không đo được" khác "không lệch".** Trả `None` khi thiếu exploration, để dashboard không xanh nhầm.

## Áp dụng thật

- Giá của exploration: cho qua 1–5% giao dịch rủi ro cao, giới hạn số tiền, loại trừ trường hợp chắc chắn (danh sách đen).
- Dùng IPW khi đánh giá model mới trên log của model cũ (off-policy evaluation), và khi huấn luyện lại (trọng số mẫu).
- Cùng kiểu thiên lệch ở recommendation (chỉ có click trên thứ đã hiện), tín dụng (chỉ biết nợ xấu của người được duyệt), kiểm duyệt nội
  dung.

## Lỗi hay gặp

- Chia cho số dòng có nhãn thay vì tổng số dòng: thành ước lượng khác, lệch khi có vùng `p = 1` và `p = epsilon` trộn nhau.
- Tính `p_approve` lại sau bằng model mới: propensity phải là của chính quyết định đã xảy ra.
