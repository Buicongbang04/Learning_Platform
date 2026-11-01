# Kế hoạch email cho olistmarket.com.br

## 1. Nguồn gửi thư

| Nguồn | Tên miền From | Envelope sender (Return-Path) | DKIM d= | Đạt DMARC alignment nhờ |
| --- | --- | --- | --- | --- |
| TODO | TODO | TODO | TODO | TODO |

## 2. Bản ghi DNS

```zone
$ORIGIN olistmarket.com.br.
$TTL 3600
; TODO: MX, SPF, DKIM, DMARC giai đoạn đầu, MTA-STS, TLS-RPT
```

## 3. Lộ trình DMARC

| Giai đoạn | Bản ghi _dmarc | Thời lượng | Điều kiện sang giai đoạn sau |
| --- | --- | --- | --- |
| TODO | TODO | TODO | TODO |

## 4. Giám sát và báo cáo

- TODO

## 5. Rủi ro và rollback

- TODO

## 6. Ngoài SPF, DKIM, DMARC

- TODO
