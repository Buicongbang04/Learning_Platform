# Hướng dẫn chấm: chọn công nghệ bằng ma trận quyết định

Bài advanced không có một đáp án duy nhất. Dưới đây là hướng làm tham khảo, các quyết định cần cân nhắc và rubric.

## Hướng làm phần code

```python
def validate(scores, weights):
    if any(w < 0 for w in weights.values()): raise ValueError("trọng số âm")
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-6): raise ValueError("tổng trọng số phải bằng 1")
    for option, row in scores.items():
        if set(row) != set(weights): raise ValueError(f"{option}: tiêu chí không khớp")
        if any(not 1 <= v <= 5 for v in row.values()): raise ValueError(f"{option}: điểm ngoài 1..5")

def rank(scores, weights):
    totals = weighted_scores(scores, weights)
    return sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))   # hoà điểm: theo tên, tất định

def reweight(weights, criterion, value):
    rest = 1 - weights[criterion]
    return {c: value if c == criterion else w * (1 - value) / rest for c, w in weights.items()}

def flip_point(scores, weights, criterion):
    # Mỗi hướng (w0 -> 1, w0 -> 0): tìm điểm đầu tiên phương án đứng đầu đổi (quét thô 1 000 bước),
    # rồi bisection giữa điểm cuối còn giữ ngôi và điểm đã đổi. Lấy kết quả gần w0 hơn.
```

Cách giải tích: với trọng số w, điểm phương án o là

$$S_o(w) = w\,s_{o,c} + \frac{1-w}{1-w_0}\left(S_o(w_0) - w_0\,s_{o,c}\right)$$

tuyến tính theo w, nên giao điểm giữa phương án đứng đầu và từng đối thủ giải được trực tiếp; chọn giao điểm trong
[0, 1] gần w0 nhất mà sau đó đối thủ thật sự vượt lên.

Lưu ý: ví dụ trong lý thuyết có A và B **bằng điểm** khi bỏ hẳn tiêu chí scalability, nên điểm đổi nằm đúng ở mép 0
và phụ thuộc sai số dấu phẩy động; test độ nhạy vì vậy dùng một biến thể không có hoà điểm chính xác.

## Lời giải tham khảo cho bài toán TP.HCM

**Khối lượng**: 300 trạm × 1 440 lần/ngày × 84 byte ≈ 36 MB/ngày, **13,2 GB/năm** thô (Parquet nhỏ hơn ~3 lần theo số đo
ở bài intermediate 02). 432 000 bản ghi/ngày = **5 bản ghi/giây**. Khối lượng không phải ràng buộc.

| Tiêu chí | Trọng số | A: MQTT + TimescaleDB một máy | B: Kafka + Flink + ClickHouse trên K8s | C: AWS IoT Core + Kinesis + S3 (Singapore) |
| --- | --- | --- | --- | --- |
| Latency cảnh báo 5 phút | 0,20 | 4 | 5 | 5 |
| Công sức vận hành (không SRE) | 0,25 | 4 | 1 | 5 |
| Năng lực đội 2 DE | 0,20 | 5 | 2 | 3 |
| Dữ liệu trong nước | 0,20 | 5 | 5 | 1 |
| Mở rộng 3 năm | 0,10 | 3 | 5 | 5 |
| Chi phí | 0,05 | 5 | 2 | 3 |
| **Điểm** | | **4,35** | **3,25** | **3,70** |

Độ nhạy (`flip_point`): A giữ ngôi trừ khi trọng số "dữ liệu trong nước" giảm xuống **≈ 0,045** (tức là luật cho phép
lưu ở nước ngoài thì C thắng), hoặc "latency" tăng lên ≈ 0,52, hoặc "công sức vận hành" tăng lên ≈ 0,55. "Năng lực đội"
và "chi phí" ở mức nào cũng không đổi kết quả. Kết luận: quyết định **phụ thuộc gần như hoàn toàn vào ràng buộc pháp lý**;
phải xác nhận ràng buộc đó bằng văn bản trước khi chốt.

**Quyết định**: A, kèm điều kiện xem lại: số trạm vượt ~5 000 (≈ 80 bản ghi/giây, bắt đầu cần phân vùng hoặc Kafka),
yêu cầu cảnh báo dưới 10 giây, hoặc có cloud trong nước cung cấp IoT managed. A là **two-way door**: dữ liệu thô vẫn
lưu Parquet, MQTT vẫn là chuẩn mở, chuyển sang B sau này không phải thu thập lại.

## Các quyết định cần cân nhắc

- **Trọng số đặt trước khi chấm điểm**, không chỉnh trọng số cho ra kết quả mong muốn. Người làm tốt ghi lại trọng số
  trước, rồi mới chấm.
- **Ràng buộc cứng hay tiêu chí mềm?** "Dữ liệu trong nước" có thể là ràng buộc loại trừ (C bị loại thẳng) chứ không
  phải một tiêu chí có trọng số. Nêu được điều này là dấu hiệu hiểu sâu.
- **Latency 5 phút không cần streaming engine**: một consumer MQTT ghi vào TimescaleDB và một job kiểm ngưỡng mỗi phút
  đủ đáp ứng; stream processing chỉ cần khi yêu cầu xuống mức giây.
- **Phát hiện trạm im lặng** cần trạng thái theo trạm (last seen): ở A là một truy vấn mỗi phút; ở B là windowing.

## Rubric

| Tiêu chí | Chưa đạt | Đạt | Tốt |
| --- | --- | --- | --- |
| Code ma trận | Test fail | Test pass | `flip_point` giải tích, giải thích được vì sao tuyến tính |
| Ước lượng khối lượng | Không có số | Phép nhân từ số đo UCI thật | Kèm bản ghi/giây và cỡ Parquet, rút ra "khối lượng không phải ràng buộc" |
| Tiêu chí và trọng số | Trọng số không giải thích | Mỗi trọng số có lý do gắn với bài toán | Phân biệt ràng buộc cứng và tiêu chí mềm |
| Phương án | < 3 hoặc mô tả mơ hồ | 3 phương án cụ thể, ai vận hành | Có phương án "nhàm chán" một máy và lý do nó cạnh tranh được |
| Độ nhạy | Không làm | `flip_point` mọi tiêu chí | Chỉ ra tiêu chí quyết định kết quả và hành động cần làm (xác nhận pháp lý) |
| Quyết định | Chỉ nêu tên | Có điều kiện xem lại | Bằng con số (số trạm, latency), nêu one-way/two-way door |
