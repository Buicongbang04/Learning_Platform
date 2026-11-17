# Lời giải: ticket escalation gửi đội sản phẩm

## Hướng làm

1. **Xếp loại trước khi viết.** README sản phẩm (mục API) ghi rõ: lỗi transport (`httpx.TransportError`, gồm
   `ReadTimeout`) được coi là sự cố hạ tầng, worker để nguyên tệp, dừng lượt quét và chờ lùi dần; "Giới hạn đã biết: tệp
   **luôn** gây lỗi kết nối … giữ cả hàng đợi". Vậy đây vừa là giới hạn đã biết, vừa là hành vi gây sự cố sev2 ở khách
   có CPU yếu. Ticket không giả vờ phát hiện lỗi mới; nó đưa bằng chứng rằng giới hạn này xảy ra ở cấu hình phần cứng
   tối thiểu mà `REQUIREMENTS.yaml` chấp nhận (2 CPU), và xin một quyết định.
2. **Loại trừ hạ tầng bằng số liệu khách đã đưa**: CPU của `embed` bão hoà (đang làm việc, không chết), RAM và đĩa còn,
   `/healthz` 200, restart worker không đổi gì, gỡ tệp lớn thì 42 tệp còn lại vào trong 25 phút. Mạng xấu của nhà máy
   không liên quan: worker gọi `embed` trong mạng bridge của compose, không đi qua NIC có netem.
3. **Tái hiện nhỏ nhất**: không cần PDF 280 trang. Điều kiện là một lời gọi embed vượt `QUILLO_HTTP_TIMEOUT_S`. Trên
   `lab-open` (snapshot `07-customer-integration-quillo`), đặt timeout 2 s cho riêng worker bằng tệp compose ghép thêm,
   thả một tệp văn bản lớn (~1,4 MB) và một tệp nhỏ xếp sau nó. Đã chạy ngày 2026-11-11: sau 75 s worker log 4 cảnh báo
   `ReadTimeout('timed out')` cho tệp lớn với `retry_s` 5 → 10 → 20 → 40, tệp nhỏ vẫn nằm trong inbox, `done/` và
   `failed/` rỗng.
4. **Câu hỏi cho đội**: quyết định hành vi (đếm timeout theo tệp và đẩy vào `failed/` sau N lần? embed theo lô nhỏ hơn?
   timeout riêng cho embed khi nạp?), có đưa `QUILLO_HTTP_TIMEOUT_S` vào `compose.yaml` để khách chỉnh không, và hướng
   dẫn tạm thời cho khách CPU yếu. Không áp đặt cách sửa.

## Bài mẫu (đạt 20/20)

```markdown
# Worker dừng cả hàng đợi khi một tệp lớn làm lời gọi embed vượt QUILLO_HTTP_TIMEOUT_S (ReadTimeout lặp vô hạn)

**Mức độ đề xuất:** sev2 — nạp tài liệu dừng hoàn toàn với một khách sản xuất cho tới khi có người can thiệp tay; hỏi
đáp tài liệu cũ vẫn chạy, có workaround thủ công.

## Tóm tắt

Trên máy 2 vCPU, một tệp có nhiều chunk làm một lời gọi `POST /v1/embeddings` (lô 16 chunk) vượt timeout HTTP của worker
(mặc định 300 s). `ingest.classify` xếp `ReadTimeout` vào "outage", nên worker để nguyên tệp, dừng lượt quét và thử lại
**cùng tệp** mãi (backoff tới 60 s). Mọi tệp xếp sau nó theo tên không bao giờ được nạp; không tệp nào vào `failed/`,
`/healthz` vẫn 200. README sản phẩm ghi đây là giới hạn đã biết; ticket này đưa bằng chứng nó xảy ra ở cấu hình tối
thiểu được hỗ trợ và xin quyết định về hành vi.

## Phiên bản và môi trường

- quillo 1.0.0 (bundle `quillo-1.0.0.tar`), compose, model `llm-small`, `nomic-embed-text-v1.5.Q8_0`,
  `QUILLO_EMBED_THREADS=2`, `QUILLO_HTTP_TIMEOUT_S` mặc định (300).
- Khách: Debian 12, 2 vCPU, 3 GB RAM (đạt `min_cpus: 2` của REQUIREMENTS.yaml, thấp hơn `min_mem_mb: 4096`), Docker CE
  29.9.2 + compose 5.6.1. Khác mặc định: proxy công ty, đường truyền xấu (không ảnh hưởng đường worker → embed trong
  mạng compose).
- Lab tái hiện: Ubuntu 22.04, 2 vCPU, 3 GB, quillo 1.0.0 từ cùng bundle.

## Cách tái hiện

Trên máy đang chạy quillo 1.0.0 bằng compose (thư mục cài `~/quillo-1.0.0`, có sudo để ghi inbox của uid 10001):

    cd ~/quillo-1.0.0
    printf 'services:\n  worker:\n    environment:\n      QUILLO_HTTP_TIMEOUT_S: "2"\n' > compose.timeout.yaml
    docker compose -f compose.yaml -f compose.timeout.yaml up -d worker
    python3 -c "import random; print(' '.join('Buoc %d: kiem tra nguyen lieu lo %d.' % (i, random.randint(1, 9999)) for i in range(40000)))" > /tmp/a-lon.txt
    printf 'Quy trinh nho.\n' > /tmp/b-nho.txt
    sudo install -o 10001 -g 10001 -m 0644 /tmp/a-lon.txt inbox/a-lon.txt
    sudo install -o 10001 -g 10001 -m 0644 /tmp/b-nho.txt inbox/b-nho.txt
    sleep 75; docker compose logs --since 2m worker; sudo ls inbox inbox/done inbox/failed

Timeout 2 s thay cho 300 s chỉ để rút ngắn thời gian; ở khách lời gọi thật vượt 300 s.

## Kết quả mong đợi và thực tế

- Mong đợi: một tệp hỏng/quá nặng không chặn các tệp khác; tệp đó được báo lỗi rõ và (sau N lần) vào `failed/`.
- Thực tế (lab, 2026-11-11, 75 s): 4 cảnh báo `dịch vụ không với tới…` cho `a-lon.txt`, `ReadTimeout('timed out')`,
  `retry_s` 5 → 10 → 20 → 40; `b-nho.txt` vẫn trong inbox; `done/`, `failed/` rỗng. Ở khách: 8 giờ, 42 tệp chờ.

## Bằng chứng

Từ `quillo/logs/worker.log` trong bundle của khách (đã che secret; tên tệp là tên quy trình, không phải nội dung):

    {"ts": "2026-11-09T08:19:02+0000", "level": "WARNING", "msg": "dịch vụ không với tới, để nguyên tệp và thử lại sau", "file": "QT-SX-03-tong-hop-2024.pdf", "error": "ReadTimeout('timed out')", "retry_s": 5.0}
    … lặp với retry_s 10, 20, 40, 60 tới 16:00, luôn cùng tệp

`docker stats --no-stream` lúc đó: `quillo-embed-1` ~195% CPU. `free -m`: ~600 MB available. `df -h /`: còn 6 GB.

## Đã kiểm và đã loại trừ

- Sự thật: embed đang làm việc (CPU bão hoà), không chết; RAM, đĩa còn; `/healthz` 200; restart worker không đổi gì;
  bỏ tệp lớn khỏi inbox thì 42 tệp còn lại nạp xong trong 25 phút.
- Loại trừ: mạng/proxy của nhà máy (worker → embed nằm trong mạng compose), DB (không có lỗi database trong log).
- Giả thuyết (chưa kiểm): tệp 280 trang có chunk dài bất thường từ lớp OCR, làm một lô 16 chunk nặng hơn nhiều so với
  trung bình. Chưa đo thời gian một lô cụ thể ở khách.

## Ảnh hưởng và workaround

Một khách sản xuất (thử nghiệm 40 người) không nạp được tài liệu mới trong 8 giờ làm việc. Workaround đang dùng: IT khách
chuyển tệp lớn ra khỏi inbox bằng tay, rồi cắt nhỏ. Giới hạn: khách phải tự nhận ra (không có cảnh báo, `/healthz` xanh)
và biết tệp nào là thủ phạm (phải đọc log).

## Cần đội sản phẩm

1. Quyết định hành vi mong muốn khi **cùng một tệp** gây lỗi transport lặp lại: có đếm theo tệp và đẩy vào `failed/` sau
   N lần như lỗi 5xx không, hay giữ nguyên và chỉ ghi tài liệu?
2. `QUILLO_HTTP_TIMEOUT_S` có nên được truyền qua `compose.yaml`/values của chart để khách CPU yếu chỉnh mà không cần tệp
   ghép thêm?
3. Có cần một tín hiệu cho vận hành (metric số tệp chờ, tuổi tệp cũ nhất trong inbox) để không phải đợi người dùng phát
   hiện?
```

## Rubric chi tiết

| Tiêu chí | Đủ điểm khi | Mất điểm khi |
| --- | --- | --- |
| Tiêu đề, đoạn đầu (3) | Nêu cơ chế (một tệp → cả hàng đợi đứng) và chữ ký (`ReadTimeout`, `dịch vụ không với tới`) | "Lỗi ở khách nhà máy", "worker bị treo" chung chung |
| Phiên bản, môi trường (3) | Bản, model, CPU/RAM, timeout, chỗ khác mặc định | Thiếu CPU (yếu tố quyết định) hay bản phát hành |
| Tái hiện (4) | Lệnh chạy được trên máy sạch, không dữ liệu khách, có mong đợi vs thực tế | Chỉ "thả một PDF lớn", hoặc cần tệp của khách |
| Bằng chứng (3) | Dòng log nguyên văn kèm nguồn, đã che; số liệu tài nguyên | Đính kèm cả bundle, hay nội dung tài liệu |
| Sự thật/giả thuyết/loại trừ (3) | Ba phần tách bạch, mỗi loại trừ có số liệu | Trộn suy đoán vào sự thật |
| Ảnh hưởng, workaround (2) | Ai, bao lâu, workaround và giới hạn | Không có, hay phóng đại thành sev1 |
| Yêu cầu cụ thể (2) | Câu hỏi quyết định, không áp đặt patch | "Sửa gấp giúp", hay ra lệnh cách sửa |

Bài mẫu ở trên: mọi phần có mặt, tái hiện đã chạy thật trên `lab-open`, không có nội dung tài liệu của khách (chỉ tên
tệp quy trình, IT khách đã đồng ý đưa vào ticket), không secret, ~800 từ.
