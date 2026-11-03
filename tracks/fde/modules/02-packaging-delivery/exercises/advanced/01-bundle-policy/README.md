---
title: Định dạng bundle và chính sách version cho ba khách
level: advanced
services: []
files:
  - path: starter/bundle-policy.md
    note: Khung tài liệu 5 phần
run: []
---

## Mục tiêu

Ba khách, ba môi trường, một sản phẩm. Bài này luyện quyết định thứ đội sản phẩm thường để FDE tự xoay: **một** định
dạng bundle phục vụ được cả ba, hợp đồng version mà khách ký được, và đường giao hàng cho từng nơi. Đây là tài liệu bạn
đưa cho trưởng nhóm sản phẩm, không phải cho khách.

## Đề bài

Sản phẩm `quillo` (`tracks/fde/product/`) phát hành một MINOR mỗi tháng. Bundle hiện tại `quillo-1.0.0.tar` là **1,08
GiB**: image `pgvector` 156 MB, `llama.cpp` server 309 MB, `quillo-api` 59 MB, model chat `llm-small` 491 MB, model
embedding 146 MB (bảng trong `tracks/fde/product/README.md`); `llm-medium` thay `llm-small` thì nặng thêm ~0,6 GB. Lộ
trình: 1.1.0 thêm cột `tags` có `DEFAULT` (đã phát hành); 1.2.0 thêm cột `tenant_id` có `DEFAULT`; **2.0.0** (quý 2/2027)
đổi model embedding, mọi tài liệu phải embed lại (ước tính 3 giờ cho 100 000 trang trên CPU) và bỏ cột embedding cũ.

| | Bệnh viện Đa khoa Sông Hồng | Ngân hàng Hải Đăng | Công ty Luật Minh Tâm |
| --- | --- | --- | --- |
| Máy | Ubuntu 20.04, đĩa 8 GB (IT hứa nới lên 40 GB quý sau), 16 GB RAM | Rocky Linux 8, SELinux enforcing, 64 GB RAM | Hai máy Ubuntu 22.04: staging và prod |
| Runtime | Docker 26 từ kho Ubuntu, **không** có plugin compose | Podman rootless, **không** sudo | Docker từ kho Ubuntu, không plugin compose; registry nội bộ HTTP |
| Mạng | Ra ngoài qua proxy có TLS inspection | Không có | Không có |
| Đưa tệp vào | SFTP qua VPN của viện, chậm (~2 MB/s) | Cổng truyền tệp MFT, quét mã độc, **tối đa 2 GB/tệp**; mỗi thành phần mới (image, binary) qua An ninh thông tin duyệt 5 ngày làm việc | FDE mang ổ USB đã mã hoá tới văn phòng |
| Thay đổi | Cửa sổ thứ Năm hằng tuần, 2 giờ | CAB; cửa sổ tối thứ Bảy, 4 giờ; nâng cấp **tối đa mỗi quý** | Muốn tính năng mới hằng tháng; mỗi bản chạy staging 2 tuần rồi mới lên prod |
| Yêu cầu thêm | Một người IT, cần hướng dẫn từng bước | Quay về được bản cũ **trong cùng cửa sổ**; muốn biết trong bundle có gì | Hai luật sư IT kiêm nhiệm |

Viết `starter/bundle-policy.md` (5 phần có sẵn). Bài không có test; tự chấm theo rubric, đạt đủ 10 mục, rồi so với bài mẫu
trong `solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| B1 | **Một** định dạng bundle cho cả ba khách (không build riêng cho từng khách), có cây thư mục và danh sách trường của manifest, gồm ít nhất: tên, version, nền tảng đích, sha256 **và** kích thước từng tệp, image kèm digest, phạm vi schema/migration |
| B2 | Tách lớp theo tần suất thay đổi (vd. nền: model + image ít đổi; ứng dụng: đổi hằng tháng), mỗi lớp có kích thước ước tính tính từ số liệu đề, và cách đáp ứng giới hạn 2 GB/tệp của ngân hàng |
| B3 | Cùng image tarball chạy được trên Docker và Podman; nói rõ mỗi khách khởi chạy bằng gì (compose binary mang theo, hay unit systemd/Quadlet cho Podman rootless) và thứ đó nằm trong bundle hay không, kèm một điểm SELinux cần xử lý |
| B4 | Hợp đồng version: PATCH/MINOR/MAJOR định nghĩa bằng **migration và khả năng quay lại**, không bằng "lớn/nhỏ"; xếp đúng 1.1.0, 1.2.0, 2.0.0 của lộ trình vào bảng đó |
| B5 | Đường nâng cấp cho khách nhảy nhiều MINOR (ngân hàng nâng mỗi quý): hoặc chuỗi migration được kiểm trên đúng đường nhảy, hoặc bắt buộc bản trung gian; nói cái nào và vì sao |
| B6 | Cửa sổ hỗ trợ (bao nhiêu bản được vá) và cách giao bản vá khẩn: là một PATCH đầy đủ qua cùng quy trình kiểm, không phải chép tay một tệp |
| B7 | Rollback: với từng loại bản, quay lại bằng gì và mất bao lâu; 2.0.0 có kế hoạch riêng (backup trước, embed lại ngoài giờ hay theo lô) vừa cửa sổ 4 giờ của ngân hàng hoặc nói rõ vì sao không vừa và làm gì |
| B8 | Cấu hình theo khách nằm **ngoài** bundle; với mỗi khách nêu ít nhất hai khác biệt cụ thể đến từ bảng đề (proxy/CA, registry, đĩa, Podman/SELinux, staging/prod…) |
| B9 | Toàn vẹn và nguồn gốc: sha256 của bundle qua kênh riêng, chữ ký (cosign với khoá, kiểm offline), khoá công khai giao một lần; SBOM cho ngân hàng |
| B10 | Bảng giao hàng theo khách: kênh, kích thước thực tế mỗi lần cập nhật thường kỳ, thời gian truyền ước tính (bệnh viện ~2 MB/s), tần suất, ai cài, và cách tận dụng staging của công ty luật |

## Tiêu chí đạt

- `bundle-policy.md` đạt đủ B1–B10 khi tự chấm từng mục.
- Mọi kích thước và thời gian trong tài liệu tính lại được từ số liệu đề (ghi phép tính hoặc nguồn).

## Gợi ý

### Gợi ý 1

Bắt đầu từ khách khó nhất ở mỗi chiều: kênh hẹp nhất (bệnh viện, 2 MB/s), quy trình chậm nhất (ngân hàng, duyệt 5 ngày
cho mỗi thành phần mới), nhịp nhanh nhất (công ty luật). Định dạng phục vụ được ba "cực" đó thì phục vụ được khách thứ tư.

### Gợi ý 2

Hỏi với từng thứ trong bundle: nó đổi bao lâu một lần, và khi nó đổi thì ai phải duyệt lại?

### Gợi ý 3

"Quay lại được" khác nhau giữa mã và dữ liệu. Viết ra trạng thái của database sau mỗi bản trong lộ trình rồi hỏi: bản
trước chạy được trên đó không?
