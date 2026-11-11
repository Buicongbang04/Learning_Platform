# Lời giải: triage log

## Hướng làm

1. **Tách dòng**: regex `^(?P<service>…)-\d+\s+\|\s?(?P<payload>.*)$`; tên dịch vụ là phần trước `-<số>` (dùng nhóm
   lazy để `quillo-api-1` cũng ra đúng nếu project có gạch ngang). Dòng không khớp bị bỏ qua, không tính vào dịch vụ nào.
2. **Sự kiện**: `json.loads` payload; phải là object có `ts` parse được bằng `%Y-%m-%dT%H:%M:%S%z`, `level` và `msg` là
   chuỗi. Mọi trường hợp khác (`ValueError`, `KeyError`, `TypeError` khi payload là mảng) là dòng không đọc được.
3. **Sắp xếp theo thời gian thật** (`datetime` có múi giờ), không theo vị trí dòng: `docker compose logs` in theo khối
   từng container, xen kẽ tuỳ lúc.
4. **Nhóm**: dict theo (dịch vụ, level, msg) cho WARNING/ERROR/CRITICAL và (path, status) cho `request` có `status` ≥
   500; giữ datetime của `first`/`last` để so, nhưng xuất nguyên chuỗi `ts`. Xếp nhóm theo (datetime đầu, khoá).
5. **Đợt sự cố**: gom mọi sự kiện xấu (cả hai loại trên), xếp theo thời gian, mở đợt mới khi khoảng cách tới sự kiện
   xấu liền trước > 30 s.

Mã: `triage_logs.py` cạnh tệp này.

## Đọc kết quả của hai log thật

- `lab-morning`: đợt 1 (05:46:53–05:47:38) gồm `model server lỗi` ở api, 503 ở `/api/ask` và `/healthz`, worker
  `dịch vụ không với tới`: một dịch vụ model không chạy. Đợt 2 (05:48:30) chỉ có worker: `EOF marker not found` của
  pypdf rồi `nạp tài liệu lỗi`, một tệp PDF hỏng, nguyên nhân khác hẳn dù chỉ cách 52 s.
- `lab-evening`: đợt 1 (05:49:50–05:50:30) `database lỗi` rồi worker chờ; đợt 2 (05:51:21–05:52:27) `model server
  lỗi`. Ngưỡng 30 s tách được hai nguyên nhân; với ngưỡng 2 phút chúng thành một đợt và bạn sẽ đi tìm một nguyên nhân
  chung không tồn tại. Ngưỡng là quyết định của người phân tích, nên bài ghim nó trong đề.
- Cả hai log còn dòng `03:13` của lần khởi động lúc dựng snapshot: `window.first` vì vậy sớm hơn buổi sự cố vài giờ.
  Log thật của máy chạy lâu luôn có phần "đời trước" như vậy.

## Phương án khác

- Đọc từng dòng (streaming) với `heapq` để không giữ cả log trong RAM: cần khi log hàng GB; bài này vài trăm dòng.
- Gom thông điệp có biến (vd. tên tệp trong `msg`) theo mẫu: quillo đã tách biến ra trường riêng nên không cần.
