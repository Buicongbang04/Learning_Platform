# Lời giải: CI cho code và CT cho model

| Câu | Đáp án | Lập luận |
| --- | --- | --- |
| ci-vs-ct | b | Đổi `src/` kích hoạt CI: lint, test, build. Train lại, đăng ký, đổi alias thuộc lớp data/model và có trigger riêng. |
| seam | d | Mỗi lớp xanh riêng vẫn có thể giao sai thứ cho lớp kia. Chỗ nối cần định danh kiểm được (version, digest, run) ở cả hai đầu. |
| trigger-choice | b | Path filter chỉ thấy commit. Dữ liệu mới không có commit nên cần lịch cộng điều kiện so phiên bản; chạy mỗi phút là lãng phí. |
| oidc | a | OIDC cấp token ngắn hạn theo danh tính workflow, bạn cấu hình quan hệ tin cậy ở phía cloud. Không có khoá dài hạn thì không có gì để rò rỉ hay xoay vòng. |
| secrets-log | a, b, d | Cơ chế che chỉ khớp chuỗi nguyên văn. Workflow từ fork không nhận secrets theo mặc định (c sai). |
| act-limits | c | `act` tiện để lặp nhanh, không thay thế một lần chạy trên runner thật: image khác, không OIDC, một số ngữ nghĩa (bộ lọc `paths`, quyền) do máy chủ xử lý. |
| tool-choice | a | Công cụ đã có runner, quyền và thói quen thắng công cụ "tốt hơn" trên giấy. Chuyển sang GitHub hay Jenkins chỉ vì tên là chi phí không mua được gì. |
