---
title: Chọn branching strategy và cách merge theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn chiến lược nhánh từ ràng buộc thật (bao nhiêu phiên bản đang chạy, deploy kiểu gì, ai phải duyệt bản phát hành,
CI nhanh tới đâu), không từ thói quen. Nối lựa chọn đó với DORA metrics: chiến lược nhánh là một trong những yếu tố
ảnh hưởng lớn nhất tới lead time for changes.

## Đề bài

Bài này không có code. Làm 10 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 9 câu chọn một đáp án, câu
cuối chọn mọi đáp án đúng. Mỗi câu là một tình huống của Olist Shop hoặc team lân cận: SaaS deploy liên tục, app
mobile phải qua store duyệt, bản cài on-prem nhiều phiên bản, hotfix khi deploy liên tục, cách merge PR, việc lớn kéo
dài nhiều tuần, nhánh theo môi trường.

Trước khi chọn, tự trả lời ba câu hỏi ở mục 3 của lý thuyết:

1. Có bao nhiêu phiên bản của phần mềm đang chạy cùng lúc ở nơi bạn phải hỗ trợ?
2. Ai quyết định lúc phát hành: pipeline (mỗi lần merge), team (theo lịch), hay bên ngoài (store, khách hàng)?
3. Việc dở dang được giấu bằng gì: nhánh, hay feature flag?

## Tiêu chí đạt

- Trả lời đúng ít nhất 8/10 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định trong tình huống, và điều kiện để phương án bạn chọn trở thành
  đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Một bản production và deploy nhiều lần mỗi ngày gần như luôn dẫn tới trunk-based. Nhiều bản cùng chạy (store, on-prem,
thư viện) cần thêm nhánh release để sửa bản cũ, nhưng `main` vẫn là nơi mọi thay đổi đi vào trước.

### Gợi ý 2

Nhánh sống lâu là chi phí: mỗi ngày nhánh tách khỏi `main` là thêm xung đột và thêm thời gian code nằm chờ. Câu hỏi
không phải "nhánh nào", mà "code tôi viết hôm nay mất bao lâu để tới production, và nếu hỏng thì quay lại bằng cách
nào".
