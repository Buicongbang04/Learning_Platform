# Lời giải: p99 vọt ở những request đầu sau deploy

## Nguyên nhân

Bảng zone (`build_zone_table`, nạp từ kho và tốn ~0.5 giây) được dựng **lười**, ở lần đầu `zone_table()` được gọi, tức là bên trong request `/predict` đầu tiên. `startup` chỉ đặt `ready=True`, nên orchestrator thấy pod `Ready` ngay và gửi traffic; request nào tới trước phải chờ dựng bảng (và các request đến cùng lúc xếp hàng sau khoá `_LOCK`). Sau đó bảng nằm trong bộ nhớ nên mọi thứ bình thường. Đó là lý do:

- p50 không đổi: chỉ vài request trong cửa sổ đầu bị ảnh hưởng, nhưng chúng đúng là đuôi, nên p99 vọt;
- không có lỗi nào: request chậm vẫn trả 200;
- mã nguồn và model không đổi, nhưng **mỗi lần khởi động** đều lặp lại, mà rolling deploy 6 replica khởi động liên tục;
- máy dev tái hiện: request đầu chậm, các request sau nhanh.

## Cách chẩn đoán

1. Đo thay vì đoán: 30 request liên tiếp ngay sau khi lên, in độ trễ từng lần. Chuỗi `[505, 3, 3, 2, ...]` nói rằng chỉ có chi phí **một lần** ở request đầu, không phải nghẽn liên tục.
2. Hỏi chi phí một lần đó nằm ở đâu: đặt `time.perf_counter()` quanh các bước trong `predict`; hoặc py-spy dump lúc request đầu. Nó chỉ vào `zone_table()`.
3. Đọc `zone_table()`: kiểu "tạo khi cần" (`if _ZONES is None`) chạy trong đường của request.

## Cách sửa

Dựng bảng trong `startup`, trước khi đặt `ready=True`:

```python
@app.on_event("startup")
def startup() -> None:
    zone_table()
    state["ready"] = True
```

`/readyz` vì thế chỉ 200 sau khi bảng đã có, và `build_zone_table` vẫn chạy đúng một lần. Thời gian khởi động tăng ~0.5 giây, nhưng chi phí đó chuyển từ người dùng sang quá trình khởi động nơi không ai chờ.

## Bài học

- **`Ready` phải có nghĩa "request đầu tiên sẽ nhanh như request thứ trăm".** Mọi chi phí một lần phải trả trước khi báo ready, bằng cách dựng sẵn hoặc bằng warmup đi qua đúng đường mã của request thật. Warmup bằng một lời gọi model đơn lẻ không chạm vào những thứ nằm ngoài model.
- **Test hồi quy là chính phép đo**: độ trễ của N request đầu sau `ready`, không chỉ trung bình.
- Bảng và cache nằm ở đầu vào của model (feature, tra cứu) dễ bị bỏ quên hơn bản thân model.
- Dashboard nên tách độ trễ theo "thời gian kể từ khi tiến trình khởi động" để bắt loại sự cố này; p99 gộp cả ngày sẽ làm nó mất tăm.

## Rubric tự chấm

| Tiêu chí | Đạt khi |
| --- | --- |
| Tìm đúng nguyên nhân bằng phép đo | Chuỗi độ trễ theo thứ tự request, dòng mã chịu trách nhiệm |
| Sửa tối thiểu đúng chỗ | Dựng trước ready, vẫn một lần, `readyz` 503 trước đó |
| Không gian lận | Không xoá hay thay `build_zone_table` bằng hằng số |
