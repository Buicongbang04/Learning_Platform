import json
import shlex
import tarfile
import time
import urllib.request
from contextlib import ExitStack
from pathlib import Path

import pytest

import fdekit
from capstonekit import (
    INSTALL_TIMEOUT,
    MEMORY_MB,
    PORT,
    RELEASE_NAME,
    REMOTE_BUNDLE,
    SERVICES,
    VERIFY_TIMEOUT,
    VERSION,
    big_tmp,
    build_bundle,
    healthz,
    make_on,
    need_files,
    output,
    quillo_containers,
    release,
    vm_sh,
)

DELIVERY = ("Makefile", "delivery/fetch_release.sh", "delivery/install.sh", "delivery/verify.sh")
REMOTE_TAR = f"{REMOTE_BUNDLE}/{RELEASE_NAME}"
TAMPER_TIMEOUT = 120
STATE = ("docker images -q | sort; echo ---; docker ps -aq | sort; echo ---; "
         "sudo -n sha256sum /etc/docker/daemon.json 2>/dev/null || echo 'no daemon.json'; echo ---; "
         "systemctl show docker -p ActiveEnterTimestamp")


class Staging:
    """Một máy lawfirm-staging dùng chung cho cả milestone, dựng lần đầu khi test cần (lỗi dựng là FAIL của test, không
    phải ERROR của fixture): bundle SITE=lawfirm-staging dựng trên máy bạn rồi chép vào /home/fde/bundle."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.stack = ExitStack()
        self.site: fdekit.Site | None = None
        self.offset = 0
        self.member = ""
        self.timings: dict[str, float] = {}

    def ready(self) -> "Staging":
        if self.site is not None:
            return self
        need_files(self.repo, *DELIVERY)
        release()
        started = time.monotonic()
        bundle = Path(self.stack.enter_context(big_tmp())) / "bundle"
        build_bundle(self.repo, "lawfirm-staging", bundle)
        self.offset, self.member = largest_member(bundle / RELEASE_NAME)
        self.timings["bundle"] = time.monotonic() - started
        site = self.stack.enter_context(fdekit.customer_site("lawfirm-staging", memory_mb=MEMORY_MB, forwards=(PORT,)))
        site.vm.put(bundle, REMOTE_BUNDLE)
        self.timings["boot+copy"] = time.monotonic() - started - self.timings["bundle"]
        self.site = site
        return self


def largest_member(tar_path: Path) -> tuple[int, str]:
    with tarfile.open(tar_path) as tar:
        member = max(tar.getmembers(), key=lambda m: m.size)
        return member.offset_data + member.size // 2, member.name.split("/", 1)[1]


@pytest.fixture(scope="module")
def staging(capstone):
    holder = Staging(capstone)
    with holder.stack:
        yield holder
    print("thời gian (s): " + ", ".join(f"{k} {v:.1f}" for k, v in holder.timings.items()))


def flip(m, offset: int) -> None:
    code = (f"f=open({REMOTE_TAR!r},'r+b'); f.seek({offset}); b=f.read(1); f.seek({offset}); "
            "f.write(bytes([b[0]^0xff])); f.close()")
    assert vm_sh(m, f"python3 -c {shlex.quote(code)}", 30).returncode == 0, "Test không sửa được byte trong bundle"


def forge_sums(m) -> None:
    code = ("import hashlib, re; t = " + repr(RELEASE_NAME) + "; d = hashlib.sha256(); "
            f"f = open({REMOTE_TAR!r}, 'rb'); [d.update(c) for c in iter(lambda: f.read(1 << 20), b'')]; "
            f"p = {REMOTE_BUNDLE + '/SHA256SUMS'!r}; s = open(p).read(); "
            "n = re.sub(r'^[0-9a-f]{64}( [ *]\\.?/?)' + re.escape(t) + '$', lambda x: d.hexdigest() + x.group(1) + t, "
            "s, flags=re.M); assert n != s, 'SHA256SUMS không có dòng cho ' + t; open(p, 'w').write(n)")
    forged = vm_sh(m, f"cp {REMOTE_BUNDLE}/SHA256SUMS /home/fde/SHA256SUMS.orig && python3 -c {shlex.quote(code)}", 60)
    assert forged.returncode == 0, f"Test không viết lại được SHA256SUMS:\n{forged.stderr[-800:]}"


def registry(site, path: str) -> dict:
    with urllib.request.urlopen(f"http://{site.registry_host}{path}", timeout=10) as response:
        return json.load(response)


def rejected(st: Staging, case: str, must_name: str, before: str) -> None:
    started = time.monotonic()
    result = make_on(st.repo, st.site.vm, "install", TAMPER_TIMEOUT)
    st.timings[case] = time.monotonic() - started
    assert result.returncode != 0, f"{case}: make install vẫn thoát 0"
    text = result.stdout + result.stderr
    assert must_name in text, f"{case}: thông báo lỗi phải nêu tệp sai '{must_name}'\n{output(result)}"
    assert not registry(st.site, "/v2/_catalog").get("repositories"), f"{case}: vẫn đẩy image lên registry nội bộ"
    after = vm_sh(st.site.vm, STATE, 30).stdout
    assert after == before, (f"{case}: installer đã đụng vào máy (image, container, daemon.json hoặc restart Docker) "
                             f"trước khi kiểm xong toàn vẹn\ntrước:\n{before}\nsau:\n{after}")


def test_m03_rejects_tampered_bundle(capstone, staging):
    need_files(capstone, *DELIVERY)
    staging.ready()
    m = staging.site.vm
    before = vm_sh(m, STATE, 30).stdout
    flip(m, staging.offset)
    try:
        rejected(staging, "tệp bundle hỏng một byte", RELEASE_NAME, before)
        forge_sums(m)
        rejected(staging, "bundle bị sửa và SHA256SUMS viết lại cho khớp", staging.member, before)
    finally:
        flip(m, staging.offset)
        vm_sh(m, f"[ ! -f /home/fde/SHA256SUMS.orig ] || cp /home/fde/SHA256SUMS.orig {REMOTE_BUNDLE}/SHA256SUMS", 30)


def test_m03_airgapped_install(capstone, staging):
    need_files(capstone, *DELIVERY)
    s, m = staging.ready().site, staging.site.vm
    started = time.monotonic()
    done = make_on(capstone, m, "install", INSTALL_TIMEOUT)
    staging.timings["install"] = time.monotonic() - started
    assert done.returncode == 0, f"make install thoát mã {done.returncode}\n{output(done)}"
    body = healthz(f"http://127.0.0.1:{m.port(PORT)}/healthz")
    assert body.get("version") == VERSION, f"/healthz trả {body}, cần version {VERSION}"

    running = quillo_containers(m)
    assert SERVICES <= set(running), f"Project compose 'quillo' thiếu dịch vụ: {sorted(SERVICES - set(running))}"
    for service, info in sorted(running.items()):
        image = info["image"]
        assert info["status"] == "running", f"Dịch vụ {service} đang {info['status']}"
        assert image.startswith(f"{s.registry}/"), f"Dịch vụ {service} chạy image {image}, phải lấy từ {s.registry}"
        repo, _, tag = image[len(s.registry) + 1:].rpartition(":")
        tags = registry(s, f"/v2/{repo}/tags/list").get("tags") or []
        assert tag in tags, f"Registry nội bộ không có {repo}:{tag} mà {service} đang chạy"

    verify = make_on(capstone, m, "verify", VERIFY_TIMEOUT)
    assert verify.returncode == 0, f"make verify thoát mã {verify.returncode}\n{output(verify)}"
    stopped = vm_sh(m, f"docker stop {running['api']['id']}", 60)
    assert stopped.returncode == 0, stopped.stderr
    broken = make_on(capstone, m, "verify", VERIFY_TIMEOUT)
    assert broken.returncode != 0, "Dịch vụ api đã dừng mà make verify vẫn thoát 0"
