import json
import os
import re
import stat
import struct
from pathlib import Path

import pytest
import yaml

from testkit import Exercise, KubeLab, kind_node_cp, kind_node_exec, run_sandboxed

ex = Exercise(__file__)
FAKE_BIN = Path(__file__).parent / "fixtures" / "bin"
PKI = "/etc/kubernetes/pki/etcd"
EXPECTED = {
    "endpoints": "https://127.0.0.1:2379",
    "cacert": f"{PKI}/ca.crt",
    "pairs": {(f"{PKI}/server.crt", f"{PKI}/server.key"), (f"{PKI}/healthcheck-client.crt", f"{PKI}/healthcheck-client.key")},
}
NAME = re.compile(r"etcd-snapshot-\d{8}T\d{6}Z\.db")


def backup(tmp_path: Path, **extra: str):
    calls = tmp_path / "calls.jsonl"
    calls.touch()
    env = {"PATH": f"{FAKE_BIN}:{os.environ.get('PATH', '/usr/bin:/bin')}", "FAKE_CALLS": str(calls),
           "ETCD_BACKUP_DIR": str(tmp_path / "backups"), **extra}
    result = run_sandboxed(["bash", str(ex.path("etcd-backup.sh"))], writable=[tmp_path], readonly=[ex.target, FAKE_BIN],
                           cwd=tmp_path, env=env, timeout=60)
    records = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines() if line.strip()]
    return result, records


def snapshots(tmp_path: Path) -> list[str]:
    folder = tmp_path / "backups"
    return sorted(p.name for p in folder.iterdir() if NAME.fullmatch(p.name)) if folder.is_dir() else []


def flags(record: dict) -> dict[str, str]:
    found = {k.removeprefix("ETCDCTL_").lower(): v for k, v in record["env"].items()}
    args = record["args"]
    for index, arg in enumerate(args):
        if arg.startswith("--"):
            name, sep, value = arg[2:].partition("=")
            if not sep and index + 1 < len(args) and not args[index + 1].startswith("-"):
                value = args[index + 1]
            found[name] = value
    return found


def old_snapshot(tmp_path: Path, stamp: str) -> Path:
    path = tmp_path / "backups" / f"etcd-snapshot-{stamp}.db"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"cu")
    return path


def test_snapshot_uses_kubeadm_endpoint_and_certificates(tmp_path):
    result, records = backup(tmp_path)
    saves = [r for r in records if r["tool"] == "etcdctl" and "save" in r["args"]]
    assert saves, f"Script chưa gọi etcdctl snapshot save:\n{result.stderr[-500:]}"
    used = flags(saves[0])
    assert used.get("endpoints") == EXPECTED["endpoints"], f"endpoint của etcd trên control plane là {EXPECTED['endpoints']}"
    assert used.get("cacert") == EXPECTED["cacert"], "--cacert là CA của etcd, không phải CA của cluster"
    assert (used.get("cert"), used.get("key")) in EXPECTED["pairs"], (
        "--cert/--key là một cặp chứng chỉ client etcd tin (server hay healthcheck-client trong pki/etcd)")


def test_snapshot_file_name_mode_and_verification(tmp_path):
    result, records = backup(tmp_path)
    assert result.returncode == 0, result.stderr[-800:]
    files = snapshots(tmp_path)
    assert len(files) == 1, f"Mong đợi một tệp etcd-snapshot-<UTC>.db, thấy {files}"
    path = tmp_path / "backups" / files[0]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600, "Snapshot chứa mọi Secret của cluster: quyền 0600"
    assert result.stdout.strip().splitlines()[-1] == str(path), "Dòng cuối stdout là đường dẫn snapshot"
    statuses = [r for r in records if r["tool"] == "etcdutl" and r["args"][:2] == ["snapshot", "status"]]
    assert statuses and statuses[-1]["args"][2] == str(path), "Kiểm snapshot vừa lưu bằng etcdutl snapshot status"
    assert not list((tmp_path / "backups").glob("*.part"))


def test_retention_keeps_newest_and_other_files(tmp_path):
    for day in range(1, 9):
        old_snapshot(tmp_path, f"202610{day:02d}T020000Z")
    (tmp_path / "backups" / "README.txt").write_text("ghi chú của ops\n", encoding="utf-8")
    result, _ = backup(tmp_path, ETCD_BACKUP_KEEP="3")
    assert result.returncode == 0, result.stderr[-800:]
    files = snapshots(tmp_path)
    assert len(files) == 3, f"ETCD_BACKUP_KEEP=3 phải còn đúng 3 snapshot: {files}"
    assert files[:2] == ["etcd-snapshot-20261007T020000Z.db", "etcd-snapshot-20261008T020000Z.db"]
    assert (tmp_path / "backups" / "README.txt").is_file(), "Không xoá tệp khác trong thư mục backup"


def test_etcdctl_failure_fails_closed(tmp_path):
    for day in range(1, 5):
        old_snapshot(tmp_path, f"202610{day:02d}T020000Z")
    result, records = backup(tmp_path, ETCD_BACKUP_KEEP="2", FAKE_ETCDCTL_FAIL="1")
    assert any(r["tool"] == "etcdctl" for r in records), "Script chưa gọi etcdctl"
    assert result.returncode != 0, "etcdctl lỗi thì script phải trả mã khác 0"
    assert len(snapshots(tmp_path)) == 4, "Lần backup lỗi không được chạy dọn bản cũ"
    assert not list((tmp_path / "backups").glob("*.part")), "Không để lại tệp .part"


@pytest.mark.parametrize("extra", [{"FAKE_ETCDUTL_FAIL": "1"}, {"FAKE_TOTAL_KEYS": "0"}])
def test_bad_snapshot_is_removed(tmp_path, extra):
    result, records = backup(tmp_path, **extra)
    assert any(r["tool"] == "etcdutl" for r in records), "Script chưa kiểm snapshot bằng etcdutl snapshot status"
    assert result.returncode != 0, "Snapshot hỏng hay rỗng phải làm script lỗi"
    assert snapshots(tmp_path) == [], "Snapshot không qua kiểm phải bị xoá, không để lại bản trông như hợp lệ"


def test_kubeadm_paths_and_snapshot_on_real_control_plane(tmp_path):
    ex.require_cluster()
    kind_node_cp("devops-lab-control-plane", "/etc/kubernetes/manifests/etcd.yaml", tmp_path / "etcd.yaml")
    manifest = yaml.safe_load((tmp_path / "etcd.yaml").read_text(encoding="utf-8"))
    command = manifest["spec"]["containers"][0]["command"]
    options = dict(arg[2:].split("=", 1) for arg in command if arg.startswith("--") and "=" in arg)
    assert options["trusted-ca-file"] == EXPECTED["cacert"]
    assert (options["cert-file"], options["key-file"]) in EXPECTED["pairs"]
    assert EXPECTED["endpoints"] in options["listen-client-urls"].split(",")
    data_dirs = [v["hostPath"]["path"] for v in manifest["spec"].get("volumes", []) if v.get("name") == "etcd-data"]
    assert data_dirs == ["/var/lib/etcd"], (
        f"Static pod etcd của devops-lab đang dùng data dir {data_dirs}, không phải /var/lib/etcd (thường do lab restore trỏ manifest "
        "sang thư mục khác). Làm lại bước 3 của lab restore ở mục 6 của module, hoặc xoá và tạo lại cluster")
    with KubeLab() as lab:
        lab.kubectl("create", "configmap", "truoc-khi-backup", "--from-literal=thoi-diem=2026-11-02")
        try:
            saved = kind_node_exec(
                "devops-lab-control-plane", "crictl", "exec", "-q", "--name", "^etcd$", "--state", "running", "etcdctl",
                "--endpoints=https://127.0.0.1:2379", "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
                "--cert=/etc/kubernetes/pki/etcd/server.crt", "--key=/etc/kubernetes/pki/etcd/server.key",
                "snapshot", "save", "/var/lib/etcd/devops-ex-snapshot.db", timeout=120)
            assert saved.returncode == 0, saved.stderr[-800:]
            kind_node_cp("devops-lab-control-plane", "/var/lib/etcd/devops-ex-snapshot.db", tmp_path / "snapshot.db")
        finally:
            kind_node_exec("devops-lab-control-plane", "rm", "-f", "/var/lib/etcd/devops-ex-snapshot.db",
                           "/var/lib/etcd/devops-ex-snapshot.db.part")
        data = (tmp_path / "snapshot.db").read_bytes()
        assert struct.unpack_from("<I", data, 16)[0] == 0xED0CDAED, "Snapshot phải là tệp bbolt hợp lệ"
        assert f"/registry/configmaps/{lab.namespace}/truoc-khi-backup".encode() in data
