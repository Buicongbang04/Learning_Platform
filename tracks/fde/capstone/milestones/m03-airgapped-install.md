# M03: Cài ở khách air-gapped, kiểm toàn vẹn trước tiên

## Mục tiêu

Ngày cài. Quy định của phòng pháp chế: phần mềm vào vùng trong chỉ qua cổng chuyển tệp đã quét virus; mọi image chạy
trong vùng trong phải đến từ registry nội bộ `10.0.2.101:5000`; máy staging không ra internet, không DNS. Bundle
`SITE=lawfirm-staging` của M02 đi qua cổng, tới `/home/fde/bundle` trên máy staging. Bạn có một buổi.

Hai điều quyết định buổi đó:

- **Toàn vẹn trước mọi thứ.** Bundle 1,1 GB qua cổng chuyển tệp có thể hỏng; cũng có thể không phải là thứ team product
  phát hành. Installer phải phát hiện cả hai **trước khi** nạp image, tạo container, sửa cấu hình Docker hay restart bất
  cứ gì, và nói rõ tệp nào sai để IT khách biết phải chép lại cái gì. Cài một bundle hỏng là mất lòng tin của IT.
- **Máy khách không phải máy lab.** Installer đã chạy êm trên `lab-open` ở M02 có thể không chạy ở đây. Báo cáo M01
  là danh sách những gì khác; những gì báo cáo chưa thấy, bạn sẽ thấy ở lần cài đầu. Đọc lỗi, sửa installer (không sửa
  tay trên máy khách rồi quên ghi lại), chạy lại.

Dựa trên [module 03](../../modules/03-airgapped-proxy/README.md) (registry nội bộ, chuyển bundle qua "USB", kiểm toàn vẹn)
và M01–M02 của bạn.

## Việc cần làm

1. Dựng bundle cho site của khách và tự diễn tập buổi cài trên máy giống staging:

   ```python
   with fdekit.customer_site("lawfirm-staging", memory_mb=5120, forwards=(18080,)) as s:
       s.vm.put(Path("<bundle>"), "/home/fde/bundle")
       # make install SSH="<shlex.join(s.vm.ssh_command())>" REMOTE_BUNDLE=/home/fde/bundle
       # registry nhìn từ máy bạn: http://{s.registry_host}/v2/_catalog
   ```

2. Installer kiểm toàn vẹn hai lớp, theo thứ tự, trước mọi thay đổi trên máy:
   - mọi tệp của bundle theo `SHA256SUMS` (bắt chép hỏng), báo **tên tệp** không khớp;
   - mọi tệp **bên trong** `quillo-1.0.0.tar` theo `manifest.json` của bản phát hành (bắt bundle bị sửa mà
     `SHA256SUMS` vẫn "khớp" vì bị viết lại cùng), báo **đường dẫn** của tệp sai theo `manifest.json` (vd.
     `images/pgvector.tar`).
3. Sau khi qua kiểm tra: mọi image dịch vụ chạy phải lấy từ registry nội bộ của khách (đẩy từ bundle lên đó), project
   compose `quillo` đủ năm dịch vụ, API gọi được từ mạng của luật sư ở cổng 18080 (test gọi qua cổng forward của VM).
4. `verify.sh` của M02 thêm: khi site có registry nội bộ, mọi dịch vụ phải chạy image từ registry đó; dịch vụ nào dừng
   thì `verify` thoát khác `0`.
5. Ghi vào `reports/` (hoặc README) những gì khác giữa lab và máy khách mà bạn chỉ thấy khi cài, và installer xử lý
   chúng ra sao; cập nhật báo cáo M01 nếu nó bỏ sót. Phần này không chấm tự động nhưng là thứ người phỏng vấn sẽ hỏi.

## Kết quả nộp

Installer, `verify.sh`, cấu hình site `lawfirm-staging` đã sửa theo những gì gặp ở khách; ghi chú khác biệt
lab ↔ khách.

```bash
uv run pytest tracks/fde/capstone -k m03 -q      # ~2 phút, một máy lawfirm-staging 5120 MB + registry nội bộ
```

## Tiêu chí đạt

Hai test dùng chung một máy `customer_site("lawfirm-staging", memory_mb=5120, forwards=(18080,))`; test dựng bundle
`SITE=lawfirm-staging` trên máy bạn như M02 rồi chép cả thư mục vào `/home/fde/bundle`. `make install`/`make verify`
chạy như M02 (`SSH=<lệnh ssh của test> REMOTE_BUNDLE=/home/fde/bundle`, sandbox, `install` ≤250 s, `verify` ≤60 s).

- [ ] `test_m03_rejects_tampered_bundle`:
  - test đổi **một byte** ở giữa một tệp nằm trong `quillo-1.0.0.tar` (bản trên máy staging): `make install` thoát
    khác `0`, output (stdout + stderr) có chữ `quillo-1.0.0.tar`;
  - giữ byte hỏng, viết lại dòng của `quillo-1.0.0.tar` trong `SHA256SUMS` cho khớp tệp đã hỏng: `make install` thoát
    khác `0`, output có đường dẫn của tệp bị sửa theo `manifest.json` (vd. `models/<tên>.gguf`);
  - sau mỗi lần: registry nội bộ không có repository nào, máy không có image hay container nào, `/etc/docker/daemon.json`
    giữ nguyên (cả khi chưa tồn tại), Docker không bị restart;
  - test trả byte và `SHA256SUMS` về như cũ khi xong.
- [ ] `test_m03_airgapped_install`:
  - `make install` thoát `0`;
  - `/healthz` qua cổng 18080 forward ra máy bạn trả 200 với `version` `1.0.0`;
  - project compose `quillo` có đủ `db`, `llm`, `embed`, `api`, `worker` đang chạy, image của mỗi dịch vụ bắt đầu bằng
    `10.0.2.101:5000/` và tag đó có trong registry nội bộ (hỏi qua API registry);
  - `make verify` thoát `0`; test dừng container `api` rồi chạy lại `make verify`: thoát khác `0`.
- [ ] Thiếu KVM, golden image, bản phát hành hay binary compose đã ghim thì test skip kèm lệnh cần chạy.
