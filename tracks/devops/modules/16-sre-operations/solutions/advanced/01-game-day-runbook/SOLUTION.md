# Lời giải: game day, runbook và postmortem

Bài Advanced không có một đáp án duy nhất. `runbook.yaml`, `RUNBOOK.md`, `POSTMORTEM.md` trong thư mục này là một lời giải qua test;
rubric bên dưới mới là thứ chấm nội dung.

## Bốn lỗi của test

| Seed | Lỗi | Dấu vết | Entry khớp trong lời giải mẫu |
| --- | --- | --- | --- |
| 14 | `kill` vào api | `up{job="olist-api"}` về 0, client mất kết nối | `api-unreachable` |
| 18 | `net-delay` vào api | p95 mọi route lên gần 1 giây, không lỗi | `api-slow` |
| 23 | `disk-full` vào redis (tmpfs `/data` 16 MiB, AOF bật) | Redis từ chối ghi (`MISCONF ... No space left on device`), `POST /jobs/recompute` 503, `/readyz` vẫn 200 | `queue-rejected` |
| 24 | `redis-stop` | `POST /jobs/recompute` 503, `/readyz` 503, worker log mất kết nối Redis | `queue-rejected` |

Lời giải mẫu còn xử lý được hai lỗi mà m09 có thể bơm: `kill` vào redis (như seed 24) và `net-delay` vào redis (`queue-slow`).

## Hướng làm

- Tách theo **triệu chứng của từng route**: tra đơn chỉ chạm Postgres, `/jobs/recompute` chạm Redis. "Tra đơn chậm" nghĩa là API (hay
  đường mạng của nó) có vấn đề; "đẩy job lỗi hay chậm trong khi tra đơn khoẻ" nghĩa là Redis.
- Đặt entry cụ thể trước: `api-unreachable` (`up == 0`) trước `api-slow`, vì API chết thì histogram cũng có thể trông lạ.
- `restart` sửa được cả container đã dừng lẫn container còn chạy nhưng hỏng (network namespace và tmpfs tạo lại). `start` chỉ đủ khi
  container đã thoát. `recreate` mạnh nhất nhưng đổi container ID và xoá luôn bằng chứng.
- Ngưỡng: p95 trên 0,3 giây trong cửa sổ 1 phút đủ nhạy (lỗi trễ đẩy p95 lên 0,8 tới 1 giây) và đủ im khi khoẻ (khoảng 10 ms).
- LogQL hợp khi metric không phân biệt được nguyên nhân: cùng 503 trên `/jobs/recompute`, nhưng dòng log `không đẩy được job vào redis`
  kèm exception cho biết lỗi ở Redis chứ không ở API.

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Runbook phân biệt thành phần hỏng bằng triệu chứng (route, loại lỗi), không có entry "bắt mọi 5xx" | 2 |
| Mỗi entry có giả thuyết rõ: vì sao truy vấn này im khi khoẻ và khớp khi hỏng, ngưỡng có lý do | 1 |
| Hành động nhỏ nhất đủ khôi phục, có bước lưu bằng chứng trước khi restart hay recreate | 1 |
| Mục Xác nhận đo bằng số (SLI về ngưỡng trong bao lâu), không phải "xem dashboard" | 1 |
| Mục Leo thang có thời hạn, người nhận, kênh liên lạc | 1 |
| Postmortem: tóm tắt đọc một lần hiểu được chuyện gì xảy ra, tác động có số và error budget | 1 |
| Timeline khớp với tóm tắt test in ra (thời điểm bơm, phát hiện, khôi phục) | 1 |
| Nguyên nhân nói về hệ thống (thiếu alert, thiếu retry, thiếu healthcheck), không đổ cho người | 1 |
| Action item cụ thể, có người và hạn, mỗi bài học có ít nhất một action item | 1 |

Trừ điểm: entry khớp nhờ may mắn (ví dụ `up == 0` dùng cho lỗi chậm), hành động `recreate postgres` (mất dữ liệu), postmortem kể lỗi
mà không nói hệ thống đã thiếu gì để phát hiện sớm hơn.

## Câu hỏi kèm theo

- **Giả thuyết trạng thái ổn định**: với traffic giả, mọi request đúng mã và dưới 0,5 giây; game day chỉ bắt đầu khi điều đó đúng 10 giây
  liên tục, và test kiểm runbook im lặng lúc đó.
- **Blast radius**: lỗi chỉ vào container có nhãn của lab, chỉ service `api` và `redis`, một lỗi mỗi lần, có hoàn tác tự động khi test
  kết thúc (kể cả khi fail).
- **"Có 5xx thì restart mọi thứ"**: test chỉ chạy hành động của **một** entry; restart nhầm thành phần làm sự cố dài thêm và xoá bằng
  chứng. Trên production, restart đồng loạt còn gây thundering herd và có thể làm mất dữ liệu.
