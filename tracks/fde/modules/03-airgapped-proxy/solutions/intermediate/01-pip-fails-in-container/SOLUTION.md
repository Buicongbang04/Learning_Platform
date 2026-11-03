# Lời giải: pip trong container báo lỗi chứng chỉ

## Nguyên nhân (đo trên `hospital`, 2026-11-04)

IT nói đúng: máy **đã** tin CA của proxy. Nhưng `RUN pip install` không chạy "trên máy", nó chạy trong một container
dựng từ `python:3.12.14-slim-bookworm`, có hệ điều hành và **trust store riêng** (`/etc/ssl/certs` của Debian trong image).
Container không thừa hưởng gì của máy chủ: không CA, không `/etc/environment`. `build.sh` của team đã truyền biến proxy
qua `--build-arg` (bài học từ khách trước), nên gói tin đi tới proxy được; proxy soi TLS và trình chứng chỉ do CA bệnh
viện ký, mà trust store trong image không có CA đó ⇒ `CERTIFICATE_VERIFY_FAILED`.

Có hai tầng, và tầng thứ hai chỉ lộ ra sau khi sửa tầng thứ nhất:

| Tầng | Chương trình | Đọc danh sách CA ở đâu | Triệu chứng |
| --- | --- | --- | --- |
| Build | pip 25 (Python 3.12) | Mặc định dùng `truststore` ⇒ trust store **hệ thống của image** | `pip install` lỗi như ticket |
| Chạy | `requests` 2.34 | `certifi` (bundle Mozilla đóng kèm gói), **không** đọc trust store hệ thống | Sau khi thêm CA vào image và `update-ca-certificates`: build qua, `run.sh` lỗi `requests.exceptions.SSLError … CERTIFICATE_VERIFY_FAILED` |

Đã kiểm cả hai: starter trên `hospital` lỗi ở pip; bản chỉ thêm CA + `update-ca-certificates` thì build được nhưng `run.sh`
lỗi ở `requests`.

## Sửa

`build.sh` dựng một build context tạm, chép vào đó mọi CA mà IT đã cài vào máy theo cách của Debian/Ubuntu
(`/usr/local/share/ca-certificates/*.crt`, kiểm từng tệp bằng `openssl x509`); `Dockerfile`:

```dockerfile
COPY site-ca/ /usr/local/share/ca-certificates/site/
RUN update-ca-certificates
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
```

- `update-ca-certificates` gộp CA bệnh viện vào bundle hệ thống của image (vẫn giữ các CA công cộng).
- `REQUESTS_CA_BUNDLE` bắt `requests` dùng bundle đó thay cho `certifi`; `SSL_CERT_FILE` cho `ssl`/`urllib`/`httpx`
  của Python; `PIP_CERT` để pip không phụ thuộc việc `truststore` có bật hay không ở bản pip khác.
- Ở `lab-open` thư mục `site-ca/` rỗng: `COPY` không chép gì, image dùng đúng các CA công cộng. Không có gì riêng của
  bệnh viện viết cứng trong tệp.
- Kiểm chứng chỉ vẫn bật: test chạy `requests` trong image tới một server chứng chỉ tự ký, phải bị từ chối.

## Các cách khác và đánh đổi

| Cách | Được | Mất |
| --- | --- | --- |
| CA vào image lúc build (lời giải) | Đơn giản, chạy với builder cũ (Docker 26 của Ubuntu 20.04 không có buildx) | Image mang CA của bệnh viện: dùng lại ở khách khác thì tin thêm một CA lạ. Build lại theo từng site, hoặc tách lớp CA cuối cùng |
| BuildKit `--secret id=ca,src=…` + `RUN --mount=type=secret` cho bước pip, mount bundle của máy lúc chạy (`-v /etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro`) | Image sạch, dùng được mọi khách; CA đổi thì không cần build lại | Cần buildx (máy này không có, không có mạng để cài thì phải mang theo); lệnh chạy phải nhớ mount |
| `pip --trusted-host`, `verify=False`, `PYTHONHTTPSVERIFY=0` | Chạy ngay | Mọi kẻ đứng giữa đều được tin, kể cả khi proxy đổi hay bị chiếm. Không bao giờ |
| Xin IT cho `pypi.org`, `files.pythonhosted.org` đi thẳng không soi TLS (bypass list) | Không đụng image | Cần IT/Security duyệt, thường mất ngày; đáng xin cho lâu dài, không chờ được trong ngày cài |

## Lỗi hay gặp

- Thêm CA vào image nhưng quên `update-ca-certificates`: tệp nằm đó, không ai đọc.
- Đặt `REQUESTS_CA_BUNDLE` trỏ vào **chỉ** tệp CA bệnh viện: chạy được sau proxy, nhưng image đó sang khách không soi TLS
  thì mọi HTTPS đều lỗi (bundle không còn CA công cộng nào).
- `pip install --cert hospital.pem` trong `Dockerfile`: sửa được pip, quên `requests` lúc chạy, và đường dẫn chỉ đúng ở
  một khách.
- Biến proxy đặt bằng `ENV` trong Dockerfile: image mang proxy của bệnh viện tới mọi nơi chạy nó. `--build-arg
  http_proxy…` là build-arg định sẵn của Docker, không lưu vào image.
