# Câu hỏi phỏng vấn: Đóng gói cho môi trường lạ

## Bạn cần giao một sản phẩm gồm vài container, một app Python và một model 2 GB cho khách không có internet. Bundle gồm những gì?

Trước hết hỏi máy đích: kiến trúc, OS/glibc, runtime container, Python có sẵn, đĩa, cách đưa tệp vào và giới hạn kích
thước. Rồi mỗi thành phần một dạng: image bằng `docker save` theo tag, đúng `--platform`; thư viện Python là wheelhouse
build cho Python/ABI/glibc của đích kèm `requirements.txt` có hash; công cụ thiếu (compose, uv) là binary tĩnh ghim
sha256; model là tệp riêng kèm sha256. Cộng manifest (sha256 + kích thước từng tệp, version, đích), installer, cấu hình mặc
định, tài liệu, SBOM và chữ ký.

Điểm muốn nghe: bundle được thiết kế từ **đích** ngược lại, và lúc cài không tải gì cả.

## Khách gửi ảnh chụp: `exec format error` khi chạy container từ bundle của bạn. Bạn nghĩ gì đầu tiên, kiểm thế nào?

Sai kiến trúc: image build trên máy ARM (Mac Apple Silicon) mang tới máy x86, hoặc ngược lại. Kiểm không cần chạy:
`docker image inspect --format '{{.Os}}/{{.Architecture}}'` trên máy khách, hoặc đọc config blob trong tarball. Sửa ở
nguồn: build và save với `--platform linux/amd64`, và thêm bước kiểm kiến trúc vào pipeline đóng gói để lần sau không lọt
tới khách. Trong lúc chờ, không đề nghị khách cài QEMU binfmt để "chạy tạm".

## Tại sao không gửi khách `requirements.txt` và bảo họ `pip install` qua proxy?

Vì kết quả phụ thuộc thứ bạn không kiểm soát: proxy soi TLS làm pip lỗi chứng chỉ, mirror nội bộ thiếu bản, PyPI có bản
mới của phụ thuộc bắc cầu, máy không có trình biên dịch cho sdist. Mỗi lần cài là một lần resolve khác nhau. Wheelhouse
offline với hash cố định thì lần cài nào cũng ra cùng một thứ, kiểm được trước, và chạy được cả khi proxy đổi cấu hình.

## Wheelhouse bạn build trên laptop cài lỗi trên máy khách: "No matching distribution found". Vì sao, và sửa thế nào?

Wheel có phần biên dịch gắn với một bộ (CPython, ABI, nền tảng/glibc). Laptop Python 3.12 tải wheel `cp312`; máy khách
3.10 cần `cp310`. Gói thuần Python lọt nên lỗi chỉ hiện ở vài gói. Sửa: lấy thông số đích từ survey, `pip download
--only-binary=:all: --python-version … --abi … --platform manylinux_2_xx_x86_64`, và ghi đích vào manifest để preflight từ
chối máy không khớp. Nhiều đích thì nhiều wheelhouse, hoặc chọn chiến lược khác (container, Python mang theo).

## Manifest sha256 nằm trong bundle chống được gì và không chống được gì?

Chống hỏng hóc khi chuyển: tar cụt, bit lỗi, thiếu hay thừa tệp. Không chống người cố ý sửa, vì kẻ sửa được bundle thì sửa
luôn được manifest. Muốn chứng minh nguồn gốc thì neo manifest ra ngoài: gửi sha256 của cả bundle qua kênh khác, hoặc ký
bundle bằng khoá riêng và giao khoá công khai qua kênh riêng một lần. Ghi thêm `size` để installer tính được chỗ trống
trước khi giải nén.

## Ký bundle bằng cosign cho khách air-gapped khác gì cách ký keyless thường thấy trên GitHub?

Keyless dựa vào OIDC (danh tính CI) và transparency log công khai (Rekor), cả lúc ký lẫn lúc kiểm đều cần internet. Khách
air-gapped không kiểm được log, nên ký bằng **khoá** (`generate-key-pair`, `sign-blob --key` tắt tlog), khách kiểm offline
bằng `verify-blob --key cosign.pub --insecure-ignore-tlog=true`. Đổi lại mất bằng chứng công khai về thời điểm ký, nên quản
lý khoá thành việc của mình: ai giữ, mật khẩu tách người, xoay định kỳ, quy trình thu hồi và báo khách.

## Khách nói: "IT bên em lỡ chạy installer hai lần, có sao không?" Bạn muốn câu trả lời là gì, và thiết kế installer thế nào cho đúng như vậy?

Câu trả lời mong muốn: "không sao, lần hai không đổi gì". Muốn vậy installer phải hội tụ: so trạng thái hiện có với trạng
thái mong muốn trước khi ghi (`cmp`, so manifest đã cài, `is-enabled`), không restart nếu không có gì đổi, không ghi đè cấu
hình khách đã sửa, và in rõ "unchanged". Test bằng cách chạy hai lần rồi so inode/mtime/PID, không chỉ so exit code.

## Installer của bạn phải làm gì trước khi dừng bản đang chạy?

Mọi thứ có thể thất bại: kiểm quyền và công cụ, kiểm chỗ trống bản mới cần (đọc từ manifest), giải nén vào một thư mục release
mới (chưa dùng), kiểm sha256 từng tệp, nạp image. Chỉ khi bản mới đã nằm đủ và đúng trên đĩa mới đổi bản
(symlink nguyên tử) và restart; health check thất bại thì quay về. Mục tiêu: cài thất bại thì khách mất **không** phút
dịch vụ nào, chỉ mất thời gian của bạn.

## Khách hỏi: "Lên 1.3 rồi có quay lại 1.2 được không?" Bạn trả lời dựa vào đâu?

Vào migration của bản đó, không vào số version. Nếu 1.3 chỉ thêm (cột có default, bảng mới) thì code 1.2 vẫn chạy trên
schema 1.3: quay lại chỉ là đổi bản chạy. Nếu có bỏ hay đổi dữ liệu thì quay lại chỉ bằng khôi phục backup, mất dữ liệu
phát sinh sau đó. Hợp đồng version nên ghi đúng điều này cho PATCH/MINOR/MAJOR, và thay đổi phá vỡ nên tách expand/contract
để phần lớn bản nâng cấp đều quay lại được.

## Khách ngân hàng nâng cấp mỗi quý, tức là nhảy ba bản một lần. Bạn chuẩn bị gì?

Chuỗi migration liên tục chạy được từ bất kỳ schema nào trong phạm vi hỗ trợ, và CI test đúng đường nhảy N−3 → N (cả quay
lại) trên dữ liệu mẫu cỡ thật. Hoặc nếu không làm được, chính sách ghi rõ bản trung gian bắt buộc. Thêm: lớp nền (image,
model) ít đổi để không phải duyệt bảo mật lại mỗi lần, runbook nâng cấp đo thời gian trên staging để biết có vừa cửa sổ
không.

## Bộ phận an ninh của khách hỏi: "Trong bundle có gì?" Bạn đưa họ cái gì?

SBOM chuẩn (CycloneDX hoặc SPDX) cho từng image và phần Python, tạo tự động lúc build (syft, `uv export --format
cyclonedx1.5`); danh mục thành phần có nguồn, digest và giấy phép (kể cả model, thứ SBOM image không liệt kê); kết quả
quét lỗ hổng lúc phát hành kèm cách họ tự quét offline; chính sách xử lý CVE theo mức độ. Không hứa "không có CVE".

## Cổng truyền tệp của khách giới hạn 2 GB một tệp, bundle của bạn 3,5 GB. Làm sao?

Ngắn hạn: `split -b 1900M`, manifest ngoài ghi sha256 từng phần và tệp ghép, installer ghép rồi kiểm trước khi làm gì
khác. Dài hạn: tách bundle theo tần suất thay đổi (lớp nền gồm image base + model, lớp ứng dụng vài chục MB) để lần cập nhật
thường kỳ chỉ còn lớp nhỏ, đi nhanh qua cổng và không kích hoạt duyệt lại các thành phần nặng.

## Khách muốn bạn "build riêng cho bên em một bản có cấu hình sẵn". Bạn xử lý thế nào?

Giải thích rằng một bản build riêng là một bản phải test, vá, ký riêng, và đó là thứ làm chậm bản vá bảo mật cho chính họ.
Đề xuất: cùng bundle cho mọi khách, cấu hình riêng nằm trong hồ sơ khách (ngoài bundle) mà installer áp vào, bí mật sinh tại
chỗ. Khi khách có yêu cầu thật sự khác (đích khác, runtime khác) thì đó là một **đích** mới trong ma trận build, không phải
một nhánh mã.
