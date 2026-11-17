# Lời giải: chính sách tag image bất biến

Script đầy đủ ở `ci/image-tags.sh` cạnh tệp này. Phần dưới giải thích chính sách mà script mã hoá.

## Vì sao từng quy tắc

| Quy tắc | Lý do |
| --- | --- |
| Luôn có `sha-<12>` | Một định danh duy nhất cho mọi image, nối thẳng về commit. Manifest deploy dùng tag này kèm digest |
| `main-<thời điểm>-<sha>` thay vì `main` | Tag `main` dời mỗi lần merge: hai node kéo cách nhau một phút chạy hai bản khác nhau, rollback không biết quay về đâu. Thêm thời điểm commit làm tag **sắp xếp được theo thứ tự chữ** mà vẫn bất biến: Flux image automation (`ImagePolicy` với `filterTags` và `policy.alphabetical`) và Argo CD Image Updater chọn được "bản mới nhất của main" mà không cần tag dời |
| Thời điểm là committer date theo UTC | Build lại cùng commit (CI chạy lại, runner khác múi giờ) ra cùng tag. Giờ chạy script thì mỗi lần một khác |
| `br-<slug>-<sha>` | Tên nhánh có `/`, chữ hoa, `_`, có thể dài hơn 128 ký tự: không hợp lệ làm tag Docker. Slug cắt 40 ký tự để cả tag dưới 63 ký tự |
| Tag phát hành `1.4.2` từ `v1.4.2` | Người đọc và công cụ (Renovate, Helm chart) hiểu SemVer. Không in `1.4`, `1`, `latest`: tag dời là thứ chính sách này cấm. Nhóm nào cần "bản 1.4 mới nhất" thì để Renovate cập nhật digest |
| Tag phải trỏ HEAD | Tránh gắn nhãn `1.4.2` cho image build từ commit khác (ví dụ workflow chạy trên nhánh sau khi tag đã được tạo ở commit trước) |
| Từ chối tree bẩn | Image phải tái lập được từ đúng một commit. Tệp sinh ra trong CI (`.env` tạm, artifact cũ) lọt vào build context thì tag `sha-...` nói dối |
| Từ chối thì stdout rỗng | Bước CI kiểu `tags=$(ci/image-tags.sh)` không bao giờ nhận được một tag nửa vời; mã thoát khác nhau cho từng lý do để log rõ |

## Promotion là retag, không build lại

`ci/promote.sh` cạnh tệp này làm promotion ngay trên registry: `GET` manifest của tag `sha-...` (kèm header `Accept` cho cả OCI
index lẫn Docker manifest, vì `docker push` từ image store containerd đẩy OCI index), rồi `PUT` **đúng những byte đó** với đúng
`Content-Type` dưới tag mới. Digest là SHA-256 của chính những byte này, nên tag mới trỏ đúng digest cũ: image đã qua test, quét và
ký ở staging chính là image lên production, từng byte. Build lại "cùng commit" ở bước phát hành tạo ra một image khác (image nền
vừa được build lại, gói mới trên PyPI, timestamp trong layer) chưa ai kiểm. Không cần pull về máy, nên promote vài chục image
mất vài giây.

Hai quy tắc làm script an toàn để chạy lại:

- Tag đích đã trỏ cùng digest: thành công mà không làm gì (pipeline chạy lại sau lỗi mạng không đỏ oan).
- Tag đích đã trỏ digest khác: thoát 5. Tag phát hành không bao giờ bị dời; muốn sửa thì phát hành `1.5.1`.

Công cụ làm sẵn việc này: `docker buildx imagetools create --tag reg/olist-api:1.5.0 reg/olist-api@sha256:...`, `crane tag`,
`skopeo copy`, `oras tag`. Registry nên bật **tag immutability** cho tag phát hành (ECR, Harbor, Google Artifact Registry, JFrog có
tuỳ chọn này) để quy tắc thứ hai được thực thi ở phía server, không chỉ dựa vào script. Registry `registry:2` không có tuỳ chọn đó,
nên kiểm "đã trỏ digest khác" phải nằm trong script; giữa lúc kiểm và lúc PUT vẫn có cửa sổ tranh chấp nhỏ mà chỉ server mới đóng
được.

## Dùng trong workflow

```yaml
      - name: Tính tag
        id: meta
        run: |
          tags="$(ci/image-tags.sh)"
          {
            echo "tags<<EOF"
            sed 's#^#ghcr.io/olist/olist-api:#' <<< "$tags"
            echo "EOF"
          } >> "$GITHUB_OUTPUT"
```

Rồi `tags: ${{ steps.meta.outputs.tags }}` cho `docker/build-push-action`. `docker/metadata-action` làm việc tương tự với cấu hình
YAML; script riêng có lợi là chạy được trong mọi CI (GitLab, Jenkins) và test được bằng repo git tạm như bài này.

## Kiểm sau khi viết

```bash
EX=tracks/devops/modules/07-cicd-artifacts/exercises/intermediate/02-immutable-image-tags &&
shellcheck "$EX/starter/ci/image-tags.sh" "$EX/starter/ci/promote.sh" &&
nice -n 15 uv run pytest "$EX" -q
```

Trên máy viết bài: `21 passed` trong khoảng 8 giây (registry local đã bật).
