# Lời giải: Bản đồ khoảng cách FDE

Bài phụ thuộc vào chính bạn nên không có bản đúng duy nhất. Dưới đây là cách gộp yêu cầu, một bản mẫu cho người học
đã qua các track DE/DS/AE/MLOps/DevOps của repo nhưng chưa làm FDE, và rubric.

## Gộp yêu cầu (một cách hợp lý)

| # | Yêu cầu | Tin | Track dạy ở đâu |
| --- | --- | --- | --- |
| 1 | Code Python production (test, packaging, log) | A, B, C | MLOps 01; mọi bài có test của repo |
| 2 | LLM/RAG và đánh giá chất lượng trên dữ liệu khách | A | AE 13, AE 20; FDE 09 |
| 3 | Triển khai on-prem/air-gapped, Linux, mạng, container | B, A (hạ tầng của khách) | FDE 01–04; DevOps 01, 04, 06 |
| 4 | Kubernetes do khách quản lý (không cluster-admin) | B | FDE 06; DevOps 10–12 |
| 5 | SSO doanh nghiệp, tích hợp hệ thống/dữ liệu cũ | B | FDE 07; DE (SQL, Kafka) |
| 6 | Chẩn đoán sự cố với quyền hạn chế | B | FDE 08 |
| 7 | Bảo mật, tuân thủ, yêu cầu của khách | A, B | FDE 07 (questionnaire, data residency) |
| 8 | Discovery, scoping từ yêu cầu mơ hồ | A, C | FDE 11–12 |
| 9 | Prototype full-stack nhanh | C | FDE 10 |
| 10 | Đo ROI cùng khách | C | FDE 13 |
| 11 | Giao tiếp với kỹ sư và lãnh đạo; phản hồi cho product | A, C | FDE 14 |
| 12 | DSA (vòng coding) | C | FDE 15–16 |
| 13 | System design, decomposition, nhập vai | C | FDE 17–18, 20 |
| 14 | Kinh nghiệm làm việc trực tiếp với khách, đi công tác, số năm | A | Không học được trong repo |

## Mẫu vài dòng của bảng

| # | Yêu cầu | Bằng chứng | Mức | Kế hoạch | Sản phẩm | Hạn |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | LLM/RAG + eval | Capstone AE đã pass, repo public có README kết quả eval | một phần | FDE 09 + milestone m09 | Eval suite trên CUAD, báo cáo groundedness/citation | tuần 6 |
| 3 | On-prem/air-gapped | Chưa cài gì ngoài máy mình; bài DevOps 06 đã pass | chưa | FDE 01–03 + m01–m03 | Bundle offline + installer cài được trên VM air-gapped, repo capstone | tuần 3 |
| 12 | DSA | Không có bài nào đã nộp | chưa | FDE 15 song song từ tuần 1, 4 bài/tuần | Lịch sử bài đã pass, ghi chú pattern | tuần 8 |
| 14 | Kinh nghiệm với khách | Từng trình bày dashboard cho trưởng phòng kinh doanh, có thay đổi quyết định nhập hàng | một phần | Kể như câu chuyện discovery; FDE 11 luyện có cấu trúc | Câu chuyện STAR 2 phút | tuần 4 |

**Ba ưu tiên mẫu:** (1) trụ 1 module 01–03 cùng m01–m03, vì cả A và B đều đòi triển khai trên hạ tầng của khách và đây là
khoảng cách lớn nhất của người đến từ DA/DS; (2) DSA song song mỗi tuần, vì đó là cửa đầu tiên của vòng phỏng vấn và cần
thời gian tích luỹ; (3) FDE 09 trên dữ liệu CUAD, vì biến kiến thức RAG đã có thành bằng chứng mà người phỏng vấn tin.

## Rubric (20 điểm)

| Tiêu chí | 0 | 2 | 4 |
| --- | --- | --- | --- |
| Gộp yêu cầu | Chép nguyên văn ba tin | Có gộp nhưng trùng hoặc trộn nhiều năng lực trong một dòng | 10–15 yêu cầu theo năng lực, ghi nguồn, không trùng |
| Bằng chứng | "Đã học", "biết" | Có link nhưng không chỉ ra kết quả | Mỗi `có` mở ra được và thấy kết quả trong 2 phút |
| Trung thực về mức | Gần như toàn `có` | Có `chưa` nhưng né các yêu cầu khó (on-prem, DSA, khách hàng) | Mức khớp bằng chứng, nói thẳng thứ không học được trong repo |
| Kế hoạch | Không có hoặc "sẽ học thêm" | Trỏ module nhưng thiếu sản phẩm hoặc hạn | Module/bài/milestone cụ thể, sản phẩm kiểm được, hạn; ưu tiên có lý do |
| Câu chuyện | Tính từ ("đam mê", "chăm chỉ") | Kể việc nhưng không có kết quả | 5–8 câu, nối bằng chứng thật thành lý do hợp vai FDE |

## Sai lầm hay gặp

- Viết bản đồ cho "người học chung chung" thay vì cho chính mình.
- Coi chứng chỉ khoá học là bằng chứng ngang với một hệ thống cài được trên máy lạ.
- Bỏ qua DSA vì "FDE là vai làm việc với khách": nhiều quy trình phỏng vấn FDE vẫn có vòng coding.
