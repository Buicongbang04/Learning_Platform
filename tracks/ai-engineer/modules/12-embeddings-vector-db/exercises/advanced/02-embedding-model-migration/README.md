---
title: Chọn embedding model, nén vector, migrate index không downtime
level: advanced
services: []
files:
  - path: starter/models.ipynb
    note: quantize_int8, dequantize_int8, binarize, hamming_topk, rescore TODO; phần đo tự viết
  - path: starter/REPORT.md
    note: Bảng so sánh, lựa chọn, kế hoạch migrate
  - path: tests/test_models.py
    note: Không sửa
run:
  - ollama pull bge-m3
  - ollama pull nomic-embed-text
  - uv run jupyter lab tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/advanced/02-embedding-model-migration/starter/models.ipynb
  - uv run pytest tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/advanced/02-embedding-model-migration -q
---

## Mục tiêu

Ra quyết định embedding như ở production: model nào cho tiếng Việt pháp lý, lưu vector ở độ chính xác nào, và khi đổi
model thì chuyển index đang phục vụ sang không gian vector mới thế nào mà người dùng không thấy gián đoạn hay tụt chất
lượng. Mọi lựa chọn dựa trên số đo của chính bạn.

## Đề bài

**Phần cứng:** CPU · ~4 giờ

Ngoài thời gian làm bài: embed pool bằng hai model qua Ollama mất từ vài phút tới vài chục phút tuỳ cỡ pool và máy.

1. **Hàm** (notebook mô tả chính xác, có test): `quantize_int8`, `dequantize_int8`, `binarize`, `hamming_topk`, `rescore`.
2. **Bảng chất lượng**: trên 300 câu hỏi ghim, Recall@10 và MRR@10 theo nhãn (định nghĩa của module 13) cho ít nhất:
   - `bge-m3` float32 trên cả corpus (cache), cắt còn 512 và 256 chiều, int8, nhị phân không rescoring, nhị phân +
     rescoring top-100;
   - `nomic-embed-text` có và không có tiền tố, và `bge-m3`, trên **cùng một pool** (mọi điều của các văn bản chứa đáp án
     cộng ít nhất 5 000 điều ngẫu nhiên, seed ghim). Ghi rõ cỡ pool và cách xử lý văn bản quá dài.
3. **Chi phí**: byte/vector của từng cách lưu và dung lượng cho cả corpus; throughput embed của mỗi model (văn bản/giây,
   cùng máy, cùng cỡ lô); số chiều.
4. **Chẩn đoán**: tìm một nguyên nhân cụ thể (có số hoặc ví dụ) cho model kém nhất trên tiếng Việt.
5. **Kế hoạch migrate** từ index A (model cũ) sang index B (model mới) cho một dịch vụ search đang chạy: các bước, tiêu
   chí chuyển (dựa trên bảng ở bước 2), cách rollback, ước lượng thời gian backfill cho 61 425 điều và cho 10 triệu
   chunk bằng throughput đã đo.

## Tiêu chí đạt

- Test hàm pass; nhị phân + rescoring tốt hơn hẳn nhị phân thuần trên dữ liệu test.
- Bảng chất lượng đủ các dòng ở bước 2, cùng tập câu hỏi, pool ghi rõ.
- Lựa chọn cuối có lý do bằng số (chất lượng, bộ nhớ, tốc độ) và nói rõ đánh đổi.
- Chẩn đoán có bằng chứng, không chỉ "model này không hợp tiếng Việt".
- Kế hoạch migrate xử lý được: vector hai model không trộn được với nhau, ghi trong lúc backfill, tiêu chí chuyển,
  rollback.
- Rubric chi tiết trong `SOLUTION.md` của bài (xem sau khi nộp).

## Gợi ý

### Gợi ý 1

Cắt chiều và nén đều làm được từ cache `bge-m3` có sẵn, không cần embed lại: cắt chiều xong phải chuẩn hoá lại. Với
nhị phân, lấy top-R theo Hamming rồi `rescore` bằng vector float32 gốc.

### Gợi ý 2

Để chẩn đoán một model kém trên tiếng Việt, so cosine của các cặp câu chỉ khác nhau một từ mang nghĩa ("rất" và "không"),
và thử cùng câu đó khi bỏ dấu. Với migrate, tìm hiểu mô hình "dual write + backfill + shadow read + chuyển alias".
