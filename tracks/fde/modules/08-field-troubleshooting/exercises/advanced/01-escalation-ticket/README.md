---
title: "Ticket escalation gửi đội sản phẩm"
level: advanced
services: []
files:
  - path: starter/escalation.md
    note: Khung ticket; bạn viết vào đây
run: []
---

## Mục tiêu

Không phải sự cố nào cũng sửa được ở hiện trường. Khi vấn đề nằm trong hành vi của sản phẩm, việc của bạn là chuyển cho
đội sản phẩm một ticket mà kỹ sư on-call đọc 30 giây là biết lỗi gì, tái hiện thế nào, ảnh hưởng tới đâu và bạn cần họ
trả lời câu gì, thay vì một tin nhắn "khách X kêu quillo không chạy, các anh xem giúp".

## Đề bài

Tình huống (hư cấu, dựng theo hành vi đã ghi trong mục API của [README sản phẩm](../../../../../product/README.md); các
dòng log dưới đây viết lại theo đúng định dạng log của quillo 1.0.0, không phải ghi từ máy khách):

- Khách: nhà máy dùng hồ sơ `factory` (Debian 12, 2 vCPU, 3 GB RAM, đường truyền xấu, proxy), quillo 1.0.0 cài bằng
  compose, model `llm-small`, nạp tài liệu bằng cách thả tệp vào `inbox/` qua thư mục chia sẻ.
- Thứ Hai 08:10, phòng chất lượng thả 46 quy trình sản xuất (PDF) vào inbox, trong đó `QT-SX-03-tong-hop-2024.pdf` là bản
  scan 280 trang có lớp chữ OCR. Tới 16:00 chỉ 3 tệp xếp trước nó theo tên vào `done/`, 42 tệp còn nằm
  nguyên, không tệp nào vào `failed/`. `/healthz` trả 200 cả ngày, hỏi về tài liệu cũ vẫn được.
- Bundle khách gửi có `quillo/logs/worker.log` với các dòng (rút gọn):

  ```text
  worker-1  | {"ts": "2026-11-09T08:12:41+0000", "level": "INFO", "logger": "quillo.ingest", "msg": "đã nạp tài liệu", "doc_id": "4be1…", "filename": "QT-SX-01-tiep-nhan-nguyen-lieu.pdf", "chunks": 14}
  worker-1  | {"ts": "2026-11-09T08:19:02+0000", "level": "WARNING", "logger": "quillo.ingest", "msg": "dịch vụ không với tới, để nguyên tệp và thử lại sau", "file": "QT-SX-03-tong-hop-2024.pdf", "error": "ReadTimeout('timed out')", "retry_s": 5.0}
  worker-1  | {"ts": "2026-11-09T08:24:13+0000", "level": "WARNING", "logger": "quillo.ingest", "msg": "dịch vụ không với tới, để nguyên tệp và thử lại sau", "file": "QT-SX-03-tong-hop-2024.pdf", "error": "ReadTimeout('timed out')", "retry_s": 10.0}
  … (lặp lại với retry_s 20, 40, rồi 60 tới hết ngày, luôn cùng tệp)
  ```

- Bạn đã kiểm qua khách: `docker stats --no-stream` cho thấy `embed` dùng ~195% CPU trong lúc worker chờ; `free -m`
  còn ~600 MB available; `df -h` còn 6 GB; `curl` tới `/healthz` 200. IT khách đã khởi động lại worker một lần, không đổi.
  Bạn tạm gỡ khách bằng cách chuyển tệp lớn ra khỏi inbox; 42 tệp còn lại nạp xong trong 25 phút.

Viết `starter/escalation.md` gửi đội sản phẩm quillo. Bạn **nên** tái hiện ở lab trước khi viết (vd. trên `lab-open`
với snapshot `07-customer-integration-quillo`: một tệp văn bản đủ lớn và `QUILLO_HTTP_TIMEOUT_S` nhỏ qua một tệp compose
ghép thêm cho `worker`), và đính kèm cách tái hiện đó vào ticket. Không có test tự động; tự chấm theo rubric dưới đây,
bài mẫu và rubric chi tiết ở `solutions/`. Độ dài: đội sản phẩm đọc được trong 5 phút (~600–900 từ, chưa tính khối
lệnh/log).

## Tiêu chí đạt

Rubric 20 điểm, đạt khi ≥ 15 và **không** có lỗi loại trừ:

| Tiêu chí | Điểm |
| --- | --- |
| Tiêu đề và đoạn đầu nêu chữ ký lỗi và hành vi sai (một tệp làm cả hàng đợi đứng), không nêu tên khách làm chủ đề | 3 |
| Phiên bản và môi trường đủ để dựng lại: bản phát hành, image/digest hoặc tag, OS, CPU/RAM, cấu hình khác mặc định | 3 |
| Cách tái hiện chạy được trên máy sạch không cần dữ liệu khách (lệnh hoặc script), kết quả mong đợi và kết quả thực tế | 4 |
| Bằng chứng trích đúng nguồn, đã che secret và không chứa dữ liệu nghiệp vụ của khách | 3 |
| Tách sự thật đã kiểm, giả thuyết, và những gì đã loại trừ (tài nguyên, mạng, restart) | 3 |
| Ảnh hưởng, mức độ có lý do, workaround đang dùng và giới hạn của nó | 2 |
| Câu hỏi/yêu cầu cụ thể cho đội sản phẩm (quyết định cần có, thông tin cần trả lời), không áp đặt cách sửa | 2 |

Lỗi loại trừ: đính kèm tài liệu hay đoạn nội dung của khách; có secret, token hay địa chỉ nội bộ không che; kết luận "lỗi
của khách" hay "lỗi của sản phẩm" mà không có bằng chứng; không có cách tái hiện và cũng không nói vì sao chưa tái hiện
được.

## Gợi ý

### Gợi ý 1

Đọc mục API của README sản phẩm, đoạn về worker, như kỹ sư on-call sẽ đọc: hành vi bạn thấy là lỗi, là giới hạn đã biết,
hay cả hai? Ticket nói rõ bạn xếp nó vào đâu và vì sao vẫn gửi.

### Gợi ý 2

Tái hiện nhỏ nhất thường không giống hiện trường: bạn không cần 280 trang PDF, bạn cần điều kiện làm một lời gọi
vượt thời gian chờ.

### Gợi ý 3

Viết câu cuối của ticket trước: "Mình cần đội trả lời …". Rồi chỉ giữ lại những gì giúp họ trả lời câu đó.
