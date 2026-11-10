---
title: Postmortem - lộ mật khẩu Postgres và khoá age qua fork công khai
level: advanced
services: []
files:
  - path: starter/POSTMORTEM.md
    note: Khung postmortem, 8 phần
  - path: tests/test_postmortem.py
    note: Kiểm cấu trúc, thứ tự, từ khoá; không sửa
  - path: tests/fixtures/POSTMORTEM.good.md
    note: Ví dụ đạt (sự cố khác)
run:
  - uv run pytest tracks/devops/modules/12-gitops-secrets/exercises/advanced/02-secret-leak-postmortem -q -rs
---

## Mục tiêu

Viết postmortem blameless cho một lần lộ secret: dựng lại timeline từ dữ kiện rời rạc, tính đúng cửa sổ lộ, tìm các điều kiện hệ thống
cùng gây ra sự cố thay vì đổ cho một người, chứng minh thứ tự xử lý đúng (thu hồi trước, dọn lịch sử sau), và đưa ra action item có người,
có hạn.

## Đề bài

Dữ kiện người trực gom được ngày 2026-10-28 (giờ Việt Nam), chưa theo thứ tự:

- 11:05 Chủ fork đọc email cảnh báo sau cuộc họp, gửi link commit vào kênh #incident.
- 09:12 Một kỹ sư chạy `sops decrypt shop/olist-db.enc.yaml > shop/olist-db.dec.yaml` để xem vì sao api staging không kết nối được DB.
- 12:30 Log Postgres staging từ 09:41 tới 12:00: không có đăng nhập thành công nào ngoài pod của Olist Shop.
- 10:05 tới 10:12 Có 14 lần đăng nhập Postgres staging thất bại từ hai IP nước ngoài; allowlist mạng (chỉ dải IP của cluster) chặn.
- 09:40 `git add -A` rồi commit "fix db url". Commit chứa `shop/olist-db.dec.yaml` và `.keys/keys.txt` (khoá riêng age của team staging,
  đặt ở đó vì README của dự án hướng dẫn `export SOPS_AGE_KEY_FILE=$PWD/.keys/keys.txt`). `.gitignore` không có hai tệp này.
- 11:52 Khoá age staging mới: thêm recipient mới, `sops updatekeys` mọi `*.enc.yaml`, thay Secret khoá riêng của ArgoCD, restart
  repo-server, gỡ recipient cũ.
- 09:41 Push lên fork cá nhân **công khai** của repo `olist-gitops` để mở pull request vào repo công ty (quy trình quen thuộc của team).
  Push protection của tổ chức bật ở repo công ty, không ở fork cá nhân.
- 11:15 Xoay mật khẩu Postgres staging.
- 10:20 GitHub secret scanning nhận ra URI Postgres, gửi email tới chủ fork (không ai khác). Không có cảnh báo nào cho khoá age.
- 11:27 Secret mã hoá lại với mật khẩu mới, ArgoCD sync, api staging Ready.
- 09:47 Traffic log của GitHub (xem sau) cho thấy một bot quét repo công khai đã clone fork.
- 12:10 Xoá fork, nhờ GitHub Support xoá cache view của commit.
- 11:08 SRE trực tuyên bố SEV2, đóng băng deploy staging.
- 14:00 Đóng sự cố.

Thêm: production mã hoá cho recipient khác (khoá của cluster `prod` và hai người trực) và dùng mật khẩu khác; Postgres staging chỉ chứa dữ
liệu Olist công khai đã ẩn danh. Repo code có pre-commit hook chặn secret (module 03), repo `olist-gitops` thì chưa.

Điền `starter/POSTMORTEM.md`, giữ đúng tám tiêu đề `## 1.` tới `## 8.`. Test chỉ kiểm phần chấm được bằng máy; rubric trong `SOLUTION.md`
chấm nội dung.

**Cách test chấm.**

| Phần | Test kiểm |
| --- | --- |
| Khung | Đủ `## 1.` tới `## 8.`, không còn `TODO` |
| 1. Tóm tắt | Ít nhất 250 ký tự văn xuôi |
| 3. Timeline | Ít nhất 8 dòng bảng có cột đầu là giờ `HH:MM`, theo thứ tự thời gian |
| 5. Xử lý | Lần đầu nhắc xoay/rotate/thu hồi/revoke/đổi mật khẩu đứng **trước** lần đầu nhắc filter-repo/BFG/xoá lịch sử/viết lại lịch sử/force push |
| 8. Action items | Bảng ít nhất 5 dòng; mỗi dòng có người phụ trách (cột 2) và hạn dạng `YYYY-MM-DD` |
| Gạch đầu dòng | Phần 4 ít nhất 3, phần 7 ít nhất 4 |
| Từ khoá (không phân biệt hoa thường, một từ trong mỗi nhóm) | Phần 2: staging; production; phút. Phần 4: giải mã/decrypt/.dec.yaml; khoá riêng/private key/AGE-SECRET-KEY; pre-commit/push protection/hook/gitignore. Phần 5: (nhóm xoay ở trên); updatekeys/recipient/khoá age mới; (nhóm xoá lịch sử ở trên); ArgoCD. Phần 6: secret scanning/cảnh báo/alert; phút. Phần 8: pre-commit/gitleaks/push protection; định kỳ/tự động/TTL/dynamic |
| Bộ kiểm | Chạy trên ba fixture (khung, bản yếu, bản đạt của sự cố khác) để chứng minh bắt được lỗi |

## Tiêu chí đạt

- Test pass.
- Rubric trong `SOLUTION.md` đạt từ 7/10.
- Trả lời được: "Fork đã xoá rồi, sao vẫn phải xoay?", "Vì sao production không phải làm gì?", "Lần sau, sau bao nhiêu phút thì phát
  hiện được, nhờ cái gì?".

## Gợi ý

### Gợi ý 1

Cửa sổ lộ của một secret kết thúc khi nó **hết dùng được** (đã xoay hay thu hồi), không phải khi tệp biến mất khỏi Internet. Mật khẩu và
khoá age kết thúc ở hai mốc khác nhau. Thời gian phát hiện có hai con số: công cụ biết, và con người biết.

### Gợi ý 2

Blameless không có nghĩa là không có nguyên nhân: hỏi "vì sao hệ thống cho phép điều đó" cho mỗi bước (README hướng dẫn đặt khoá trong
repo, fork không có push protection, cảnh báo tới một người). Mỗi nguyên nhân nên có ít nhất một action item phòng ngừa hay phát hiện.
