# Lời giải: cổng đăng ký model

`registry_gate.py` cạnh tệp này là bản tham khảo.

- **Tách luật thành hàm thuần.** `check_request` không đụng MLflow, nên kiểm được bằng bảng ca nhanh; `register_if_allowed` và
  `audit_registry` chỉ là lớp mỏng gọi nó. Cùng một bộ luật dùng cho cổng lúc đăng ký và cho audit, không có hai định nghĩa "hợp lệ".
- **Thứ tự ưu tiên lỗi.** `team-mismatch` và `permission` chỉ báo khi tên hợp lệ: tên sai thì không biết tiền tố là đội nào, báo thêm chỉ
  làm nhiễu. Kết quả sắp xếp để so được và để người đọc thấy ổn định giữa các lần chạy.
- **Không ghi gì khi bị từ chối.** Kiểm toàn bộ trước, ghi sau. Nếu tạo registered model trước rồi mới kiểm model card, bạn để lại một
  registered model rỗng mang tên của đội khác.
- **Audit tồn tại vì cổng có đường vòng.** Bất kỳ ai có quyền ghi vào MLflow đều gọi thẳng `create_model_version` được. Audit định kỳ
  bắt các version đó; về lâu dài, quyền ghi trực tiếp chỉ nên thuộc về service account của cổng.
- `client.create_model_version(...).version` là số nguyên ở MLflow 3; hàm trả `str` theo đề.

**Ép quyền thật.** Cổng trong code chỉ có giá trị khi registry từ chối mọi đường khác. Với MLflow tự host: bật basic auth app
(`mlflow server --app-name basic-auth`) và cấp quyền `MANAGE` trên registered model theo đội, người dùng bình thường chỉ `READ`; cổng chạy
bằng service account có quyền tạo. Với Databricks: Unity Catalog, mỗi đội một schema (`ml.pricing.*`), quyền `CREATE MODEL` theo nhóm.
Quy ước tên `<team>-...` trên MLflow đóng vai trò của schema đó.

**Mở rộng.** Thêm tag `data_classification` để cổng deploy từ chối đưa model huấn luyện trên dữ liệu PCI ra namespace không thuộc phạm vi
PCI; thêm hạn sử dụng cho model card (ngày review gần nhất).
