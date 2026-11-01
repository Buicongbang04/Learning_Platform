# Lời giải: pre-commit hook chặn secret

Hook đầy đủ ở `pre-commit` cạnh tệp này. Cài thử vào một repo của bạn:
`cp pre-commit <repo>/.git/hooks/pre-commit && chmod +x <repo>/.git/hooks/pre-commit`.

## Cách làm

1. **So với `HEAD`, hoặc empty tree khi chưa có commit.** `git diff --cached` cần một mốc; ở commit đầu tiên mốc đó là
   tree rỗng, SHA của nó tính được bằng `git hash-object -t tree /dev/null`.
2. **`--diff-filter=ACMR` và `-z`.** Bỏ tệp bị xoá (xoá `.env` là việc tốt, không được chặn), giữ tên có dấu cách.
3. **`git grep --cached` đọc index.** Đây là chỗ hook ngây thơ hay sai: `grep` trên tệp ở working tree vừa chặn nhầm thứ
   không được commit, vừa để lọt thứ đã stage rồi sửa trong working tree. `tests/fixtures/naive-pre-commit` là đúng
   kiểu hook đó, và `test_naive_hook_is_caught` chứng minh cả hai lỗi. `-I` bỏ tệp nhị phân. Lọc trước bằng chuỗi cố
   định rẻ (`-F -e AKIA ...`) rồi mới áp regex trong Bash, để hook vẫn nhanh trên commit lớn.
4. **Ranh giới token cho AWS key.** Thay mọi ký tự ngoài `[A-Z0-9]` bằng dấu cách rồi xét từng token: `AKIA` + 16 ký
   tự đúng khớp, `AKIA1234` hay chuỗi dài hơn không khớp. `set -f` để token không bị glob.
5. **URL Postgres lặp qua mọi lần xuất hiện**, mỗi lần kiểm password có phải placeholder (`$...`, `<...>`) không. Một
   dòng có cả URL mẫu lẫn URL thật vẫn bị bắt.
6. **Allowlist có kiểm soát.** `pragma: allowlist secret` nằm ngay trên dòng, nên reviewer thấy nó trong diff. Tệp
   `.secrets-allowlist` cũng nằm trong Git và đi qua review. Dòng trống bị bỏ, vì chuỗi rỗng "nằm trong" mọi dòng.
7. **Báo hết rồi mới thoát**, kèm hướng dẫn: người bị chặn cần biết sửa gì, không chỉ biết là bị chặn.

## Đánh đổi của hook tự viết

Bài này viết tay để bạn hiểu cơ chế. Trong dự án thật, dùng công cụ có sẵn qua framework [pre-commit](https://pre-commit.com/):

| Công cụ | Mạnh | Yếu |
| --- | --- | --- |
| gitleaks | Hơn 150 rule, quét cả lịch sử (`gitleaks git`), chạy được trong CI, cấu hình allowlist bằng TOML | Regex nên vẫn có false positive với token tự sinh |
| trufflehog | **Xác minh** key còn sống bằng cách gọi API của nhà cung cấp, giảm báo động giả | Gọi mạng; chậm hơn; cẩn thận khi chạy trên code không tin cậy |
| detect-secrets (Yelp) | Baseline: chấp nhận secret cũ đã biết, chỉ chặn secret mới; entropy | Baseline phải được bảo trì |
| GitHub push protection, GitLab secret push protection | Chạy trên server, không bypass bằng `--no-verify`, đối tác (AWS, Stripe) được báo để thu hồi key | Chỉ có trên nền tảng đó, chỉ với các mẫu nền tảng hỗ trợ |

Bố trí nhiều lớp: hook trên máy (nhanh, sửa trước khi push), quét trong CI cho mọi PR (không bypass được bằng
`--no-verify`), push protection trên server, và quét định kỳ toàn bộ lịch sử. Không lớp nào thay được việc **không để
secret trong code**: dùng biến môi trường, secret manager (module 12), và `.env` luôn nằm trong `.gitignore`.

## Khi secret đã lọt lên remote

Thứ tự quan trọng: **thu hồi trước, dọn sau**. Coi secret là đã lộ ngay khi nó lên remote, kể cả repo private, kể cả
đã force-push xoá: bot quét GitHub công khai trong vài phút, và các fork, clone, cache, PR ref vẫn giữ commit.

1. Thu hồi hoặc xoay key (IAM: deactivate access key; Postgres: đổi mật khẩu, kết thúc phiên cũ).
2. Kiểm tra key đã bị dùng chưa (CloudTrail, log đăng nhập DB) trong khoảng từ lúc lộ.
3. Cập nhật nơi dùng key mới (secret manager, deploy lại).
4. Dọn lịch sử nếu cần (`git filter-repo --replace-text`), phối hợp với team vì mọi người phải clone lại; với GitHub,
   liên hệ support để xoá cached view và PR ref.
5. Postmortem không đổ lỗi: vì sao lọt qua được mọi lớp, thêm lớp nào.
