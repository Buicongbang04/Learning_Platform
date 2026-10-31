# Nhật ký cài shellcheck

## Thông tin

- Phiên bản: 0.11.0
- Nền tảng: linux.x86_64
- URL tải: https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz
- Đường dẫn cài: ~/.local/bin/shellcheck

## Lệnh đã chạy

```bash
SC_VERSION=0.11.0
SC_PLATFORM=linux.x86_64
SC_FILE="shellcheck-v${SC_VERSION}.${SC_PLATFORM}.tar.xz"
SC_SHA256=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198
work="$(mktemp -d)" && cd "$work"
curl -fsSL "https://api.github.com/repos/koalaman/shellcheck/releases/tags/v${SC_VERSION}" \
  | jq -r --arg f "$SC_FILE" '.assets[] | select(.name == $f) | .digest'
curl -fLO --proto '=https' "https://github.com/koalaman/shellcheck/releases/download/v${SC_VERSION}/${SC_FILE}"
echo "${SC_SHA256}  ${SC_FILE}" > "${SC_FILE}.sha256"
sha256sum -c "${SC_FILE}.sha256"
tar -xJf "${SC_FILE}"
mkdir -p ~/.local/bin
install -m 0755 "shellcheck-v${SC_VERSION}/shellcheck" ~/.local/bin/shellcheck
which shellcheck
shellcheck --version
cp "${SC_FILE}.sha256" "$EX/starter/shellcheck.sha256"
(cd ~/.local/bin && sha256sum shellcheck) >> "$EX/starter/shellcheck.sha256"
cd ~ && rm -rf "$work"
```

`$EX` là thư mục bài tập này. Lệnh `curl ... | jq` thứ hai đọc `digest` GitHub tính cho tệp, để đối chiếu với hash đã
ghim trong hướng dẫn trước khi tải (in ra `sha256:8c3be12b...7198`).

## Kết quả kiểm checksum

```text
shellcheck-v0.11.0.linux.x86_64.tar.xz: OK
```

## Kết quả xác nhận

```text
$ which shellcheck
/home/learner/.local/bin/shellcheck
$ shellcheck --version
ShellCheck - shell script analysis tool
version: 0.11.0
license: GNU General Public License, version 3
website: https://www.shellcheck.net
```

## Cách gỡ

```bash
rm -f ~/.local/bin/shellcheck
hash -r
command -v shellcheck || echo "đã gỡ"
```
