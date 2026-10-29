# Báo cáo: NASA KSC HTTP access log, tháng 7/1995

## Bộ dữ liệu

- Nguồn: Internet Traffic Archive, access log web server NASA Kennedy Space Center
  (https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html), công bố tự do.
- Tệp `NASA_access_log_Jul95.gz`: 20,7 MB gzip, 205 MB text, 1 891 715 dòng Common Log Format.
- Mỗi dòng là một request: host (tên miền hoặc IP), timestamp có múi giờ `-0400`, request line,
  status, số byte trả về. Không có user id, không có khoá: một request là một dòng.
- Thời gian thật sự có dữ liệu: 01/07/1995 00:00:01 tới **28/07/1995 13:32:25**, không phải hết tháng 7.

## Làm sạch

- 6 dòng hỏng (0,0003%): 5 request là byte rác hoặc thiếu method (`"\x05\x01"`, `"1/history/apollo/images/"`),
  và dòng cuối tệp bị cắt giữa chừng (`alyssa.p`). Tách ra danh sách reject, không làm sập pipeline.
- Request chứa dấu `"` bên trong (`"GET /images/" HTTP/1.0"`) vẫn đọc được nhờ regex tham lam.
- 3 604 request không có protocol (kiểu HTTP/0.9 `"GET /page.html"`): giữ, `protocol = null`.
- `bytes = -` (304, 404 không có body) thành 0. Timestamp đọc kèm offset rồi lưu **UTC**; phân tích đổi về
  `America/New_York`.
- Không dedup: 835 dòng giống hệt một dòng khác (cùng host, cùng giây, cùng request) là request thật (trình duyệt tải lại, proxy).
- Thêm `host_type`: `ip`, `local`, hoặc đuôi tên miền.
- Kết quả: `data/clean/nasa-http-logs/requests.parquet`, 1 891 709 dòng, ~22 MB (bằng cỡ tệp gzip
  nhưng đã có kiểu, đọc từng cột, không phải parse lại).

## Insight

1. **Ngày phóng tàu con thoi làm traffic gần gấp đôi**: 13/07/1995 có **134 203** request, so với trung
   bình **76 237**/ngày thường. Đó là ngày Discovery (STS-70) phóng. Khoảng lặng dài nhất cả tháng
   (**22,1 phút**, từ 19:48:59) cũng rơi vào tối hôm đó: nhiều khả năng server quá tải hoặc khởi động lại.
   Bài học hạ tầng: tải theo sự kiện, không theo trung bình.
2. **Người dùng là dân văn phòng ở Mỹ**: đỉnh lúc **14h**, đáy lúc **5h** (giờ miền Đông, ~31 900 request
   cả tháng so với ~122 500). Cuối tuần chỉ **45 871** request/ngày, thấp hơn ngày thường **40%**.
3. **404 có nguyên nhân cụ thể**: 10 845 request 404 (0,6%), đứng đầu là `/pub/winvn/readme.txt`
   (**667** lần): một link chết trong phần mềm đọc tin WinVN. Sửa một link là bớt 6% lỗi 404.
4. **Khối lượng**: 38,7 GB trả về cho 81 982 host khác nhau. Host `.com` tải nhiều nhất (13,2 GB, riêng
   bốn ISP quay số AOL, Prodigy, Netcom, CompuServe đã 4,7 GB), tiếp theo là host chỉ có IP (7,8 GB).
5. **Log dừng sớm**: request cuối cùng lúc 28/07 13:32:25, thiếu 3,4 ngày cuối tháng. Mọi tổng "theo tháng"
   phải ghi rõ điều này.

## Giới hạn

- Một host không phải một người: proxy của AOL/Prodigy gộp hàng nghìn người dùng vào vài host; cache của
  proxy cũng làm số request thấp hơn số lượt xem thật.
- Không có user agent, referrer: không tách được bot với người.
- Log dừng 28/07; nguyên nhân khoảng lặng 22 phút ngày 13/07 là suy đoán, log không ghi lý do.
- Dữ liệu năm 1995: nhịp truy cập và tỉ lệ ISP không đại diện cho web hiện nay; bài học là về cách xử lý log.
