# Lời giải: rerank top-50 hybrid bằng cross-encoder

## Cách làm

**`rerank`** gọi `score_fn` một lần cho cả danh sách: cross-encoder chạy theo batch, nên gom mọi cặp của một câu hỏi
vào một lời gọi nhanh hơn nhiều so với chấm từng cặp. Văn bản là `"<title>\n<text>"` vì tiêu đề điều ("Điều 7. Nhiệm
vụ của Công an xã") thường là phần mang nghĩa nhất, và cross-encoder chỉ đọc 512 token đầu. Điểm đổi sang `float` rồi
`sorted(range(n), key=lambda i: -scores[i])`: `sorted` của Python ổn định, nên hai ứng viên bằng điểm giữ thứ tự của
retrieval, thứ tự đó vẫn là thông tin có ích. Danh sách rỗng trả `[]` sớm, không gọi model.

**`cross_encoder_score_fn`** là một closure nạp lười:

```python
model = None
def score(query, texts):
    nonlocal model
    if model is None:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder(model_name, device=device, max_length=max_length)
    ...
```

Ba lợi ích: import notebook (và chạy test) không kéo `sentence_transformers`, `torch` và 2.3 GB trọng số; test thay
được module bằng bản giả qua `sys.modules`; và model chỉ nạp một lần cho mọi câu hỏi. Đặt `import` ở đầu notebook hay
tạo `CrossEncoder` ngay trong hàm ngoài đều làm mất cả ba.

## Kết quả thật

Laptop của track, môi trường gốc (`torch 2.14.1+cpu`, `transformers 5.22.0`, `sentence-transformers 6.2.0`), CPU 8
luồng PyTorch, `max_length=512`, `batch_size=16`. 100 câu đầu tập ghim, ứng viên là top-50 hybrid của bài 01 (cả điều):

| Cấu hình | MRR@10 | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- |
| Hybrid (bài 01), 100 câu đầu | 0.680 | 0.56 | **0.83** | **0.89** |
| Hybrid + rerank top-50 | 0.697 | 0.60 | 0.81 | 0.87 |
| Hybrid + rerank top-20 (dùng lại điểm) | **0.706** | **0.61** | | |
| Hybrid + rerank top-10 (dùng lại điểm) | 0.701 | **0.61** | | |

| Độ trễ rerank top-50 | Giá trị |
| --- | --- |
| Trung vị / p95 mỗi câu | 35.0 s / 47.3 s (khoảng 0.7 s một cặp) |
| Cả 100 câu | khoảng 60 phút (lần sau đọc cache, notebook chạy dưới 30 s) |
| Nạp model lần đầu (đã có trong cache Hugging Face) | vài giây; lần đầu tải 2.3 GB |

R@50 của hybrid trên 100 câu là 0.960: 4 câu có điều đúng ngoài top-50, không reranker nào cứu được. Điều đúng đầu tiên
lên hạng ở 23 câu, tụt hạng ở 19 câu, giữ nguyên ở 58 câu. Câu đầu tiên của tập ("Mức phạt khi quay đầu xe ô tô trên
đường cao tốc") là ví dụ tụt: hybrid đặt Điều 5 Nghị định 100/2019 ở hạng 1, cross-encoder đẩy Điều 7 (cũng là mức phạt
xe ô tô, nhưng hành vi trên đường cao tốc nằm ở Điều 5) lên trước.

## Đọc kết quả

- **Cùng kết luận với mục 4 lý thuyết, ở quy mô lớn hơn**: cross-encoder đẩy thêm câu lên hạng 1 (R@1 0.56 lên 0.60)
  nhưng kéo câu khác xuống, nên MRR@10 chỉ tăng 0.017 và R@5, R@10 còn **giảm** 0.02. Trên 100 câu, mỗi câu là 0.01 của
  R@1: mức tăng ròng 4 câu nằm sát biên nhiễu. Phần lý thuyết (top-20, lát cắt) đo +0.009 MRR, +0.05 R@1.
- **Nhiều ứng viên hơn không tốt hơn**: rerank top-20 cho MRR@10 0.706, cao hơn top-50 (0.697), với 40% chi phí. Ứng viên
  từ hạng 21 tới 50 của hybrid hiếm khi đúng nhưng đôi khi được cross-encoder chấm cao (điều cùng chủ đề, đoạn đầu giống
  câu hỏi), và chen vào top-10. $$K$$ là siêu tham số phải đo, không phải "càng nhiều càng chắc".
- **Vì sao tụt hạng**: cross-encoder chỉ đọc 512 token đầu của mỗi điều (khoảng 2 000 ký tự). Nghị định xử phạt có các
  điều dài, liệt kê hàng chục hành vi theo mức phạt; hành vi mà câu hỏi nhắc tới có thể nằm sau chỗ cắt, trong khi một
  điều lân cận nói đúng chủ đề ở ngay đầu. Đây cùng loại lỗi "cả điều bị cắt" của bài 02: rerank trên **khoản** (chunk
  theo bài Basic 01) thay vì cả điều là thí nghiệm đáng làm tiếp.
- **Độ trễ là cái giá thật**: 35 s một câu trên CPU, gấp khoảng 1 700 lần dense search (20 ms) và 6 000 lần BM25 (6 ms) ở
  bài 01. Trên CPU, rerank chỉ dùng được cho xử lý offline hoặc $$K$$ rất nhỏ; phục vụ người dùng thì cần GPU (phần lý
  thuyết đo 0.59 s cho 20 cặp trên GPU 4GB), hoặc model rerank nhỏ hơn, hoặc cắt ngắn ứng viên.
- **Nạp lười trả công ngay**: 8 test của bài chạy trong khoảng 2 giây không tải model nào, vì `sentence_transformers` chỉ
  được import trong hàm chấm và test thay nó bằng module giả.
