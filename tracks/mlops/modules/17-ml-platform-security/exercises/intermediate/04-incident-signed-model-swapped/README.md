---
title: "Sự cố: model đã ký vẫn bị thay mà cổng không chặn"
level: intermediate
services: []
files:
  - path: starter/release.py
    note: Code đưa model về node đang chạy ở production, tìm và sửa
  - path: tests/fixtures/release.original.py
    note: Bản gốc, test hồi quy dùng
  - path: tests/test_release.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/intermediate/04-incident-signed-model-swapped -q
---

## Mục tiêu

Điều tra một sự cố chuỗi cung ứng model: mọi bản phát hành đều được ký, cổng deploy đều báo chữ ký hợp lệ, vậy mà một node đang phục vụ
model khác với model đã ký. Tìm vì sao cổng không chặn, sửa, và đề xuất thay đổi để loại cả nhóm lỗi này.

## Đề bài

Thứ Năm, 10:40. Đội pricing báo:

- Model `pricing-tip-amount` version 7 cho dự đoán tiền tip lệch rõ trên **một phần** lưu lượng, khoảng 1/6 số yêu cầu. Lưu lượng đi qua
  sáu node; khi gọi thẳng từng node, chỉ `node-4` trả kết quả lệch. Năm node còn lại khớp với lần chạy lại offline từ bản trong registry.
- Log deploy của `node-4` lúc 09:12 hôm nay: `release pricing-tip-amount/7 signature OK, key=release-2026`. Năm node kia có cùng dòng log.
  Khoá ký không bị lộ, không ai thay khoá, chữ ký trong registry vẫn verify được với bản trong registry.
- Audit log của registry: không ai ghi vào `pricing-tip-amount/7` kể từ lúc pipeline huấn luyện đẩy lên hôm thứ Hai.
- Bảng băm sha256 của `model.safetensors` mà `node-4` đang nạp khác bản trong registry. Năm node kia giống registry.
- Đội hạ tầng xác nhận có người đã đăng nhập vào `node-4` tuần trước để "thử một bản sửa nóng", và cho biết `node-4` đã từng chạy version
  7 trong một đợt canary hôm thứ Ba trước khi rollback rồi deploy lại hôm nay.

`starter/release.py` là code mà agent trên mỗi node gọi khi deploy: `stage(bundle, signature, public_key, cache_root)` lấy bản phát hành
từ registry (`bundle` là thư mục model, `signature` là chữ ký model-signing của nó) về đĩa của node dưới `cache_root`, rồi serving nạp
model từ thư mục mà hàm trả về.

Sửa `starter/release.py`. Giữ nguyên chữ ký hàm `stage` và lớp `Rejected`. Luật mà test kiểm:

- Thư mục `stage` trả về nằm dưới `cache_root` (serving đọc từ đĩa node, không đọc thẳng registry), khác thư mục `bundle`, và **nội dung
  của nó verify được** với `signature` và `public_key`, giống từng byte với bản đã ký. Luật này phải đúng ở **mọi** lần gọi, không chỉ lần
  đầu.
- Gọi lại khi thư mục trên node vẫn nguyên vẹn thì dùng lại, không chép lại (test so inode và mtime của tệp trọng số).
- Thư mục trên node bị đổi (sửa byte, thêm hay xoá tệp) mà bản trong registry vẫn đúng thì deploy vẫn thành công: `stage` trả một thư mục
  dưới `cache_root` có nội dung đúng bản đã ký, không `raise`.
- Bản trong registry không verify được (sửa, thêm, xoá tệp; chữ ký thiếu, rỗng, hỏng; ký bằng khoá khác) thì `raise Rejected`, không ném
  lỗi loại khác, và không để lại thư mục nào (kể cả thư mục tạm) dưới `cache_root` khi trước đó trống.
- Node đã có bản cũ mà registry bị sửa thì hoặc `Rejected`, hoặc trả thư mục verify được; không bao giờ trả nội dung chưa verify.
- Test hồi quy chứng minh bản gốc (`tests/fixtures/release.original.py`) tái hiện đúng triệu chứng trên.

Test chỉ dùng safetensors và JSON, không có pickle. Ghi lại một câu nguyên nhân gốc và một thay đổi để loại sự cố cùng loại không lặp lại;
đối chiếu với `SOLUTION.md` sau khi xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/17-ml-platform-security/exercises/intermediate/04-incident-signed-model-swapped -q` pass.
- Bạn giải thích được vì sao log `signature OK` là thật mà model đang chạy vẫn sai.
- Bạn nêu được ít nhất hai lớp bảo vệ ngoài sửa code này (ở mức node và ở mức nền tảng) để một người có quyền vào node không thể âm
  thầm thay model.

## Gợi ý

### Gợi ý 1

Liệt kê mọi bản sao của model trong luồng từ registry tới tiến trình serving. Hàm verify đang chạy trên bản nào, serving nạp bản nào?

### Gợi ý 2

Thử gọi `stage` hai lần với cùng `cache_root`, và giữa hai lần đó sửa một byte trong thư mục mà lần đầu trả về.
