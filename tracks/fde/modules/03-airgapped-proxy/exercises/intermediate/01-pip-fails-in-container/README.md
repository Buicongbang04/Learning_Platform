---
title: "Hiện trường: pip trong container báo lỗi chứng chỉ"
level: intermediate
services: []
files:
  - path: starter/build.sh
    note: Script build image của team, bạn sửa
  - path: starter/Dockerfile
    note: Bạn sửa
  - path: starter/run.sh
    note: Chạy image với một URL, sửa nếu cần
  - path: starter/fetch.py
    note: App tải một URL và in sha256 (không cần sửa)
  - path: starter/requirements.txt
    note: Phụ thuộc đã ghim kèm hash (không sửa)
  - path: tests/test_pip_in_container.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lab-open
  - nice -n 15 uv run python -m fdekit prepare hospital
  - uv run pytest tracks/fde/modules/03-airgapped-proxy/exercises/intermediate/01-pip-fails-in-container -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Một ticket thật, không kèm chẩn đoán, và IT khách tin rằng phía họ đã làm đủ. Bạn tự tái hiện trên máy khách, tìm
nguyên nhân, sửa sao cho cùng bộ tệp chạy được ở cả máy lab lẫn máy bệnh viện, và **không** đổi lấy việc chạy được bằng
cách tắt kiểm chứng chỉ.

## Đề bài

`starter/` là một công cụ nhỏ team bạn dùng ở nhiều khách: `fetch.py` tải một URL HTTPS bằng `requests` và in JSON
(`sha256`, số byte, phiên bản `requests`). `build.sh` dựng image `fetcher:1` từ `Dockerfile`, `run.sh <url>` chạy nó.
Trên máy lab (`lab-open`) cả hai script chạy tốt.

Ticket từ bệnh viện (máy `hospital`):

> Bên em đã làm theo checklist: cài chứng chỉ gốc của bệnh viện vào máy, cấu hình proxy cho Docker. Trên máy, `curl
> https://pypi.org` chạy bình thường, `docker pull` cũng được. Nhưng chạy `sh build.sh` thì dừng ở bước pip:
>
> ```text
> WARNING: Retrying (Retry(total=0, ...)) after connection broken by 'SSLError(SSLCertVerificationError(1, '[SSL:
> CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)'))':
> /simple/certifi/
> ERROR: Could not find a version that satisfies the requirement certifi==2026.7.22
> ```
>
> Máy đã tin chứng chỉ rồi mà sao vẫn báo lỗi chứng chỉ?

Sửa các tệp trong `starter/` (giữ nguyên cách gọi `sh build.sh` và `sh run.sh <url>`, giữ tên image `fetcher:1`). Test chạy
cùng kịch bản trên `lab-open` và trên `hospital`, mỗi máy một VM, bằng user `fde` (trong nhóm `docker`, không sudo):

1. Trên `hospital`, làm đúng những gì IT nói đã làm (CA vào trust store hệ thống, proxy cho Docker daemon) và kiểm `curl
   https://pypi.org` trên máy chạy được.
2. Chép 5 tệp vào `/home/fde/fetcher/`, chạy `sh /home/fde/fetcher/build.sh`.
3. Chạy `sh /home/fde/fetcher/run.sh <url>` với một tệp ngẫu nhiên trên `files.pythonhosted.org`.

Bài cần máy bạn ra internet (Docker Hub, PyPI); không có mạng thì test skip. Tự boot máy để điều tra:
`with fdekit.customer_site("hospital") as s:`, CA của proxy ở `s.proxy_ca`; các lệnh "IT đã làm" nằm trong
`tests/test_pip_in_container.py` (`IT_SETUP`).

## Tiêu chí đạt

`test_build_and_fetch[lab-open]` và `test_build_and_fetch[hospital]`, trên mỗi máy:

- `build.sh` thoát `0` trong 240 s.
- `run.sh <url>` thoát `0` trong 90 s; dòng JSON cuối cùng của stdout có `sha256` đúng của tệp và `requests` là `2.34.2`.
- Image `fetcher:1` vẫn **kiểm chứng chỉ**: chạy `python -c "import requests; requests.get('https://10.0.2.15:18443/')"`
  trong image (không proxy) tới một server dùng chứng chỉ tự ký lạ phải lỗi `CERTIFICATE_VERIFY_FAILED`.

`test_learner_files_keep_tls_verification`: không tệp nào trong 5 tệp chứa cách tắt kiểm chứng chỉ: `verify=False`,
`trusted-host`/`trusted_host`, `PYTHONHTTPSVERIFY`, `--insecure`, `CERT_NONE`, `check_hostname = False`, hay đặt
`REQUESTS_CA_BUNDLE`/`CURL_CA_BUNDLE` thành rỗng.

## Gợi ý

### Gợi ý 1

Tái hiện trước, trên VM `hospital`, sau khi chạy đúng các lệnh `IT_SETUP`. Rồi so: lệnh nào chạy được trên máy, lệnh "giống
hệt" nào không chạy được, và chúng khác nhau ở **đâu** chúng chạy.

### Gợi ý 2

Khi bước build qua được, đừng dừng: chạy `run.sh` rồi đọc kỹ traceback. Hai thư viện cùng nói HTTPS trong một image
không nhất thiết hỏi cùng một nơi xem nên tin ai.

### Gợi ý 3

Cùng bộ tệp phải chạy ở `lab-open`, nơi không có proxy hay CA lạ nào. Lời giải tốt không chứa thứ gì riêng của bệnh viện
được viết cứng trong tệp.
