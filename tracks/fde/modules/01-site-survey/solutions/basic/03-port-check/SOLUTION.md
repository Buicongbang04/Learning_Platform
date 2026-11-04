# Lời giải: Cổng nào đang bị chiếm

Lời giải ở `check_ports.sh` cạnh tệp này. Chạy:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/01-site-survey/exercises/basic/03-port-check -q
```

## Cách làm

1. Lấy bảng một lần: `ss -H -t -l -n -p` (không tiêu đề, TCP, chỉ LISTEN, không phân giải tên, kèm tiến trình nếu thấy).
2. Với mỗi cổng, `awk` tách cột 4 theo `:` và so **phần tử cuối** với cổng: đúng cho `127.0.0.1:28080`, `[::]:22`,
   `127.0.0.53%lo:53`, `*:22`, và không nhầm `8080` với `28080`.
3. Có dòng khớp ⇒ `busy`; tên tiến trình lấy từ `users:(("python3",pid=...` bằng `sed`, không có thì `unknown`.

## Vì sao `unknown` là câu trả lời đúng

User thường không đọc được `/proc/<pid>/fd` của tiến trình user khác, nên `ss` không nối được socket với tiến trình.
`ss -e` vẫn cho thấy `uid:0`, nhưng "root đang giữ cổng" chưa phải tên tiến trình. Báo `unknown` và ghi trong báo cáo
khoảng cách "cổng 18080 đang có tiến trình của user khác nghe, nhờ IT kiểm `sudo ss -tlnp 'sport = :18080'`" là đúng
vai: bạn chỉ ra chỗ cần nhìn, IT (có quyền) xác nhận.

## Output trên bốn hồ sơ

Cả bốn: `18080 free`, `22 busy unknown`. Trên máy khách thật hay gặp `18080` bị chiếm bởi agent giám sát, Jenkins agent,
hay một bản thử nghiệm cũ: hỏi trước, đừng tự `kill`.

## Lỗi hay gặp

- `netstat -tlnp`: không có trên Rocky cloud image (gói `net-tools` đã lỗi thời).
- `grep ":$port"`: `:80` khớp cả `:8080`; `grep ":$port "` lại hỏng khi cột được căn lề khác nhau giữa các bản `ss`.
- Gọi `sudo ss -p` "cho đủ thông tin": trên `lab-open` chạy được, trên `bank` thì không, và đề cấm.
- Thử `bind` vào cổng bằng `nc`/Python để xem có lỗi `Address already in use` không: thay đổi trạng thái máy khách và
  cần công cụ không chắc có.
