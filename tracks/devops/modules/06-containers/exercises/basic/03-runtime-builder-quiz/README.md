---
title: Chọn runtime, builder và cách tham chiếu image theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn đúng công cụ trong hệ container (Docker Engine, Podman, containerd, nerdctl, BuildKit, Buildah, Kaniko, LXD) từ ràng buộc
thật, phân biệt tag với digest, và đọc đúng triệu chứng như exit 137.

## Đề bài

Bài này không có code. Làm 9 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới): 8 câu chọn một đáp án, câu cuối chọn
mọi đáp án đúng. Các câu đi qua: tham chiếu image trong manifest production, vì sao digest của một tag đổi, build image trong CI
không có socket Docker, máy dev cấm daemon root, runtime của node Kubernetes, system container, điều tra image distroless, exit
137, và các thiết lập giảm bề mặt tấn công.

Trước khi chọn, với mỗi tình huống tự hỏi:

1. Có được chạy daemon không, daemon đó có quyền root không?
2. Có được `privileged` hay mount `/var/run/docker.sock` không?
3. Thứ cần chạy là một tiến trình (application container) hay cả một hệ điều hành (system container)?

## Tiêu chí đạt

- Trả lời đúng ít nhất 7/9 câu.
- Với mỗi câu sai, nói lại được ràng buộc quyết định và điều kiện để phương án bạn chọn trở thành đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Docker Engine, Podman và nerdctl là CLI và engine; containerd và CRI-O là runtime mà kubelet gọi qua CRI; runc là low-level
runtime tạo namespace và cgroup. BuildKit, Buildah và Kaniko chỉ build image.

### Gợi ý 2

Tag là con trỏ có thể dời; digest là SHA-256 của manifest và không đổi được. Exit 137 nghĩa là tiến trình chết vì SIGKILL
(128 + 9); còn ai gửi SIGKILL thì xem `State.OOMKilled` và log của `docker stop`.
