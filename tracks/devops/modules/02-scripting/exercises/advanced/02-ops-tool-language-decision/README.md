---
title: Chọn ngôn ngữ cho công cụ vận hành olistctl - Bash, Python hay Go
level: advanced
services: []
files:
  - path: starter/DECISION.md
    note: Khung ADR, điền mọi TODO
  - path: tests/test_decision.py
    note: Không sửa; kiểm khung, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/02-scripting/exercises/advanced/02-ops-tool-language-decision -q
---

## Mục tiêu

Ra một quyết định công cụ mà team sẽ sống cùng vài năm theo cách bảo vệ được trước tech lead: tách ràng buộc bắt buộc
khỏi sở thích, so sánh bằng tiêu chí gắn với tình huống, nói rõ cái giá, vạch ranh giới để không "viết lại mọi thứ",
và có kế hoạch chuyển đổi từng bước.

## Đề bài

Team vận hành Olist Shop (4 người) có khoảng 40 script Bash, tổng 3.000 dòng, lớn dần trong hai năm: backup, restore,
healthcheck, xoay secret, deploy lên 12 VM qua SSH, gom log khi có sự cố. Ghi chép sau một quý:

- Ba sự cố trong quý do script: một biến rỗng xoá nhầm thư mục, một lần parse output `kubectl` hỏng khi phiên bản đổi
  định dạng, một lần script deploy chạy tiếp sau khi một máy trong 12 máy lỗi.
- Script chạy ở ba nơi: laptop của kỹ sư (2 Ubuntu, 1 macOS, 1 Windows dùng WSL2), runner CI (container Ubuntu), và
  trên chính các VM (Ubuntu 24.04, không có quyền cài gói tuỳ ý, Python hệ thống 3.12).
- Nhiều việc mới cần gọi API (Kubernetes, object storage, PagerDuty) và xử lý JSON lồng nhau.
- Hai người viết Python thạo; một người từng viết Go; người còn lại chỉ viết Bash. Team phát triển Olist Shop dùng
  Python (FastAPI).
- Người trực đêm phải đọc và sửa nóng được công cụ lúc 3 giờ sáng.
- Một số việc (gom log, khởi động lại service trên một máy) chạy qua SSH trên VM, nơi không muốn cài thêm runtime.
- Không có ngân sách cho công cụ trả phí; thời gian chuyển đổi tối đa hai quý, song song với việc vận hành.

Team đề xuất gom tất cả vào một CLI tên `olistctl`. Viết `starter/DECISION.md` dạng ADR:

1. **Bối cảnh**: ràng buộc quyết định lựa chọn, tách bắt buộc và nên có, ít nhất 200 ký tự.
2. **Phương án**: bảng ít nhất 3 dòng, **phải có Bash, Python và Go** (thêm ngôn ngữ khác tuỳ bạn), đủ 6 cột theo
   khung, cột cuối là điểm nguyên 1–5. Cột đầu ghi tên ngôn ngữ (có thể kèm phiên bản hay cách dùng, ví dụ
   `Python 3.12 + uv`).
3. **Quyết định**: dòng `Chọn: <ngôn ngữ>`, tên phải chứa tên một dòng trong bảng (được chọn kết hợp, ví dụ
   `Chọn: Python cho olistctl, giữ Bash cho ...`, miễn chứa đúng tên ở cột đầu của một dòng); lý do gắn với ràng buộc
   và cái giá chấp nhận. Cả phần ít nhất 300 ký tự.
4. **Ranh giới giữa các ngôn ngữ**: ít nhất 2 gạch đầu dòng: phần nào vẫn để Bash (hoặc ngôn ngữ khác), phần nào chuyển,
   vì sao.
5. **Kế hoạch chuyển đổi**: ít nhất 3 bước **đánh số** (`1.`, `2.`...).
6. **Rủi ro và đánh đổi**: ít nhất 3 gạch đầu dòng.
7. **Khi nào xem lại quyết định**: ít nhất 2 tín hiệu cụ thể.

Không còn chữ `TODO` nào. Giữ nguyên các heading `## 1.` tới `## 7.` của khung.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/02-scripting/exercises/advanced/02-ops-tool-language-decision -q` pass. Test
  chỉ kiểm khung và độ dài; chất lượng chấm theo rubric trong
  `solutions/advanced/02-ops-tool-language-decision/SOLUTION.md`.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi ô trong bảng so sánh là nhận định kiểm chứng được cho **tình huống này** (ví dụ "VM có sẵn Python 3.12"), không
  phải nhận xét chung kiểu "dễ học".

## Gợi ý

### Gợi ý 1

Bắt đầu từ ba sự cố: mỗi sự cố là một lớp lỗi. Ngôn ngữ nào loại bỏ lớp lỗi đó theo thiết kế (biến rỗng, parse text,
xử lý lỗi khi chạy song song), ngôn ngữ nào chỉ giảm bằng kỷ luật? Rồi tới phân phối: chạy trên VM không cài được gói
thì "một binary tĩnh" và "Python có sẵn chỉ dùng thư viện chuẩn" đều là lời giải, mỗi cái một giá.

### Gợi ý 2

Đừng chọn một ngôn ngữ cho mọi thứ. Một ranh giới hay gặp: Bash cho đoạn ngắn chủ yếu nối lệnh có sẵn (entrypoint
container, hook, bước CI dưới khoảng 50 dòng), ngôn ngữ thật cho phần có logic, gọi API, xử lý JSON, chạy song song.
Kế hoạch chuyển đổi nên đi theo rủi ro: script gây sự cố trước, script ổn định và ít đổi sau cùng (hoặc không bao
giờ).
