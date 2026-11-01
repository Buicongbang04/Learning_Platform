---
title: Trắc nghiệm - precedence, handler, check mode, push và pull, chọn công cụ
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Trả lời được các câu hỏi tình huống mà người vận hành Ansible gặp hằng tuần: biến nào thắng, handler chạy lúc nào, `--check` tin
được tới đâu, rollout an toàn thế nào; và chọn đúng giữa Ansible, image bất biến, Puppet, Chef, Salt, cloud-init theo ràng buộc.

## Đề bài

Bài này không có code. Làm 14 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 13 câu chọn một đáp án, một câu chọn mọi
đáp án đúng. Đọc mục 2 tới 6 của module trước khi làm.

Với mỗi câu, tự hỏi:

1. Giá trị này được định nghĩa ở **tầng** nào trong danh sách precedence, và có tầng nào cao hơn đang đặt nó không?
2. Task này biết **trạng thái hiện tại** của máy không, hay chỉ chạy một lệnh?
3. Nếu máy thứ hai trong đợt lỗi, chuyện gì xảy ra với máy thứ ba?

## Tiêu chí đạt

- Đúng ít nhất 11/14 câu.
- Với mỗi câu sai, nói lại được vì sao đáp án đúng đúng và khi nào phương án bạn chọn mới đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Bảng precedence ở mục 4: role `defaults` thấp nhất, extra vars (`-e`) cao nhất; role `vars` cao hơn inventory và play vars.
Handler chạy ở điểm flush (sau `pre_tasks`, sau `roles` và `tasks`, sau `post_tasks`, hay ở `meta: flush_handlers`), và không
chạy trên máy đã fail trừ khi bật `force_handlers`.

### Gợi ý 2

Push hay pull là câu hỏi "ai khởi động lần cấu hình": máy điều khiển ngoài vào (Ansible) hay agent trên máy tự kéo về (Puppet,
Chef, `ansible-pull`). Mutable hay immutable là câu hỏi "có sửa máy đang chạy không".
