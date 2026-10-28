# Lời giải: Masking, pseudonymization và tokenization

## Cách làm

- **`mask_email`** dùng `str.partition("@")`: nếu không có `@` hoặc phần local rỗng thì không còn gì
  hợp lệ để giữ, trả `"***"`. Giữ nguyên domain vì nó có ích cho phân tích (tỉ lệ gmail, email doanh nghiệp)
  mà gần như không định danh.
- **`mask_phone`** chuẩn hoá về chữ số trước (`re.sub(r"\D", "", ...)`) để không phụ thuộc định dạng
  `(11) 98765-4321` hay `11987654321`, rồi giữ 4 số cuối, đủ để CSKH xác nhận "số đuôi 4321".
- **`pseudonymize`** dùng **HMAC-SHA256** chứ không phải SHA-256 trần. Không gian `customer_id`, số điện
  thoại, CPF đủ nhỏ hoặc đủ đoán được để brute-force hash trần; với HMAC, kẻ tấn công cần thêm secret key.
  Kết quả deterministic nên các bảng pseudonymize bằng cùng key vẫn join được với nhau.
- **`Tokenizer`**: token sinh từ HMAC nên cùng giá trị luôn ra cùng token (không phình vault, join được).
  Vault lưu **ciphertext Fernet** chứ không lưu plaintext: lộ bản dump vault mà không có Fernet key thì
  vẫn an toàn. `detokenize` để `KeyError` tự nổi lên khi token lạ.
- **`mask_dataframe`** bắt đầu bằng `df.copy()` để không có side effect, ánh xạ action → hàm qua dict, và
  báo lỗi rõ ràng với action lạ (fail closed: không lặng lẽ để lọt cột PII chưa che).

## Vì sao

| Kỹ thuật | Đảo ngược | Dùng khi |
| --- | --- | --- |
| Partial masking | Không | Hiển thị cho CSKH, dashboard |
| HMAC pseudonym | Không (cần key + brute-force) | Phân tích theo khách, join giữa bảng |
| Tokenization + vault | Có, chỉ service có Fernet key | Thanh toán, cần lấy lại giá trị gốc |

Ở production: key lấy từ secret manager/KMS, có rotation; vault là một service riêng có audit log thay vì dict.
