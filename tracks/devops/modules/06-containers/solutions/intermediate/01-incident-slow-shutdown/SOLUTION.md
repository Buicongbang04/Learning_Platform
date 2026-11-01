# Lời giải: worker mất 10 giây mới dừng

## Nguyên nhân

`ENTRYPOINT ["/app/entrypoint.sh"]` làm `/bin/sh` (dash) thành PID 1 của container. Script chạy `python /app/worker.py` như một
tiến trình con (không `exec`), rồi còn một lệnh `echo` sau đó. Chuỗi sự kiện khi `docker stop`:

1. Docker gửi SIGTERM tới PID 1, tức `sh`, không phải Python.
2. Kernel không giao tín hiệu cho PID 1 của một PID namespace nếu tiến trình đó không cài handler cho tín hiệu ấy (ngoại lệ
   duy nhất là SIGKILL và SIGSTOP từ namespace cha). `sh` không cài handler cho SIGTERM, nên tín hiệu bị bỏ. Kể cả khi `sh` nhận
   được, shell không chuyển tiếp tín hiệu cho tiến trình con.
3. Worker không biết gì, tiếp tục xử lý. Hết 10 giây, Docker gửi SIGKILL tới PID 1; namespace bị huỷ, mọi tiến trình chết ngay,
   batch đang dở không được ack. Mã thoát 128 + 9 = 137.

Log `order-sync sẵn sàng` in `"pid": 7`: worker không phải PID 1. `docker top` cho thấy `/bin/sh /app/entrypoint.sh` đứng trước.

**Vì sao máy dev không tái hiện.** Ctrl-C trong terminal gửi SIGINT tới **cả process group** đang ở foreground, nên Python nhận
trực tiếp; và trên máy dev Python không phải PID 1 của namespace nào nên không có luật đặc biệt của init.

## Sửa

Một từ trong `entrypoint.sh`: `exec` thay tiến trình shell bằng Python, Python thành PID 1, nhận SIGTERM và chạy handler đã có.

```sh
#!/bin/sh
set -eu

: "${REGION:=sa-east-1}"
ORDER_SYNC_QUEUE="${ORDER_SYNC_QUEUE:-olist-orders-${REGION}}"
export ORDER_SYNC_QUEUE

echo "order-sync: region=${REGION} queue=${ORDER_SYNC_QUEUE}"
exec python /app/worker.py
```

Dòng `echo "order-sync: worker đã thoát"` sau đó bị bỏ vì không bao giờ chạy được nữa (`exec` không quay lại). Dockerfile và
`worker.py` giữ nguyên. Kết quả trong test: dừng trong khoảng 0,3 giây, mã 0, có dòng `dừng sạch`.

## Các cách sửa khác và khi nào chọn

| Cách | Khi nào hợp | Lưu ý |
| --- | --- | --- |
| `exec` ở dòng cuối script | Script chỉ chuẩn bị môi trường rồi chạy một tiến trình | Ít thay đổi nhất; lệnh sau `exec` không chạy |
| Init nhỏ làm PID 1: `ENTRYPOINT ["tini", "--", "/app/entrypoint.sh"]` | App sinh tiến trình con (worker pool, gọi lệnh ngoài) cần dọn zombie | Cài `tini` (`apt-get install tini`), tini chuyển tín hiệu cho tiến trình con trực tiếp; thêm `-g` để gửi cho cả process group |
| `docker run --init` hoặc `init: true` trong compose | Không sửa được image | Docker chèn `docker-init` (tini) làm PID 1; phụ thuộc người chạy nhớ bật |
| `trap` trong shell rồi `kill` tiến trình con | Script phải làm gì đó sau khi app thoát | Dễ sai (phải `wait` lại sau `kill`); chỉ dùng khi thật cần |
| Bỏ script, `ENV` và `ENTRYPOINT ["python", "/app/worker.py"]` | Logic khởi động đơn giản | Mất phép suy ra queue từ `REGION`; ở đây phải chuyển logic đó vào code |

`STOPSIGNAL` đổi tín hiệu Docker gửi (ví dụ `SIGQUIT` cho Nginx để dừng êm), không chữa được lỗi này: `sh` làm PID 1 bỏ qua mọi
tín hiệu không có handler.

## Kiểm sau khi sửa

```bash
EX=tracks/devops/modules/06-containers/exercises/intermediate/01-incident-slow-shutdown &&
CPU=${DEVOPS_CPUSET:+--cpuset-cpus=$DEVOPS_CPUSET} &&
nice -n 15 docker build $CPU --pull=false --label devops-ex=1 -t devops-ex-order-sync:fix "$EX/starter" &&
docker run -d $CPU --label devops-ex=1 --name devops-ex-order-sync -e REGION=us-east-1 devops-ex-order-sync:fix &&
sleep 2 && time docker stop devops-ex-order-sync &&
docker inspect -f '{{.State.ExitCode}}' devops-ex-order-sync &&
docker logs devops-ex-order-sync | tail -3;
docker rm -f devops-ex-order-sync; docker image rm devops-ex-order-sync:fix
```

`time` phải dưới 1 giây, mã thoát 0. Hai lệnh dọn cuối nối bằng `;` để luôn chạy kể cả khi một bước trước lỗi.

## Bài học cho postmortem

- Ghi rõ grace period và thời gian dừng thực tế vào dashboard deploy: "mọi container dừng đúng 10 giây" là chữ ký của PID 1 bỏ
  qua SIGTERM, phát hiện được từ lần deploy đầu tiên.
- Kubernetes có cùng hành vi (`terminationGracePeriodSeconds`, mặc định 30 giây, rồi SIGKILL); chưa kể pod còn nhận traffic
  trong vài giây sau SIGTERM, nên app cần `preStop` hoặc tiếp tục phục vụ một lúc (module 11).
- Xử lý idempotent ở phía tiêu thụ hàng đợi (khoá theo `order_id`) để lần dừng không sạch tiếp theo không thành tiền.
