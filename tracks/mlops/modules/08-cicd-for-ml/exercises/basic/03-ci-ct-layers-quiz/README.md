---
title: CI cho code và CT cho model - phân lớp, trigger, secrets, act
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Phân biệt hai lớp pipeline của một repo ML và những quyết định quanh nó: lớp nào chạy khi nào, chỗ hai lớp gặp nhau, secrets và
OIDC, giới hạn của `act`, chọn công cụ CI khi bối cảnh đã có sẵn.

## Đề bài

Bài không có code. Làm 7 câu trắc nghiệm trong app (card **Trắc nghiệm**): 6 câu chọn một đáp án, 1 câu chọn mọi đáp án
đúng. Đọc README module (mục 2 đến 6) trước khi làm sẽ dễ hơn.

Mỗi tình huống nên tự hỏi: thay đổi này chạm vào code, dữ liệu hay model? Việc nào phải chặn merge, việc nào chỉ cần chạy khi có
lý do? Giá phải trả của phương án là gì?

## Tiêu chí đạt

- Đúng ít nhất 5/7 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định và điều kiện để phương án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đọc lời giải.

## Gợi ý

### Gợi ý 1

Một workflow trả lời "thay đổi này có phá thứ đang chạy không"; workflow kia trả lời "model mới có đáng thay model đang chạy
không". Hai câu hỏi có chi phí, tần suất và người chịu trách nhiệm khác nhau.

### Gợi ý 2

Cơ chế che secret của runner nhận diện giá trị nguyên văn. Hãy nghĩ điều gì xảy ra với bản đã biến đổi.
