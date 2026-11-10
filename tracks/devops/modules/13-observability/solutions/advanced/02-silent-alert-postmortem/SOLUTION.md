# Lời giải: postmortem "alert im lặng"

`POSTMORTEM.md` trong thư mục này là một bản qua test. Rubric bên dưới chấm nội dung.

## Hướng làm

1. Dựng timeline trước, sắp theo giờ. Hai mốc tính số: ảnh hưởng 21:02 tới 21:58 là **56 phút**; con người biết lúc 21:38, tức **36 phút**
   sau khi lỗi bắt đầu, dù alert đã bắn lúc 21:09.
2. Đi theo đường đi của alert: rule đúng và bắn (Prometheus), tới Alertmanager (có trong `/api/v2/alerts`), trạng thái `suppressed`,
   `silencedBy` rỗng, `inhibitedBy` trỏ fingerprint `3f1c9a7e52b0d6a4` của `MaintenanceMode`. Vậy bước chặn là inhibit.
3. Đọc `inhibit_rules`: luật thứ nhất có `equal: [service, alertname]`, luật thứ hai không có `equal`. Không có `equal` nghĩa là không
   cần nhãn nào trùng: một alert nguồn bất kỳ đang bắn chặn mọi alert đích ở mọi service.
4. Giải thích các dữ kiện phụ bằng cùng nguyên nhân: sự cố 2026-10-08 (ticket đĩa bị chặn khi Search bảo trì), Watchdog vẫn đều (route riêng,
   `severity="none"` không khớp target), `amtool check-config` qua (chỉ kiểm cú pháp).
5. Tách hai chuỗi nguyên nhân: vì sao khách bị lỗi (pool kết nối, canary ngắn) và vì sao không ai biết (inhibit thiếu `equal`, bảo trì mô
   hình hoá bằng inhibit, CI chỉ kiểm cú pháp, review không có chủ sở hữu cấu hình chung, không đo alert bị suppress).
6. Mỗi nguyên nhân hệ thống một action item, có người, có hạn.

## Rubric (10 điểm)

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Timeline và số liệu | 1,5 | Timeline đủ mốc, đúng thứ tự; 56 phút ảnh hưởng, 36 phút tới khi con người biết, 7 phút alert bắn, 20 phút xử lý; ước tính đơn thất bại có cách tính |
| Đúng cơ chế | 2 | Chỉ ra luật inhibit thứ hai thiếu `equal`, dẫn bằng chứng `inhibitedBy`/fingerprint; giải thích vì sao thiếu `equal` làm nó chặn mọi service |
| Giải thích dữ kiện phụ | 1,5 | Watchdog không cứu được vì sao; `check-config` qua vì sao; liên hệ đúng sự cố 2026-10-08 như tín hiệu bị bỏ lỡ |
| Hai chuỗi nguyên nhân | 1 | Tách nguyên nhân lỗi của khách (pool, canary) khỏi nguyên nhân im lặng; không dừng ở "deploy lỗi" |
| Blameless | 1 | Không đổ cho người viết hay người duyệt PR; hỏi "vì sao hệ thống cho phép" (không có chủ sở hữu, không có test hành vi) |
| Thứ tự xử lý | 1 | Giảm thiểu (rollback) trước, điều tra sau; sửa cấu hình mà vẫn giữ ý định của team Search (silence có phạm vi) |
| Action items | 2 | Có phòng ngừa (silence thay inhibit, lint `equal`, CODEOWNERS), phát hiện (test Alertmanager thật, alert về alert bị suppress, diễn tập page), và cho lỗi gốc của API; mỗi việc có người và hạn hợp lý |

## Câu hỏi để tự kiểm

- **Vì sao Watchdog không cứu được?** Watchdog chứng minh Prometheus đánh giá rule và Alertmanager gửi được tới một receiver. Nó đi route
  riêng và không khớp target của luật inhibit, nên không bị chặn. Bước hỏng nằm sau Watchdog trên đường đi của alert khác.
- **Vì sao `amtool check-config` qua?** Cấu hình hợp lệ về cú pháp; thiếu `equal` là cấu hình hợp lệ (đôi khi cố ý). `amtool config routes
  test` cũng không mô phỏng inhibit. Chỉ gửi alert thật tới Alertmanager mới thấy.
- **Sự cố 2026-10-08 liên quan gì?** Cùng cơ chế: trong lúc `MaintenanceMode` bắn, ticket đĩa Postgres của Olist Shop bị chặn. Đó là lần
  hệ thống đã báo trước mà không ai nhận ra, vì một ticket không tới thì không ai thấy thiếu.
- **Lần sau ai biết, sau bao lâu?** Alert về số alert page bị suppress (khoảng 10 phút sau khi bị chặn), và alert page tự nó tới người trực
  sau khoảng 7 phút vì luật inhibit sai đã bị lint và test CI chặn từ lúc mở PR.

## Lỗi hay gặp khi viết

- Dừng ở "pager không rung" mà không đi tiếp vì sao.
- Đổ cho người duyệt PR: một người không thể nhớ ngữ nghĩa của `equal` vắng mặt; hệ thống cần test hành vi.
- Action item "cẩn thận hơn", "review kỹ hơn": không kiểm được, không có hạn.
