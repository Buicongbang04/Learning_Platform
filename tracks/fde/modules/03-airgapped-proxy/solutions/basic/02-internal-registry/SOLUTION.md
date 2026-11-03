# Lời giải: đẩy image vào registry nội bộ của khách

Lần push đầu tiên trên máy staging chưa cấu hình gì:

```text
The push refers to repository [10.0.2.101:5000/tools/hello-ab12]
Get "https://10.0.2.101:5000/v2/": http: server gave HTTP response to HTTPS client
```

Docker chỉ nói HTTP thường với registry nằm trong `127.0.0.0/8`/`::1`; mọi registry khác phải là HTTPS có chứng chỉ hợp
lệ, **trừ** khi được khai trong `insecure-registries`. Registry của công ty luật chạy HTTP và ta không sửa được phía nó,
nên lời giải khai đúng một mục `"insecure-registries": ["10.0.2.101:5000"]`.

## Hai cách, và cái giá

| | `insecure-registries` | Registry có TLS (CA nội bộ của khách) |
| --- | --- | --- |
| Việc phía khách | Không có | IT cấp chứng chỉ cho registry, bật TLS |
| Việc trên mỗi máy Docker | Sửa `daemon.json` + **restart daemon** | Đặt CA vào `/etc/docker/certs.d/10.0.2.101:5000/ca.crt`; Docker đọc thư mục này mỗi lần kết nối, **không** cần restart |
| Rủi ro | Image đi trên mạng không mã hoá, không xác thực máy chủ: ai chen được vào mạng nội bộ thì thay được image | Như registry công cộng |
| Hợp khi | Staging, mạng cô lập, tạm thời; ghi rõ trong biên bản bàn giao | Production, nhiều máy, khách có PKI |

Khuyến nghị gửi khách: dùng `insecure-registries` cho staging **có ghi nhận rủi ro bằng văn bản**, đề nghị bật TLS trước
production; khi đó chỉ cần chép `ca.crt`, không phải restart Docker ở từng máy. Không bao giờ khai cả dải
(`10.0.0.0/8`, `0.0.0.0/0`): mọi registry giả mạo trong dải đó cũng được tin.

## Các bước trong `publish.sh`

1. Kiểm đầu vào (root, tệp đọc được, `host:port`, `repo:tag`).
2. Đọc `daemon.json` bằng `python3` (có sẵn trên Ubuntu, máy không có mạng để cài `jq`), thêm registry vào danh sách đang có
   nếu chưa có, giữ mọi khoá khác. So **nội dung JSON** (không so byte) với bản cũ: giống thì không ghi, không restart.
   Khác thì lưu bản `.bak` có dấu thời gian, ghi bản mới vào tệp tạm rồi `mv` (không bao giờ để `daemon.json` ghi dở), restart
   Docker. Restart lỗi ⇒ tự chép `.bak` về, restart lại, báo lỗi rõ. IT đã bật `live-restore`, nên container đang chạy sống
   qua lần restart daemon; không có `live-restore` thì restart Docker là downtime (script in cảnh báo), phải xin cửa sổ bảo
   trì.
3. Kiểm daemon đã nhận registry (`docker info` → `IndexConfigs`) và registry trả lời `/v2/` trước khi load/push.
4. `docker load` (lỗi ⇒ in nguyên văn output của Docker rồi dừng), lấy tên image từ dòng `Loaded image:` (không đoán từ tên tệp), `docker tag` sang
   `10.0.2.101:5000/<repo:tag>`, `docker push`. Lần chạy thứ hai: load/tag/push lại cùng nội dung, registry đã có các blob nên
   push chỉ xác nhận digest.

## Lỗi hay gặp

- Ghi đè `daemon.json` bằng `echo '{"insecure-registries": [...]}' >`: mất cấu hình log của IT; với `log-opts` mất, log
  container lại phình đầy đĩa vài tuần sau và không ai nối được hai việc với nhau.
- Thêm registry mà quên restart: `docker info` vẫn không thấy, push vẫn lỗi y như cũ.
- JSON sai cú pháp (dấu phẩy thừa) ⇒ `dockerd` không khởi động lại được, **mọi** container không có `live-restore` đều
  dừng. Vì vậy ghi bằng `json.dump`, giữ `.bak`, và kiểm `systemctl is-active docker` ngay sau restart.
- Push lên `localhost:5000` qua một tunnel `socat`/SSH để né cấu hình: chạy được trên một máy, nhưng mọi máy khác của khách
  không kéo được image theo tên đó.
