# Lời giải: ký model và cổng deploy

`signing.py` cạnh tệp này là bản tham khảo.

- **Ký cả thư mục.** model-signing băm từng tệp rồi ký manifest (tên tệp và hash), bọc trong DSSE envelope theo định dạng bundle của
  Sigstore. Verify phát hiện sửa byte, thêm, xoá, đổi tên tệp. Ký riêng tệp trọng số là không đủ: tokenizer, cấu hình tiền xử lý, code
  tuỳ biến cũng quyết định dự đoán.
- **Không bật `ignore_unsigned_files`.** Tuỳ chọn này (CLI `--ignore_unsigned_files`, API `set_ignore_unsigned_files`) cho verify bỏ qua
  tệp không có trong manifest: kẻ tấn công thêm `preprocess.pkl` mà serving nạp, verify vẫn qua. Tương tự, mặc định model-signing bỏ qua
  đường dẫn git (`.git`, `.gitattributes`); đừng để serving nạp gì từ đó.
- **Chữ ký ngoài thư mục.** Nằm trong thư mục, chữ ký thành một tệp "thừa" khi verify (hoặc phải cấu hình bỏ qua, mở thêm một khe).
- **Fail closed với mọi lỗi.** Thư viện ném `ValueError` khi không khớp, nhưng thiếu tệp là `FileNotFoundError`, JSON hỏng là
  `JSONDecodeError`, cấu trúc lạ có thể là `KeyError` hay lỗi khác. `except ValueError` thì một tệp chữ ký hỏng làm cổng **crash**; nếu
  pipeline coi crash của bước kiểm là "bỏ qua bước", model đi qua. Bắt mọi `Exception` và trả `False`.
- **Ký và quét là hai câu hỏi.** Ca "ký đúng nhưng chứa payload" mô phỏng pipeline huấn luyện bị chiếm (dependency độc, model gốc độc):
  chữ ký chứng minh nguồn gốc, không chứng minh vô hại. Ngược lại, quét sạch không chứng minh model chưa bị thay. Cổng gọi cả hai và báo
  đủ lý do để người trực biết phải xử lý cả hai chuyện.

**Quản lý khoá.** Khoá riêng chỉ ở trong hệ thống ký của CI (KMS hay HSM, không bao giờ trên laptop); cổng deploy chỉ cần khoá công khai,
phát qua cấu hình có kiểm soát thay đổi. Khoá lộ: thu hồi (cổng ngừng tin khoá cũ), sinh khoá mới, ký lại các model còn hiệu lực sau khi
kiểm lại chúng, và rà các model đã ký trong khoảng thời gian khoá có thể đã lộ.

**Sigstore keyless (tuỳ chọn, cần mạng).** Thay vì tự giữ khoá, người ký đăng nhập OIDC (Google, GitHub Actions); Fulcio cấp chứng chỉ
ngắn hạn gắn danh tính đó; chữ ký được ghi vào log minh bạch Rekor. Cổng verify theo **danh tính** ("ký bởi workflow `train.yml` của repo
X") thay vì theo khoá. Thử ngoài bài, trên máy có mạng:

```bash
uv run python -m model_signing sign sigstore ./model --signature model.sig
uv run python -m model_signing verify sigstore ./model --signature model.sig \
  --identity you@example.com --identity_provider https://accounts.google.com
```

Không cần cho test của module, và lệnh ký mở trình duyệt để đăng nhập.
