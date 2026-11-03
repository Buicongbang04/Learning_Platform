# Hướng làm và rubric: bộ đề system design mức senior

Mỗi đề chấm trên 100 điểm theo cùng tám mục của khung trả lời (README module mục 6), cộng các câu "đào sâu" mà người phỏng vấn
senior thường hỏi. Các con số dưới đây là ước tính hợp lý, không phải đáp án duy nhất; điều được chấm là lập luận ra con số.

## Rubric chung (áp cho cả ba đề)

| Mục | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Làm rõ yêu cầu | 10 | Hỏi ít nhất 3 câu thay đổi thiết kế (quy mô, độ trễ, ràng buộc pháp lý hay ngân sách); chốt giả định bằng lời |
| Chỉ số | 15 | Có chỉ số nghiệp vụ online, chỉ số offline tương quan với nó, và guardrail metric; nói chỉ số offline sai ở đâu |
| Dữ liệu và nhãn | 10 | Nguồn nhãn, độ trễ nhãn, thiên lệch trong nhãn và cách giảm |
| Baseline | 10 | Một baseline không cần ML hoặc đơn giản, và lý do mỗi bước phức tạp hơn phải thắng nó |
| Kiến trúc | 20 | Đường online và offline tách bạch; tầng sinh ứng viên và xếp hạng (A, B) hoặc cổng nền tảng (C); feature store, log để huấn luyện lại |
| Ước tính và đánh đổi | 15 | Ít nhất 2 phép tính dung lượng hay chi phí; ba đánh đổi lớn có số |
| Vận hành | 15 | SLO gồm chất lượng và freshness; chế độ hỏng có fallback; rollout có A/B hoặc canary; ai trực |
| Giao tiếp | 5 | Nói thứ tự trước khi đi; quản lý thời gian; thừa nhận giả định và giới hạn |

Mức đạt 70. Trừ điểm: vẽ model trước khi có chỉ số (-10), không nhắc baseline (-5), không có fallback trên đường nóng (-10).

## Đề A: gợi ý trang chủ

**Hướng làm.** Chỉ số online: GMV từ gợi ý mỗi phiên, CTR, tỉ lệ thêm giỏ; guardrail: đa dạng, độ phủ người bán mới, độ trễ trang.
Offline: recall@K của tầng sinh ứng viên, NDCG của tầng xếp hạng trên log đã khử thiên lệch. Kiến trúc hai tầng: sinh vài trăm ứng viên
từ nhiều nguồn (two-tower ANN, co-occurrence, phổ biến theo vùng, nguồn "người bán mới") rồi model xếp hạng (GBM hay DNN nhỏ) trên vài trăm
ứng viên, cuối cùng tầng luật (lọc mặt hàng nhạy cảm, đa dạng hoá, tần suất). Tính trước embedding sản phẩm theo lô; embedding người dùng
và feature phiên tính gần realtime. Ngân sách độ trễ: khoảng 30 ms ANN, 50 ms xếp hạng, phần còn lại cho trang.

**Ước tính mẫu.** 20 triệu sản phẩm x embedding 128 chiều float16 = khoảng 5 GB, vừa một index ANN có replica. Xếp hạng 300 ứng viên x
5 000 RPS = 1.5 triệu lượt chấm mỗi giây: cần batching trong yêu cầu và model nhỏ, hoặc cắt còn 100 ứng viên.

**Câu đào sâu.** Người bán mới không có tương tác (cold start: nguồn ứng viên riêng, khám phá có ngân sách, feature nội dung). Feedback loop
làm gợi ý hẹp dần (khám phá, đo độ phủ danh mục). Cache trang chủ theo người dùng giúp gì cho p99 (bài Basic 02). Mặt hàng nhạy cảm: lọc
cứng sau model, không trông vào model tự học.

**Điều kiện cho từng mục (đề A).** Kiến trúc chỉ được đủ 20 điểm khi có hai tầng và một nguồn ứng viên cho người bán mới; Dữ liệu và nhãn
cần nói thiên lệch phơi bày (chỉ có nhãn cho thứ đã được gợi ý); Vận hành cần guardrail đa dạng hay độ phủ, không chỉ CTR.

## Đề B: xếp hạng tìm kiếm

**Hướng làm.** Chỉ số online: tỉ lệ truy vấn có click hay mua, thời gian tới mua, tỉ lệ truy vấn không kết quả; offline: NDCG trên nhãn
mức liên quan do người chấm (một tập nhỏ có chất lượng) cộng nhãn click đã hiệu chỉnh thiên lệch vị trí (interleaving, propensity). Kiến
trúc: hiểu truy vấn (chuẩn hoá, sửa lỗi chính tả, phân loại danh mục), truy xuất lai (BM25 cộng dense retrieval cho đuôi dài), xếp hạng
learning-to-rank, rồi trộn quảng cáo ở tầng riêng với ràng buộc mức liên quan tối thiểu.

**Ước tính mẫu.** 1 500 QPS x 1 000 ứng viên chấm bằng GBM khoảng 1.5 triệu lượt mỗi giây, cùng bậc với đề A; cache truy vấn đầu phân
phối (40% lưu lượng) cắt phần lớn tải nhưng không giúp đuôi dài (60% truy vấn).

**Câu đào sâu.** Thiên lệch vị trí trong log click và vì sao huấn luyện thẳng trên click khuếch đại thứ hạng cũ. Đuôi dài: dense retrieval
và mở rộng truy vấn; đánh giá riêng slice đuôi dài. Quảng cáo: hai mục tiêu xung đột, cần guardrail mức liên quan đo bằng người chấm. Đổi model
xếp hạng: interleaving nhạy hơn A/B và tốn ít traffic hơn.

**Điều kiện cho từng mục (đề B).** Dữ liệu và nhãn chỉ đủ điểm khi xử lý thiên lệch vị trí; Kiến trúc cần đường riêng cho đuôi dài; Chỉ
số cần tập nhãn mức liên quan do người chấm làm thước đo độc lập với click; Vận hành cần guardrail mức liên quan khi trộn quảng cáo.

## Đề C: nền tảng LLM nội bộ

**Hướng làm.** Đây là bài nền tảng: một cổng LLM chung (xác thực, hạn mức theo đội, định tuyến model, log và đo chi phí theo đội), model
tự host trên 16 GPU cho dữ liệu nhạy cảm (model mở cỡ vừa, lượng tử hoá, continuous batching qua vLLM hay TGI) và API bên ngoài cho tác vụ
không nhạy cảm cần chất lượng cao; định tuyến theo nhãn độ nhạy của dữ liệu. RAG dùng chỉ mục **riêng từng đội** có kiểm quyền theo tài
liệu tại lúc truy xuất. Guardrail: lọc PII đầu vào và đầu ra, chống prompt injection (tách chỉ dẫn hệ thống khỏi nội dung truy xuất, không
cho công cụ có quyền ghi chạy theo nội dung truy xuất). Đánh giá: bộ đánh giá theo từng use case, LLM-as-judge có hiệu chỉnh với người chấm,
chạy như cổng promotion khi đổi model hay prompt (ôn AE 20).

**Ước tính mẫu.** Một GPU 24 GB chạy model 8B lượng tử hoá 4 bit, continuous batching, cho cỡ vài nghìn token mỗi giây tổng; 16 GPU ở
mức sử dụng 50% cho cỡ chục nghìn token mỗi giây. Chi phí theo đội = GPU-giờ chia theo token đã dùng cộng hoá đơn API theo khoá của đội.

**Câu đào sâu.** Rò rỉ giữa các đội qua cache ngữ nghĩa dùng chung (cache theo đội, khoá gồm quyền). Một đội đốt hết hạn mức GPU (hạn mức
và hàng đợi ưu tiên, giống Kueue ở module 14). Prompt injection từ tài liệu nội bộ. SLO cho LLM: thời gian ra token đầu, token mỗi giây,
tỉ lệ trả lời qua guardrail, chất lượng theo bộ đánh giá. Khi nào fine-tune, khi nào chỉ RAG.

**Điều kiện cho từng mục (đề C).** Kiến trúc chỉ đủ điểm khi có cổng chung, định tuyến theo độ nhạy dữ liệu và chỉ mục RAG cô lập theo đội;
Ước tính cần quy GPU-giờ ra chi phí theo đội; Vận hành cần hạn mức, guardrail PII và prompt injection, và bộ đánh giá làm cổng khi đổi
model hay prompt. Trả lời chỉ xoay quanh chọn model nào thì tối đa 50 điểm.

## Giới hạn

Rubric chấm cách lập luận trong 45 phút. Người phỏng vấn senior thật còn hỏi về những lần bạn đã vận hành hệ thống như vậy: sự cố, đánh
đổi đã sai, con số thật. Phần đó chỉ có từ kinh nghiệm production; bộ đề này giúp bạn có khung để kể và để học nhanh hơn khi có cơ hội.
