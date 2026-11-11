---
title: Game day - runbook chẩn đoán bằng observability, khôi phục và postmortem
level: advanced
services: []
files:
  - path: starter/runbook.yaml
    note: Phần máy chạy của runbook
  - path: starter/RUNBOOK.md
    note: Runbook cho người đọc
  - path: starter/POSTMORTEM.md
    note: Khung postmortem, 7 phần
  - path: tests/test_game_day.py
    note: Không sửa
  - path: tests/fixtures/compose.yaml
    note: Olist Shop của game day
  - path: tests/fixtures/POSTMORTEM.good.md
    note: Ví dụ postmortem đạt (game day khác)
  - path: tests/fixtures/RUNBOOK.good.md
    note: Ví dụ runbook đạt (dịch vụ khác)
run:
  - nice -n 15 docker build --pull=false -t devops-track/netem:1.0 setup/netem
  - uv run pytest tracks/devops/modules/16-sre-operations/exercises/advanced/01-game-day-runbook -q -rs -s
---

## Mục tiêu

Chạy một game day nhỏ: một lỗi không báo trước được bơm vào Olist Shop đang có traffic; runbook của bạn phải tự chẩn đoán bằng
metric hay log của stack observability, chọn đúng hành động khôi phục, và không báo động giả khi hệ thống khoẻ. Sau đó viết
postmortem không đổ lỗi cho lần game day đó.

## Đề bài

Cần Docker, các image của stack observability (module 13), `postgres:16.15-alpine`, `redis:7.4.12-alpine`,
`python:3.12.16-slim-trixie` và image `devops-track/netem:1.0` (lệnh build ở trên, xem `## 0. Cài đặt` của module). Mỗi lần chạy
mất khoảng 1 phút; test có 4 lần.

**Test làm gì, mỗi seed một lần:**

1. Dựng Olist Shop (`tests/fixtures/compose.yaml`: api, worker, postgres, redis) cùng `testkit.ObsStack`, rồi chạy một khách giả liên
   tục: tra đơn, gọi `/readyz`, thỉnh thoảng `POST /jobs/recompute`. Một request **đạt** khi đúng mã mong đợi (200 hay 404, 200, 202)
   và trả lời dưới 0,5 giây.
2. Chờ trạng thái ổn định (mọi request đạt trong 10 giây liên tục), rồi đánh giá mọi entry của runbook: entry nào khớp lúc này là báo
   động giả, test fail.
3. `testkit.FaultInjector(lab, seed=..., services=["api", "redis"])` bơm **một** lỗi. Bạn không biết trước lỗi gì.
4. Mỗi 2 giây, đánh giá các entry theo thứ tự trong tệp; entry **đầu tiên** khớp được chọn, tối đa 120 giây. Hành động của entry đó
   được chạy một lần.
5. Hệ thống phải khoẻ lại (mọi request đạt trong 10 giây liên tục) trong 120 giây sau hành động.

Với `-s`, test in tóm tắt mỗi lần: seed, lỗi đã bơm, entry đã khớp, thời gian phát hiện và khôi phục. Dùng nó cho postmortem.

**1. `starter/runbook.yaml`:** 2 tới 10 entry, mỗi entry đúng ba khoá:

```yaml
entries:
  - id: api-unreachable              # chữ thường, số, '-', không trùng
    detect:
      promql: up{job="olist-api"} == 0   # hoặc logql: '{service_name="olist-shop-api"} |= "..."'
    action:
      do: start                      # start, restart hoặc recreate
      service: api                   # api, worker, postgres hoặc redis
```

- `promql`: instant query trên Prometheus của stack; **khớp** khi kết quả khác rỗng (viết điều kiện bằng `> ngưỡng`, `== 0`).
  Prometheus scrape `olist-api` (metric `http_requests_total`, `http_request_duration_seconds`, `jobs_enqueued_total`) và
  `olist-worker` mỗi 5 giây.
- `logql`: log query (bắt đầu bằng `{`) trên Loki; khớp khi có ít nhất một dòng log **kể từ lúc bắt đầu đánh giá** (lúc bơm lỗi,
  hay lúc traffic bắt đầu khi kiểm báo động giả). Log của API có nhãn `service_name="olist-shop-api"`, của worker là
  `olist-shop-worker`.
- `action` chạy `docker compose start|restart <service>` hay `docker compose up -d --no-deps --force-recreate <service>` trên project
  của lab.

**2. `starter/RUNBOOK.md`:** mỗi entry một phần `## <id>` với năm mục `### Triệu chứng`, `### Chẩn đoán`, `### Khôi phục`,
`### Xác nhận`, `### Leo thang`, mỗi mục ít nhất 40 ký tự. Mục Chẩn đoán chép nguyên truy vấn `detect`; mục Khôi phục nêu hành động
(ví dụ `start api`).

**3. `starter/POSTMORTEM.md`:** postmortem cho **một** lần game day bạn đã chạy, giữ bảy tiêu đề. Test kiểm: không còn `TODO`; phần 1
ít nhất 200 ký tự văn xuôi và ghi `seed <số>`; phần 2 có số liệu và nói error budget đã tiêu; phần 3 ít nhất 5 dòng bảng bắt đầu bằng
`HH:MM:SS`, theo thứ tự; phần 4 ít nhất 2 gạch đầu dòng; phần 5 nêu id entry đã phát hiện trong dấu backtick; phần 6 ít nhất 3 gạch đầu
dòng; phần 7 bảng ít nhất 3 action item có người phụ trách (cột 2) và hạn `YYYY-MM-DD`; không có cụm đổ lỗi cho người (ví dụ "cẩu thả").

Test còn chạy bộ kiểm runbook và postmortem trên các fixture (tệp hỏng, bản yếu, bản đạt) để chứng minh nó bắt được lỗi. Nội dung
chấm bằng rubric trong `SOLUTION.md`; đọc rubric **sau** khi làm xong.

## Tiêu chí đạt

- `uv run pytest ... -q -rs` pass, không skip.
- Rubric trong `SOLUTION.md` đạt từ 7/10.
- Trả lời được: giả thuyết trạng thái ổn định của game day là gì; blast radius được giới hạn thế nào; vì sao một entry "có 5xx thì
  restart mọi thứ" vừa nguy hiểm vừa không qua test.

## Gợi ý

### Gợi ý 1

Chạy thử với runbook một entry rồi đọc tóm tắt in ra bằng `-s` và log của test khi fail: lỗi nào làm route nào hỏng, hỏng kiểu gì
(lỗi, chậm, mất kết nối)? Mỗi kiểu hỏng để lại dấu vết khác nhau trên metric và log. Xem thêm dashboard bằng cách chạy stack tay
theo `setup/DEVOPS-TOOLS.md`.

### Gợi ý 2

Route tra đơn chỉ dùng Postgres, `/jobs/recompute` dùng Redis, `/readyz` dùng cả hai. So sánh các route với nhau cho biết thành phần
nào đang có vấn đề. Đặt entry cụ thể nhất lên trước entry chung chung.
