# Lời giải: hiệu chỉnh multiple testing

## Ba phương pháp kiểm soát hai thứ khác nhau

- **FWER** (family-wise error rate): xác suất có **ít nhất một** false positive trong cả họ kiểm
  định. Bonferroni và Holm kiểm soát FWER ≤ α.
- **FDR** (false discovery rate): **tỉ lệ kỳ vọng** false positive trong số các phát hiện.
  Benjamini-Hochberg kiểm soát FDR ≤ α (khi các kiểm định độc lập hoặc tương quan dương).

Chọn theo hậu quả: quyết định ship dựa trên một họ metric → FWER (Holm). Sàng lọc 200 segment để
tìm hướng điều tra, chấp nhận vài phát hiện sai → FDR (BH).

## Vì sao Holm luôn tốt hơn Bonferroni

p-value nhỏ nhất so với α/m (giống Bonferroni), nhưng p-value thứ hai chỉ cần vượt α/(m − 1), thứ
ba α/(m − 2)… Ngưỡng nới dần nên Holm bác bỏ ít nhất bằng Bonferroni, không đòi giả định gì thêm,
và vẫn kiểm soát FWER. Không có lý do dùng Bonferroni thay Holm, trừ khi cần tính nhẩm.

## Chi tiết cài đặt

- Dùng `<=` để khớp statsmodels.
- `argsort(kind="stable")` để p-value trùng nhau có thứ tự xác định.
- BH step-up: tìm vị trí cuối cùng thoả điều kiện; mọi p-value nhỏ hơn đều bị bác bỏ, kể cả khi
  bản thân chúng không thoả (vector thứ hai trong test có trường hợp này).

## Mô phỏng

10 metric độc lập, không metric nào có tác động: xác suất có ít nhất một p < 0.05 là
1 − 0.95¹⁰ ≈ 40%. Trong thực tế các metric thường tương quan (visit và conversion), nên con số thấp
hơn, nhưng vẫn cao hơn nhiều so với 5% mà người đọc báo cáo ngầm giả định.

## Hillstrom (mở rộng)

Cả 6 kiểm định (2 email × visit, conversion, spend) có p-value rất nhỏ, nên kết luận không đổi sau
hiệu chỉnh. Multiple testing quan trọng nhất ở vùng p ≈ 0.01–0.05, và khi chia nhỏ theo segment.

## Cách giảm vấn đề từ gốc

Một OEC định trước, vài guardrail, metric chẩn đoán chỉ để hiểu cơ chế. Phân tích segment để sinh
giả thuyết cho thí nghiệm sau.
