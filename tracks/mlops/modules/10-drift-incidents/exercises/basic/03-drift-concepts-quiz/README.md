---
title: Phân biệt các loại drift và quyết định theo bằng chứng
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Phân biệt data drift, prediction drift và concept drift, hiểu giới hạn của PSI/KS khi mẫu lớn và khi chỉ nhìn từng feature, biết dùng gì khi nhãn về muộn,
và nhớ thứ tự detect, verify, impact, decide thay vì phản xạ "thấy drift là train lại".

## Đề bài

Bài này không có code. Làm 7 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 6 câu chọn một đáp án, câu về nhãn về muộn chọn mọi đáp án đúng. Các câu đi qua: loại drift,
drift so với chất lượng, KS với mẫu lớn, drift đa biến, tín hiệu proxy khi chờ nhãn, baseline theo mùa vụ và bước đầu tiên khi dashboard đỏ.

Trước khi chọn, với mỗi tình huống tự hỏi: cái gì đã đổi (đầu vào, đầu ra hay quan hệ giữa chúng), ta đã biết điều đó từ đâu (thống kê hay nhãn), và hành động rẻ nhất, an toàn nhất là gì.

## Tiêu chí đạt

- Trả lời đúng ít nhất 6/7 câu.
- Với mỗi câu sai, nói lại được điều kiện làm cho đáp án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Một tên gọi cho một thứ đổi: $$P(X)$$ là data (covariate) drift, $$P(\hat{y})$$ là prediction drift, $$P(y \mid X)$$ là concept drift. Chỉ concept drift làm một model đã học đúng trở nên sai ngay cả khi đầu vào trông quen.

### Gợi ý 2

Tín hiệu nào mất thêm nhãn mới tính được thì không dùng được trong lúc chờ nhãn; tín hiệu nào chỉ cần đầu vào hoặc đầu ra của model thì dùng được. Thứ tự đúng của khung quyết định bắt đầu từ việc kiểm xem tín hiệu có thật không.
