---
title: Cổng promotion - hàm decide_promotion với các ca biên
level: basic
services: []
files:
  - path: starter/promotion.py
    note: 1 hàm TODO
  - path: tests/test_promotion.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/04-tracking-registry/exercises/basic/02-promotion-decision -q
---

## Mục tiêu

Biến câu "model mới tốt hơn" thành một hàm thuần túy, có test, trả về quyết định kèm lý do mà người khác đọc được. Phần khó
không phải so hai con số MAE mà là các ca biên: tổng tốt hơn nhưng một slice quan trọng xấu đi, slice quá nhỏ, thiếu số đo.

## Đề bài

Model dự đoán thời gian chuyến taxi (MAE tính bằng giây). Trong `starter/promotion.py` cài
`decide_promotion(challenger, champion, policy) -> Decision`. Mỗi model mô tả bằng
`{"mae", "latency_p95_ms", "slices": {tên: {"mae", "n"}}}`; `policy` ghi đè các khoá của `DEFAULT_POLICY` (đã có trong starter: `min_improvement` 0.01, `slice_tolerance` 0.05,
`min_slice_n` 200, `max_latency_ratio` 1.2, `max_latency_ms` None, `max_mae` None).

Ba cổng, đều phải qua:

1. **overall_mae**: MAE tổng của challenger cải thiện ít nhất `min_improvement` (tỉ lệ tương đối so với champion).
   Đúng bằng ngưỡng thì qua.
2. **slices**: mọi slice của champion có cỡ mẫu (cả hai bên) tối thiểu `min_slice_n` không được xấu đi quá
   `slice_tolerance` (tương đối). Slice champion có mà challenger thiếu thì không kiểm được, coi là trượt. Slice nhỏ hơn
   `min_slice_n` bị bỏ qua vì quá nhiễu.
3. **latency**: p95 của challenger không quá `max_latency_ratio` lần champion, và không quá `max_latency_ms` nếu policy đặt.

Thêm: giá trị không hữu hạn (NaN, thiếu) không bao giờ được promote. Không có champion (`None`) thì chỉ áp ngưỡng tuyệt đối
`max_mae` và `max_latency_ms` của policy. `Decision.checks` có đúng ba khoá trên; `reasons` có một dòng cho mỗi cổng trượt
(nêu tên slice), hoặc một dòng tóm tắt khi promote. Không sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Ca "tổng tốt hơn 10%, slice `airport` xấu đi 20%" bị từ chối và lý do nhắc `airport`.
- Các ca biên đúng: cải thiện đúng bằng ngưỡng, slice xấu đi đúng bằng dung sai, latency đúng 1.2 lần.
- Nhiều cổng trượt cùng lúc thì báo đủ mọi lý do, không dừng ở lý do đầu tiên.
- Hàm không đổi `challenger`, `champion`, `policy`.

## Gợi ý

### Gợi ý 1

Viết ba hàm kiểm nhỏ, mỗi hàm nhận `reasons` và trả `bool`, rồi gộp trong `decide_promotion`. Nhờ đó cổng nào trượt cũng
ghi được lý do mà không phải `return` sớm.

### Gợi ý 2

So sánh số thực có sai số làm tròn: `(315 / 300) - 1` ra `0.05000000000000004`, lớn hơn `0.05`. Cộng/trừ một epsilon nhỏ
(`1e-12`) ở các phép so sánh biên. Kiểm NaN bằng `math.isfinite`, vì mọi phép so sánh với NaN đều `False` và dễ để lọt.
