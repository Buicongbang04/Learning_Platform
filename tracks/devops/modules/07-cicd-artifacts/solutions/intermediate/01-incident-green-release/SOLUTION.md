# Lời giải: pipeline release xanh dù test đỏ

## Nguyên nhân

Lần chỉnh sửa tuần trước đổi bước **Test** từ

```yaml
run: '"$RUNNER_TEMP/venv/bin/python" -m pytest -q tests'
```

thành

```yaml
run: |
  "$RUNNER_TEMP/venv/bin/python" -m pytest -q tests 2>&1 | tee pytest-report.txt
```

để có tệp `pytest-report.txt` cho bước tóm tắt. Trong shell, mã thoát của một pipeline (`a | b`) là mã thoát của **lệnh cuối**,
tức `tee`, và `tee` ghi tệp thành công nên trả 0. pytest trả 1 nhưng con số đó bị bỏ.

Runner có bắt lỗi không? Khi bước không khai báo `shell:`, GitHub (và act, làm theo) chạy script bằng `bash -e {0}`: có `errexit`
nhưng **không** có `pipefail`. Chỉ khi khai báo tường minh `shell: bash`, runner mới gọi `bash --noprofile --norc -eo pipefail
{0}`. Log của act cho thấy rõ: bước không khai báo chạy `cmd=[bash -e /var/run/act/workflow/5]`, bước có `shell: bash` chạy
`cmd=[bash --noprofile --norc -e -o pipefail ...]`.

Chuỗi sự kiện: pytest in `1 failed` và thoát 1, `tee` thoát 0, cả dòng thoát 0, bước ✅, job `test` ✅, `needs: test` thoả, job
`publish` đẩy image, hệ thống deploy kéo nó lên staging. `continue-on-error: false` và `needs: test` đều đúng; chúng chỉ làm việc
với kết quả mà runner nhìn thấy.

**Vì sao không ai thấy ở lần chỉnh sửa tuần trước.** PR thêm `tee` có mọi test xanh, nên pipeline xanh là đúng. Lỗi chỉ lộ ra ở
commit đầu tiên có test đỏ sau đó, đúng lúc pipeline cần làm việc của nó nhất. Máy dev không tái hiện vì dev chạy pytest trực
tiếp, không qua `tee`.

## Sửa

Một khối ở cấp workflow, áp cho mọi bước `run:`:

```yaml
defaults:
  run:
    shell: bash
```

Mọi bước giờ chạy với `-eo pipefail`; dòng `pytest ... | tee ...` thoát 1 khi pytest thoát 1, bước đỏ, job `test` đỏ, `publish`
không chạy. Bước tóm tắt có `if: always()` nên vẫn chạy và vẫn đọc được `pytest-report.txt` (tee đã ghi xong trước khi pipeline
trả mã). `continue-on-error: false` được bỏ vì đó là mặc định và chỉ gây hiểu nhầm rằng lỗi đã được xử lý.

## Các cách sửa khác và khi nào chọn

| Cách | Khi nào hợp | Lưu ý |
| --- | --- | --- |
| `defaults: run: shell: bash` cấp workflow (lời giải) | Mặc định cho mọi workflow mới | Bảo vệ cả bước viết sau này; đưa vào template workflow của tổ chức |
| `shell: bash` trên riêng bước đó | Chỉ muốn đổi một bước | Bước khác viết sau vẫn có thể dính |
| `set -o pipefail` đầu script | Script cũng chạy ngoài GitHub (Makefile, script local) | Dễ quên ở bước mới |
| `pytest --junitxml=report.xml` hoặc `pytest ... > pytest-report.txt; status=$?` rồi `exit $status` | Cần báo cáo có cấu trúc | Bỏ hẳn pipe; JUnit XML đọc được bởi action hiển thị test |
| `PIPESTATUS[0]` | Cần mã thoát của từng lệnh trong pipe | Chỉ có trong bash; khó đọc |

Không sửa bằng cách bỏ `tee` và bước tóm tắt: báo cáo test là thứ team cần, và lần sau ai đó sẽ thêm lại đúng dòng đó.

## Kiểm sau khi sửa

```bash
EX=tracks/devops/modules/07-cicd-artifacts/exercises/intermediate/01-incident-green-release &&
actionlint "$EX/starter/.github/workflows/release.yml" &&
nice -n 15 uv run pytest "$EX" -q
```

Trên máy viết bài: `6 passed` trong khoảng 60 giây. Lưu ý `actionlint` kèm shellcheck **không** bắt lỗi này ở bản lúc sự cố:
thiếu `pipefail` không phải lỗi cú pháp, nên chỉ test hành vi (cài một test đỏ rồi đòi pipeline đỏ) mới bắt được.

## Bài học cho postmortem

- **Test chính pipeline**: một job định kỳ (hoặc một PR mẫu) cố ý thêm test đỏ và đòi pipeline đỏ, đúng như harness của bài này.
  Pipeline là code chạy production; nó cần test như code khác.
- **Mặc định an toàn ở cấp tổ chức**: template workflow có sẵn `defaults: run: shell: bash`, ruleset hay linter (zizmor, review
  của platform team qua CODEOWNERS) cho `.github/workflows/`.
- **Deploy không chỉ dựa vào tín hiệu của CI**: staging nên có smoke test sau deploy và tự quay lại khi đỏ; lỗi này sống 40 phút
  vì không có gate nào sau deploy.
- **Đọc summary**: summary đã ghi `1 failed`. Một bước nhỏ so summary với trạng thái job (có `failed` mà job xanh thì đỏ) là lưới
  thứ hai rẻ.
