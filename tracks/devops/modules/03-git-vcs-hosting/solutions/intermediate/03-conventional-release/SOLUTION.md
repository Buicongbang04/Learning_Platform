# Lời giải: phiên bản semver và changelog từ Conventional Commits

Code đầy đủ ở `release.py` cạnh tệp này.

## Cách làm

1. **Tag gốc = semver cao nhất trong `git tag --merged HEAD`.** `--merged HEAD` loại tag trên nhánh chưa merge (một
   `v3.0.0` thử nghiệm). Regex chặt `^v\d+\.\d+\.\d+$` loại pre-release và tag không phải phiên bản. So bằng tuple số,
   nên `v1.10.0` lớn hơn `v1.9.0`.
2. **`git log --no-merges --format=%H%x00%B%x00 <tag>..HEAD`.** NUL không thể có trong message, nên tách an toàn kể cả
   message nhiều dòng. Merge commit bị bỏ vì message của nó ("Merge pull request #7") không mô tả thay đổi; các commit
   thật của nhánh đã nằm trong khoảng.
3. **Regex header một dòng, footer `re.M`.** `FOOTER` dùng `^` với `re.M`, nên chỉ khớp ở đầu dòng; chữ
   `BREAKING CHANGE:` giữa câu không tính, viết thường không tính.
4. **Bump theo thứ tự ưu tiên** breaking > feat > fix/perf, với ngoại lệ major `0`: theo semver mục 4, `0.y.z` là giai
   đoạn phát triển ban đầu, API chưa ổn định. Nhiều công cụ (release-please `bump-minor-pre-major`, commitizen
   `major_version_zero`) cho breaking chỉ bump minor ở giai đoạn này, để không nhảy lên `1.0.0` ngoài ý muốn. Lên
   `1.0.0` là quyết định có chủ đích của team.
5. **Lỗi git thành exception riêng**, `main()` bắt và trả `1`: người gọi (CI) nhận exit code rõ ràng, không phải đọc
   traceback.

## Vì sao các cách "nhanh" cho tag sai

| Cách | Trả về trong test | Vì sao sai |
| --- | --- | --- |
| `git describe --tags --abbrev=0` | `v2.0.0-rc.1` | Tag gần nhất, kể cả pre-release |
| `git tag \| sort \| tail -1` | `v3.0.0` hoặc `v1.9.0` | Lấy cả tag chưa merge; sắp xếp chữ đặt `v1.9.0` sau `v1.10.0` |
| `git tag --sort=-v:refname \| head -1` | `v3.0.0` | Đúng thứ tự semver nhưng vẫn lấy tag chưa merge, và cấu hình `versionsort.suffix` ảnh hưởng tới rc |

## Trong dự án thật

Không tự viết công cụ này. So sánh:

| Công cụ | Cách làm | Hợp với |
| --- | --- | --- |
| release-please (Google) | Bot mở "release PR" cập nhật changelog và phiên bản; merge PR đó là phát hành | GitHub, monorepo nhiều package, muốn người duyệt release |
| semantic-release | Phát hành ngay trong CI sau mỗi lần merge vào `main` | Thư viện npm, phát hành liên tục không cần duyệt |
| commitizen (`cz bump`) | CLI Python, kèm hook kiểm message | Dự án Python, muốn chạy tay hoặc trong CI |
| changesets | Người viết PR thêm tệp mô tả thay đổi, không dựa vào message | Monorepo JS, message commit không đáng tin |

Ép chuẩn message: với squash merge, **tiêu đề PR** trở thành message trên `main`, nên kiểm tiêu đề PR trong CI
(action `amannn/action-semantic-pull-request` chẳng hạn) hiệu quả hơn bắt từng commit trên máy. Hook `commit-msg` với
commitlint vẫn hữu ích cho team merge từng commit.
