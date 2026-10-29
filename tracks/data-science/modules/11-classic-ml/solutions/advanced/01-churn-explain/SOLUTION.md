# Hướng làm: giải thích model churn cho đội retention

Bài Advanced không có một đáp án duy nhất. Dưới đây là kết quả tham chiếu (random forest 300 cây,
`min_samples_leaf=10`, test 25% phân tầng, `random_state=42`), các quyết định cần cân nhắc, và rubric.

## Kết quả tham chiếu

ROC-AUC test 0.845.

| Hạng | Permutation (giảm ROC-AUC, 10 lần) | MDI (cột one-hot) | SHAP gộp (trung bình \|SHAP\|, cả tập test) |
| --- | --- | --- | --- |
| 1 | Contract 0.0487 | tenure 0.147 | Contract 0.0775 |
| 2 | tenure 0.0243 | Contract_Month-to-month 0.135 | InternetService 0.0526 |
| 3 | InternetService 0.0187 | TotalCharges 0.117 | tenure 0.0491 |
| 4 | TotalCharges 0.0139 | MonthlyCharges 0.076 | OnlineSecurity 0.0391 |
| 5 | PaymentMethod 0.0037 | OnlineSecurity_No 0.064 | TechSupport 0.0335 |

- **Feature tương quan.** Tương quan `tenure`–`TotalCharges` 0.83, `MonthlyCharges`–`TotalCharges` 0.65.
  `MonthlyCharges` không vào top 8 permutation nhưng thứ 4 theo MDI. Bỏ `TotalCharges` rồi train lại: ROC-AUC
  0.844 (gần như không đổi), và importance của `tenure` tăng từ 0.024 lên 0.048: thông tin chỉ chuyển chỗ.
- **Additivity**: giá trị nền 0.266 cộng tổng SHAP khớp xác suất dự đoán tới 3e-15.
- **Hai khách**: khách 1069-XAIEM (p = 0.912): hợp đồng tháng, `tenure` 1, internet cáp quang, trả bằng
  electronic check; SHAP lớn nhất ở tenure (+0.122), Contract (+0.099). Khách 3508-VLHCZ (p = 0.001): hợp đồng
  2 năm, `tenure` 71, DSL; Contract (−0.090), tenure (−0.043).

## Các quyết định cần cân nhắc

1. **Tính importance trên tập nào**: test (đo mức feature giúp dự đoán dữ liệu mới), không phải train.
2. **Hoán vị cột thô hay cột one-hot**: hoán vị cột one-hot riêng lẻ tạo ra khách có hai loại hợp đồng cùng lúc.
   Hoán vị cột thô qua pipeline tránh được.
3. **Metric cho permutation**: ROC-AUC (thứ hạng) hay log loss (xác suất); kết quả có thể khác. Chọn theo cách
   model được dùng.
4. **Background của SHAP**: `TreeExplainer` mặc định dùng phân phối train của cây (path-dependent). Đổi sang
   interventional với một tập background thì giá trị đổi; nêu rõ đã dùng gì.
5. **Câu hỏi nhân quả**: "chuyển sang hợp đồng 1 năm giảm churn bao nhiêu" không trả lời được bằng SHAP. Tỉ lệ
   churn 42.7% (tháng) so với 11.3% (1 năm) chứa selection: khách chọn hợp đồng dài vốn gắn bó hơn. Đề xuất thí
   nghiệm (module 03) hoặc ít nhất phân tích causal có kiểm soát confounder (module 06), và nhắm theo uplift.
6. **Fairness**: `gender`, `SeniorCitizen` có trong dữ liệu. Nói rõ có dùng không, và nếu dùng để quyết định ưu
   đãi thì kiểm tra metric theo nhóm.

## Khung REPORT.md mạnh

- Câu đầu: kết luận và khuyến nghị ("Ba yếu tố gắn với churn nhất là…; đề xuất thí nghiệm ưu đãi đổi hợp đồng
  cho nhóm X").
- Độ chính xác bằng ngôn ngữ thường: "trong 100 khách model xếp rủi ro cao nhất, khoảng N người thật sự rời đi".
- Bảng yếu tố với **chiều** tác động (hợp đồng tháng, tenure thấp, cáp quang, không có OnlineSecurity/TechSupport
  làm tăng rủi ro), nói rõ đây là quan hệ trong model.
- Một đoạn riêng "những gì giải thích này không nói".
- Bước tiếp: thí nghiệm, theo dõi model, dữ liệu cần thu thêm (lý do huỷ, khiếu nại, lịch sử giá).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Hàm chấm điểm | 15 | Test pass |
| Permutation so với MDI | 15 | Chỉ ra khác biệt và giải thích bằng cách tính (train vs held-out, thiên vị nhiều giá trị) |
| Feature tương quan | 15 | Thực nghiệm bỏ một feature hoặc gộp nhóm, kết luận đúng về chia importance |
| SHAP global và local | 15 | Gộp one-hot đúng, kiểm tra additivity, giải thích ít nhất 2 khách bằng ngôn ngữ thường |
| Nhân quả | 20 | Nói rõ SHAP không trả lời câu hỏi can thiệp; đề xuất thí nghiệm hoặc phương pháp causal, nhắc uplift |
| REPORT.md | 20 | Người không làm ML đọc hiểu; có khuyến nghị cụ thể; có giới hạn; không quá lời |

Từ 70 điểm: đủ để trình bày trước lãnh đạo. Dưới 50: thường do đọc importance như nhân quả.
