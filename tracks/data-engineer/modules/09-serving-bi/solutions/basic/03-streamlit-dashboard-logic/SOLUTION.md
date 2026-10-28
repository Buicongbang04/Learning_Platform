# Lời giải: Tách logic dashboard Streamlit để test được

Xem `dashboard_logic.py` (lời giải) và `app.py` (giữ nguyên như starter).

## Vì sao tách logic khỏi UI

Streamlit chạy lại toàn bộ script mỗi lần người dùng bấm. Nếu tính toán nằm lẫn trong `app.py`, cách duy nhất để
kiểm tra là mở trình duyệt và bấm thử. Đưa logic ra module thuần Python (nhận DataFrame, trả DataFrame/dict) thì:

- Viết unit test bằng pytest, chạy trong CI.
- Dùng lại logic cho API hoặc job báo cáo email.
- `app.py` mỏng, dễ đổi giao diện mà không sợ sai số.

## Điểm đáng chú ý

- **`compute_kpis` đưa về grain đơn hàng** trước khi tính `late_rate`. Dữ liệu ở grain item, đơn `o3` có 2 item trễ;
  tính trên item sẽ ra 3/6 thay vì 2/4. Cùng bài học fan-out như ở bài basic/01.
- **Trường hợp rỗng** (không có đơn, không có đơn delivered) trả `0.0` hoặc `None` rõ ràng. Dashboard thật hay gặp
  bộ lọc ra rỗng; chia cho 0 làm cả trang lỗi.
- **`daily_series` điền ngày trống bằng 0** bằng `reindex`. Nếu không, biểu đồ line nối thẳng qua ngày không có đơn,
  che mất sự cố (một ngày không có đơn nào thường là dấu hiệu pipeline hỏng).
- **`kpi_status`** gom quy tắc ngưỡng vào một chỗ, hỗ trợ cả KPI "càng thấp càng tốt" như late rate.
- **`format_brl`** đổi dấu phân cách qua ký tự trung gian, không phụ thuộc `locale` của máy chạy (container thường
  không cài sẵn locale `pt_BR`).

## Phần UI trong `app.py`

- `@st.cache_data(ttl=600)` cache dữ liệu 10 phút. Kết nối DB thật nên bọc bằng `@st.cache_resource`.
- So sánh với kỳ trước cùng độ dài, hiển thị qua tham số `delta` của `st.metric`.
- Dòng "Dữ liệu cập nhật lúc …" là thông tin freshness tối thiểu cho dashboard vận hành.
