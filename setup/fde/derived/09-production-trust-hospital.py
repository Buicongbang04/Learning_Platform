"""Module 09 (chứng minh hệ thống không hỏng): `hospital` (3072 MB) đã chạy quillo 1.0.0 bằng compose một thời gian.

Cài đúng theo mục "Cài từ bundle" của README sản phẩm: bundle `~/quillo-1.0.0.tar` và thư mục `images/` sau khi giải nén
vẫn nằm trên máy, binary compose v5.6.1 đã ghim ở `~/.docker/cli-plugins/` của `fde` (máy không có plugin compose),
`QUILLO_BIND=0.0.0.0` để cổng forward của QEMU tới được api. Phòng Vật tư đã nạp 12 hợp đồng (văn bản CUAD v1, CC BY 4.0,
The Atticus Project) vào thư mục `vat-tu/` qua inbox.

Dựng bằng `09-production-trust-hospital.sh`."""

import hashlib
import io
import json
import shlex
import tarfile
import time
from pathlib import Path

PROFILE = "hospital"
VERSION = "1.0.0"
BUNDLE = Path("tracks/fde/product/dist/quillo-1.0.0.tar")
SCRIPT = Path("setup/fde/derived/09-production-trust-hospital.sh")
COMPOSE = Path("data/raw/fde-tools/docker-compose-v5.6.1/docker-compose-linux-x86_64")
COMPOSE_SHA256 = "47737f4236e6d3ccea7291995203f8f018058783b4c3a9469119811a0b5db8c0"
CUAD = Path("data/raw/cuad/CUAD_v1/CUAD_v1.json")
FOLDER = "vat-tu"
CONTRACTS = {
    "Co-Branding Agency Agreement 2TheMart.txt":
        "2ThemartComInc_19990826_10-12G_EX-10.10_6700288_EX-10.10_Co-Branding Agreement_ Agency Agreement",
    "Sponsorship Agreement ArcGroup.txt": "ArcGroupInc_20171211_8-K_EX-10.1_10976103_EX-10.1_Sponsorship Agreement",
    "Outsourcing Agreement CCA Industries.txt": "CCAINDUSTRIESINC_04_14_2014-EX-10.1-OUTSOURCING AGREEMENT",
    "Sponsorship Agreement drkoop.txt": "DRKOOPCOMINC_04_21_1999-EX-10.28-SPONSORSHIP AGREEMENT",
    "Distributor Agreement Fuse Medical.txt":
        "FuseMedicalInc_20190321_10-K_EX-10.43_11575454_EX-10.43_Distributor Agreement",
    "Cooperation Agreement HPIL.txt": "HPILHOLDING_01_07_2015-EX-99.1-COOPERATION AGREEMENT",
    "Co-Branding Agreement Integrity Media.txt":
        "IntegrityMediaInc_20010329_10-K405_EX-10.17_2373875_EX-10.17_Co-Branding Agreement",
    "Marketing Agreement Loop Industries.txt": "Loop Industries, Inc. - Marketing Agreement",
    "Trademark License Agreement NMF SLF.txt":
        "NmfSlfIInc_20200115_10-12GA_EX-10.5_11946987_EX-10.5_Trademark License Agreement",
    "Endorsement Agreement Performance Sports.txt":
        "PerformanceSportsBrandsInc_20110909_S-1_EX-10.10_7220214_EX-10.10_Endorsement Agreement",
    "Software License and Maintenance Agreement Sparkling Spring.txt":
        "SPARKLINGSPRINGWATERHOLDINGSLTD_07_03_2002-EX-10.13-SOFTWARE LICENSE AND MAINTENANCE AGREEMENT",
    "Maintenance Agreement UAGH.txt": "UAGHINC_04_14_2004-EX-10.18-MAINTENANCE AGREEMENT",
}
INPUTS = [BUNDLE, SCRIPT, COMPOSE_SHA256, CUAD, json.dumps(CONTRACTS, sort_keys=True)]
SITE = False
MEMORY_MB = 3072


def contracts_tar() -> bytes:
    import fdekit

    data = json.loads((fdekit.ROOT / CUAD).read_text(encoding="utf-8"))["data"]
    texts = {entry["title"]: entry["paragraphs"][0]["context"] for entry in data}
    buffer = io.BytesIO()
    old = time.time() - 86400
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, title in sorted(CONTRACTS.items()):
            body = texts[title].encode("utf-8")
            info = tarfile.TarInfo(f"{FOLDER}/{name}")
            info.size, info.mtime, info.mode = len(body), old, 0o644
            tar.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


def build(target):
    import tempfile

    import fdekit

    compose = fdekit.ROOT / COMPOSE
    if not compose.is_file() or hashlib.sha256(compose.read_bytes()).hexdigest() != COMPOSE_SHA256:
        raise RuntimeError(f"Thiếu {COMPOSE} đúng sha256 {COMPOSE_SHA256}; tải theo mục '0. Cài đặt' của module 03")
    target.ssh("mkdir -p ~/.docker/cli-plugins", timeout=60, check=True)
    target.put(compose, "/home/fde/.docker/cli-plugins/docker-compose")
    target.put(fdekit.ROOT / BUNDLE, f"/home/fde/quillo-{VERSION}.tar")
    target.put(fdekit.ROOT / SCRIPT, "/home/fde/quillo-compose.sh")
    with tempfile.TemporaryDirectory() as work:
        seed = Path(work) / "contracts.tar"
        seed.write_bytes(contracts_tar())
        target.put(seed, "/home/fde/contracts.tar")
    done = target.ssh(f"chmod 0755 ~/.docker/cli-plugins/docker-compose && sh /home/fde/quillo-compose.sh {VERSION} "
                      "&& rm /home/fde/quillo-compose.sh", timeout=900)
    if done.returncode != 0:
        raise RuntimeError(f"quillo-compose.sh lỗi ({done.returncode}):\n{done.stdout[-3000:]}\n{done.stderr[-3000:]}")
    quillo = f"/home/fde/quillo-{VERSION}"
    count = (f"t=$(sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {quillo}/.env); "
             "curl -fsS --noproxy '*' -m 20 -H \"Authorization: Bearer $t\" http://127.0.0.1:18080/api/documents")
    deadline = time.monotonic() + 1200
    while True:
        listed = target.ssh(count, timeout=60)
        pending = target.ssh(f"sudo -n find {shlex.quote(quillo)}/inbox -maxdepth 2 -type f -not -path '*/done/*' "
                             "-not -path '*/failed/*' | wc -l", timeout=60).stdout.strip()
        try:
            docs = json.loads(listed.stdout) if listed.returncode == 0 else []
        except json.JSONDecodeError:
            docs = []
        if len(docs) >= len(CONTRACTS) and pending == "0":
            break
        if time.monotonic() > deadline:
            raise RuntimeError(f"Worker chưa nạp đủ {len(CONTRACTS)} hợp đồng sau 1200 s: {len(docs)} tài liệu, "
                               f"{pending} tệp còn trong inbox")
        time.sleep(5)
    failed = target.ssh(f"sudo -n find {shlex.quote(quillo)}/inbox/failed -type f | wc -l", timeout=60).stdout.strip()
    if failed not in ("", "0"):
        raise RuntimeError(f"{failed} hợp đồng vào inbox/failed")
    print(target.ssh("df -B1 / | tail -n 1", timeout=60).stdout.strip())
