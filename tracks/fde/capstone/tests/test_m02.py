import time
from pathlib import Path

import fdekit
from capstonekit import (
    COMPOSE_SHA256,
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
    bundle_vars,
    healthz,
    make,
    make_on,
    need_files,
    output,
    quillo_containers,
    read_sums,
    release,
    release_member,
    sha256,
)

DELIVERY = ("Makefile", "delivery/fetch_release.sh", "delivery/install.sh", "delivery/verify.sh")
REQUIRED = {RELEASE_NAME, "REQUIREMENTS.yaml", "install.sh", "verify.sh", "tools/docker-compose"}


def bundle_files(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} - {"SHA256SUMS"}


def test_m02_bundle_reproducible(capstone):
    need_files(capstone, *DELIVERY)
    rel = release()
    with big_tmp() as tmp:
        work = Path(tmp)
        bundle = work / "bundle"
        build_bundle(capstone, "lawfirm-staging", bundle)
        first = (bundle / "SHA256SUMS").read_bytes()
        build_bundle(capstone, "lawfirm-staging", bundle)
        second = (bundle / "SHA256SUMS").read_bytes()
        assert first == second, "Dựng lại bundle cùng đầu vào mà SHA256SUMS khác: bundle chưa tái lập được"

        sums = read_sums(bundle / "SHA256SUMS")
        files = bundle_files(bundle)
        assert set(sums) == files, (
            f"SHA256SUMS phải liệt kê đúng mọi tệp của bundle. Thiếu dòng: {sorted(files - set(sums))}; "
            f"dòng thừa: {sorted(set(sums) - files)}")
        missing = sorted(REQUIRED - files)
        assert not missing, f"Bundle thiếu {missing}"
        wrong = [name for name, digest in sums.items() if sha256(bundle / name) != digest]
        assert not wrong, f"sha256 trong SHA256SUMS không khớp tệp: {wrong}"
        assert sums[RELEASE_NAME] == rel.sha256, f"{RELEASE_NAME} trong bundle khác byte bản phát hành"
        assert sums["tools/docker-compose"] == COMPOSE_SHA256, "tools/docker-compose không phải binary compose đã ghim"
        assert (bundle / "REQUIREMENTS.yaml").read_bytes() == release_member("REQUIREMENTS.yaml"), (
            f"REQUIREMENTS.yaml của bundle phải là đúng tệp trong {RELEASE_NAME}")

        rejected = work / "rejected"
        bad = make(capstone, "bundle", *bundle_vars("lawfirm-staging", rejected, sha="0" * 64), writable=[work],
                   timeout=120)
        assert bad.returncode != 0, "QUILLO_RELEASE_SHA256 sai mà make bundle vẫn thoát 0"
        assert not (rejected / "SHA256SUMS").exists(), "sha bản phát hành sai mà vẫn để lại một bundle trông như hoàn chỉnh"


def test_m02_installer_idempotent(capstone):
    need_files(capstone, *DELIVERY)
    release()
    timings = {}
    started = time.monotonic()
    with big_tmp() as tmp:
        bundle = Path(tmp) / "bundle"
        build_bundle(capstone, "lab", bundle)
        timings["bundle"] = time.monotonic() - started
        with fdekit.vm("lab-open", memory_mb=MEMORY_MB, forwards=(PORT,)) as m:
            m.put(bundle, REMOTE_BUNDLE)
            timings["boot+copy"] = time.monotonic() - started - timings["bundle"]
            mark = time.monotonic()
            first = make_on(capstone, m, "install", INSTALL_TIMEOUT)
            timings["install"] = time.monotonic() - mark
            assert first.returncode == 0, f"make install lần 1 thoát mã {first.returncode}\n{output(first)}"
            body = healthz(f"http://127.0.0.1:{m.port(PORT)}/healthz")
            assert body.get("version") == VERSION, f"/healthz trả {body}, cần version {VERSION}"
            before = quillo_containers(m)
            assert SERVICES <= set(before), f"Project compose 'quillo' thiếu dịch vụ: {sorted(SERVICES - set(before))}"
            down = {name: c["status"] for name, c in before.items() if c["status"] != "running"}
            assert not down, f"Dịch vụ không chạy sau khi cài: {down}"

            mark = time.monotonic()
            again = make_on(capstone, m, "install", INSTALL_TIMEOUT)
            timings["install again"] = time.monotonic() - mark
            assert again.returncode == 0, f"make install lần 2 thoát mã {again.returncode}\n{output(again)}"
            after = quillo_containers(m)
            changed = sorted(name for name in SERVICES
                             if (before[name]["id"], before[name]["started"]) != (after.get(name, {}).get("id"),
                                                                                  after.get(name, {}).get("started")))
            assert not changed, f"Cài lại cùng bản mà container bị tạo lại hoặc restart: {changed}"
            verify = make_on(capstone, m, "verify", VERIFY_TIMEOUT)
            assert verify.returncode == 0, f"make verify thoát mã {verify.returncode}\n{output(verify)}"
    timings["total"] = time.monotonic() - started
    print("thời gian (s): " + ", ".join(f"{k} {v:.1f}" for k, v in timings.items()))
