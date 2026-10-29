# Lời giải: LaLonde, propensity score so với thí nghiệm

Notebook lời giải: `lalonde.ipynb` (chạy được toàn bộ khi đã tải `lalonde`).

## Con số chính

| Ước lượng | Giá trị (USD, thu nhập 1978) |
| --- | --- |
| Thí nghiệm NSW (chuẩn) | **1 794** (CI 95% khoảng [479, 3 109]) |
| Ngây thơ: NSW treated vs PSID | −15 205 |
| IPW, 8 covariate | 1 759 |
| 1-NN matching, 8 covariate | 2 126 |
| IPW, đặc tả Dehejia–Wahba (+ age², education², u74, u75) | 2 768 |
| 1-NN matching, đặc tả Dehejia–Wahba | 1 593 |
| IPW 8 covariate, trim propensity ngoài [0.05, 0.95] | 1 754 |
| IPW Dehejia–Wahba, trim [0.05, 0.95] | 582 |

## Vì sao ngây thơ sai tới mức đổi dấu

Người tham gia NSW là người thất nghiệp lâu, phần lớn không có bằng cấp; người PSID là hộ gia đình
nói chung. SMD trước khi cân: `married` −1.84, `re75` −1.77, `re74` −1.72, `black` +1.48 (ngưỡng
"cân bằng" là 0.1). Thu nhập 1978 trung bình của PSID là $21 554, của người được đào tạo là $6 349.
Không phải đào tạo làm mất tiền: hai nhóm vốn không so sánh được.

## IPW làm gì và cái giá

Sau khi cân, mọi |SMD| ≤ 0.08. Nhưng 1 952 trên 2 490 người PSID có propensity dưới 0.01; họ gần như
không đóng góp gì. ESS của nhóm control là 42.6: toàn bộ ước lượng dựa trên khoảng 43 "người hiệu
dụng", một người PSID chiếm 5.8% tổng trọng số. Matching cho kết luận tương tự: 185 người treated
được ghép với chỉ 69 người PSID khác nhau.

Đó là **vấn đề overlap**. Propensity score không tạo ra người so sánh được; nó chỉ tìm và nhân trọng
số những người đã có. Khi overlap kém, ước lượng có variance lớn và cực nhạy với đặc tả mô hình,
đúng như bảng trên: cùng dữ liệu, các lựa chọn hợp lý cho từ $582 tới $2 768.

## Thực hành tốt

- **Luôn** in balance (SMD) trước và sau, histogram propensity hai nhóm, ESS. Đó là phần "chẩn
  đoán" bắt buộc như kiểm SRM trong A/B test.
- Đặc tả propensity được chọn để **cân bằng covariate**, không phải để tối đa AUC. AUC rất cao
  (ở đây gần như tách hoàn toàn hai nhóm) là tin xấu, không phải tin tốt.
- Báo cáo một bảng độ nhạy thay vì một con số. Cân nhắc doubly robust (AIPW): kết hợp mô hình
  outcome và propensity, đúng nếu một trong hai đúng.
- Trimming đổi **câu hỏi**: kết quả là tác động trên tổng thể có overlap, không còn là ATT trên mọi
  người tham gia. Phải nói rõ điều đó.

## Bài học lớn của LaLonde

Phương pháp quan sát chỉ tốt bằng giả định "không còn confounder chưa đo". Ở đây ta may mắn có
thu nhập hai năm trước (re74, re75), biến quan trọng nhất; Dehejia & Wahba (1999) cho thấy thiếu
re74 thì kết quả tệ hẳn. Smith & Todd (2005) chỉ ra kết quả "propensity score tìm lại được con số
thí nghiệm" phụ thuộc mạnh vào mẫu và đặc tả. Câu trả lời trung thực trong thực tế là một khoảng
kèm danh sách giả định, không phải một con số.

## Rubric cho phần kết luận

| Tiêu chí | Đạt khi |
| --- | --- |
| So với chuẩn | Nêu IPW / matching gần $1 794 và mức chênh |
| Giải thích ngây thơ | Chỉ ra confounding qua SMD, không chỉ nói "bias" |
| Overlap | Nhắc ESS hoặc số người PSID thực sự được dùng |
| Độ nhạy | Thấy kết quả đổi theo đặc tả / trimming và rút ra hệ quả |
| Không quá lời | Không nói "đã chứng minh"; nêu giả định unconfoundedness |
