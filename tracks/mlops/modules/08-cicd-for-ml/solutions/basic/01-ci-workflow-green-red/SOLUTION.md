# Lời giải: workflow CI cho repo ML

Xem `ci.yml` cạnh tệp này. Ba điểm cần nhớ:

- **Đỏ phải thật sự đỏ.** Mỗi `run:` chạy với `bash -e`, nên lệnh thoát mã khác 0 làm bước fail, job fail, và `act` (như
  GitHub) thoát khác 0. Lỗi thường gặp là nuốt mã thoát (`ruff check ... || true`, `pytest ... ; echo done`): pipeline xanh
  vĩnh viễn. Bài này kiểm cả hai chiều chính vì lý do đó.
- **`needs` là cổng.** `build` chỉ chạy khi `lint` và `test` xanh; không có `needs`, ba job chạy song song và có thể đóng gói
  một bản lỗi.
- **Công cụ đến từ đâu.** Trên GitHub runner, bạn cài bằng một bước `setup-uv` rồi `uv sync --frozen`; bài này chép sẵn công cụ
  để chạy ngoại tuyến. Phần quan trọng là bản ghim: `ruff==0.17.1` và `pytest` cùng bản với môi trường, nên "xanh trên máy
  tôi" và "xanh trên CI" so được với nhau.

`PYTHONPATH=.ci-tools` đặt ở `env:` của bước, không phải `export` riêng, để biến chỉ có hiệu lực đúng bước cần nó.
