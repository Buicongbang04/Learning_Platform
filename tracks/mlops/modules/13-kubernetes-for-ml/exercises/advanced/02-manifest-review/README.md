---
title: Review manifest K8s của một service model
level: advanced
services: []
files:
  - path: starter/manifest.yaml
    note: Manifest cần review (không apply lên cluster dùng chung)
  - path: starter/REVIEW.md
    note: Bản review của bạn
run: []
---

## Mục tiêu

Review một manifest K8s cho service model như reviewer của PR: tìm lỗi chặn release, lỗi bảo mật, lỗi vận hành, xếp mức độ và đề xuất sửa cụ thể.

## Đề bài

Một đồng nghiệp mở PR đưa service ETA (CPU, sklearn, nghe cổng 8080, model nạp từ đường dẫn `MODEL_PATH`) lên cluster production bằng `starter/manifest.yaml`. Viết `starter/REVIEW.md`:

1. Bảng các vấn đề: trường nào, vấn đề, hậu quả khi chạy thật, cách sửa. Xếp mức **chặn** (không merge), **nên sửa**, **gợi ý**.
2. Bản sửa đề xuất của manifest (YAML đầy đủ, có thể dán vào PR).
3. Những câu bạn cần hỏi tác giả trước khi duyệt (thông tin manifest không cho biết).

Có thể kiểm phần cú pháp bằng `kubectl --context kind-mlops apply --dry-run=server -f ... -n <namespace của bạn>`, nhưng đừng apply manifest gốc lên namespace `default` của cluster dùng chung.

## Tiêu chí đạt

- Tìm được ít nhất 8 vấn đề, xếp mức hợp lý, mỗi vấn đề có hậu quả cụ thể.
- Bản sửa apply được (dry-run server không lỗi) và không đưa vào lỗi mới.
- Tự chấm theo rubric trong `SOLUTION.md`, đạt từ 14/20.

## Gợi ý

### Gợi ý 1

Đi theo đường một request: Service tìm pod thế nào, tới cổng nào; rồi theo vòng đời pod: image kéo từ đâu, model ở đâu, probe nào quyết định sống chết.

### Gợi ý 2

Với mỗi trường `resources`, hỏi: scheduler dùng nó để làm gì, và ở lúc chạy nó giới hạn điều gì?
