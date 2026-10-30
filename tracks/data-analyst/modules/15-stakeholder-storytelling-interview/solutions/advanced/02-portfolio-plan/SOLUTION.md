# Lời giải tham khảo: kế hoạch portfolio và công cụ tự kiểm repo

## `audit_project`: hướng làm

```python
root = Path(path)
readme = root / "README.md"
headings = [line[3:].strip().lower() for line in text.splitlines() if line.startswith("## ")]
for f in root.rglob("*"):
    rel = f.relative_to(root)
    if not f.is_file() or any(part in SKIP_DIRS for part in rel.parts):
        continue
    ...
return sorted(problems)
```

Các quyết định đáng chú ý:

- **Chỉ heading cấp 2**: `line.startswith("## ")` loại `### ` tự nhiên (ký tự thứ ba là `#`, không phải khoảng trắng).
- **Bỏ `.git` theo `parts`**, không theo chuỗi con (`"my.git.notes/"` không phải thư mục git).
- **Mẫu secret có ba loại**: định dạng key đã biết (`sk-...`, `AKIA...`) và phép gán chuỗi cứng cho tên nghe như bí mật.
  Đọc key từ `os.environ` hay `os.getenv` là cách đúng, không bị báo. Mẫu bắt cả key trong notebook (JSON), chỗ hay bị lộ
  nhất vì output và source cùng commit.
- **`.env` không có đuôi** (`Path(".env").suffix == ""`): kiểm theo tên, không theo đuôi.
- **Sort kết quả** để đầu ra ổn định, dễ so trong CI.

Công cụ này là một **pre-commit check** nhỏ. Trong thực tế dùng thêm công cụ chuyên dụng (`gitleaks`, `detect-secrets`,
`nbstripout` của module 04) và luôn **thu hồi** key đã lỡ commit, vì xoá khỏi commit mới không xoá khỏi lịch sử git.

Bản tham chiếu (kiểm trong scratch, không commit) qua cả 6 test của hàm và 3 test của kế hoạch.

## Kế hoạch portfolio: điều làm nên một bản tốt

- **Vai trò mục tiêu có bằng chứng**: "8/8 tin yêu cầu SQL, 5/8 Power BI" thay vì "DA cần SQL". Khoảng trống được gọi tên và
  có việc lấp (dự án dùng Power BI, khoá cụ thể).
- **Ba dự án, mỗi dự án một câu hỏi có quyết định**: ví dụ cắt mã hàng an toàn (Online Retail II, CC BY 4.0), dự báo doanh số
  8 tuần (predicting sales trends), phân khúc khách hàng và đề xuất chăm sóc (customer segmentation). Dữ liệu có giấy phép
  rõ; với dữ liệu competition Kaggle, ghi rõ chỉ đăng code và kết quả.
- **Mỗi dự án thể hiện một kỹ năng khác nhau** khớp tin tuyển dụng (SQL + memo; dự báo + dashboard; segment + slide), không
  ba notebook EDA giống nhau.
- **Kaggle có mục đích**: notebook công khai cho dự án, một competition Playground để học validation, không chạy theo thứ hạng.
- **Khoá học theo khoảng trống**, chứng chỉ chỉ khi công ty mục tiêu dùng công cụ đó.
- **Networking cụ thể**: tên cộng đồng, nhịp viết, câu hỏi cho mentor; không phải "mở rộng mạng lưới".
- **90 ngày theo sản phẩm**: tuần 1-4 dự án 1 công khai và CV mới; tuần 5-8 dự án 2 và dashboard; tuần 9-12 dự án 3, luyện
  SQL live và case, nộp đơn.

## Rubric (100 điểm)

| Hạng mục | Điểm | Đạt tối đa khi |
| --- | --- | --- |
| `audit_project` | 20 | Qua mọi test; code đọc được, hằng số tách riêng, không báo nhầm cách đọc key đúng |
| Vai trò mục tiêu | 10 | Có số đếm từ tin tuyển dụng thật, khoảng trống rõ |
| Ba dự án | 30 | Câu hỏi có quyết định; dữ liệu thật có link và giấy phép đúng; kỹ năng khác nhau khớp tin tuyển dụng; có hai dự án roadmap gợi ý |
| Kaggle, khoá học, chứng chỉ | 15 | Mục đích cụ thể, chọn theo khoảng trống, nói rõ điều không làm |
| Networking | 10 | Kênh cụ thể, nhịp cụ thể, hành động theo dõi sau sự kiện |
| Kế hoạch 90 ngày | 15 | Mỗi mốc một sản phẩm người khác kiểm được; khả thi với thời gian thật của người học |

Lỗi hay gặp: mười dự án dang dở thay vì ba dự án xong; dự án trên bộ dữ liệu không rõ nguồn hoặc synthetic (module 06); mốc
dạng "học xong X"; danh sách chứng chỉ không liên quan tới vai trò mục tiêu; quên chạy kiểm repo trước khi công khai.
