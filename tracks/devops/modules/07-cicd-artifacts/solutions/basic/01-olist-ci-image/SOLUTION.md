# Lời giải: workflow CI cho Olist Shop

Workflow đầy đủ nằm ở `.github/workflows/ci.yml` cạnh tệp này. Phần dưới giải thích từng quyết định và vì sao harness làm phần
build, push thay cho workflow khi chấm.

## Từng quyết định

| Chỗ | Viết | Vì sao |
| --- | --- | --- |
| Trigger | `push: branches: [main]` cộng `pull_request` | Mọi PR được kiểm trước khi merge; chỉ code đã vào `main` mới được đẩy image. Không trigger `push` trên mọi nhánh: mỗi nhánh tính năng đẩy một image là rác trên registry và tốn phút runner |
| Quyền | `permissions: contents: read` ở cấp workflow, job `image` nâng lên `packages: write` | `GITHUB_TOKEN` mặc định của repo cũ có quyền ghi gần như mọi thứ. Đặt quyền tối thiểu ở cấp workflow rồi chỉ nâng cho đúng job cần; job `test` chạy code của PR không bao giờ cầm token ghi được package |
| `concurrency` | `group: ci-${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true` | Push liên tiếp lên một PR huỷ lần chạy cũ; nhánh khác nhau không chặn nhau |
| `timeout-minutes` | 15 và 20 | Mặc định là 360 phút: một test treo đốt 6 giờ runner |
| `needs: test` | Job `image` chờ `test` | Không có `needs`, hai job chạy song song và image của code đỏ vẫn được đẩy |
| Tag | `sha-${GITHUB_SHA::12}` | Bất biến: cùng tag luôn là cùng commit, rollback biết quay về đâu. 12 ký tự đủ tránh trùng ở quy mô repo này (7 ký tự bắt đầu trùng ở repo hàng trăm nghìn commit). Tag theo ngày giờ hay `run_number` không truy về commit được và đổi khi chạy lại |
| `outputs.tag` | Từ `steps.meta.outputs.tag` | Job deploy sau này (capstone) đọc `needs.image.outputs.tag` thay vì tự tính lại |
| Login | `docker/login-action`, `ghcr.io`, `secrets.GITHUB_TOKEN` | Token ngắn hạn, tự hết hạn khi job xong, phạm vi theo `permissions`; không cần PAT sống lâu |
| Build | `docker/build-push-action`, `build-args: APP_VERSION=<tag>`, nhãn `org.opencontainers.image.revision` | `/healthz` trả đúng tag, nhãn OCI trỏ về commit: nhìn container đang chạy là biết từ commit nào |
| `push` | `${{ github.event_name == 'push' }}` | PR vẫn build (bắt Dockerfile hỏng sớm) nhưng không đẩy image của code chưa review. Test chỉ nhận đúng dạng này hoặc `!= 'pull_request'`: một biểu thức "có nhắc tới event_name" như `!= 'push'` làm ngược lại |
| Guard | `if: ${{ !env.ACT }}` | act đặt biến `ACT`, nên hai bước Docker chỉ chạy trên GitHub |

Các action được ghim theo commit SHA (`actions/checkout@3d3c42e...` là v7.0.1). Basic 02 giải thích vì sao; bài này không chấm
điểm đó nhưng lời giải làm đúng từ đầu.

## Vì sao harness build và push thay workflow

Job của act chạy trong container không có socket Docker (testkit truyền `--container-daemon-socket -`). Cho job socket Docker
là cho nó quyền root trên máy bạn (module 06, mục 3), và một workflow lỗi có thể xoá container của bạn. Docker-in-Docker cần
`--privileged`, cũng là quyền root. Vì vậy:

- Phần logic có giá trị chấm (test, tính tag, thứ tự job) chạy thật dưới act.
- Phần chỉ là gọi Docker (login, build, push) chạy thật trên GitHub, kiểm tĩnh trên máy, và harness làm lại bằng `DockerLab`
  với đúng tham số workflow khai báo (`context: .`, `APP_VERSION=<tag>`, tag lấy từ output của workflow).

Đó cũng là cách nhiều team thử pipeline: tách logic ra bước `run:` hay script chạy được ở mọi nơi, giữ phần gắn với nền tảng
(action của vendor) mỏng.

## Kiểm sau khi viết

```bash
EX=tracks/devops/modules/07-cicd-artifacts/exercises/basic/01-olist-ci-image &&
actionlint "$EX/starter/.github/workflows/ci.yml" &&
nice -n 15 uv run pytest "$EX" -q
```

`actionlint` không kèm cờ thì chạy cả shellcheck trên từng bước `run:` (nếu đã cài từ module 01): lời giải sạch cả hai. Kết quả
trên máy viết bài: `16 passed` trong khoảng 60 giây (hai lần act khoảng 15 giây mỗi lần, build image có cache).

## Lỗi hay gặp

- Quên `id:` ở bước tính tag: `steps.meta.outputs.tag` rỗng, job `image` xanh mà không có tag.
- Dùng `${{ github.sha }}` trong `run:` rồi cắt bằng `cut -c1-12`: đúng, nhưng `${GITHUB_SHA::12}` gọn hơn và không chèn biểu thức
  vào script (Basic 02).
- Đặt `permissions: packages: write` ở cấp workflow: job `test` chạy code của PR cũng cầm quyền đó.
- Viết `push: true`: mọi PR (kể cả từ fork khi được phép) đẩy image lên registry.
