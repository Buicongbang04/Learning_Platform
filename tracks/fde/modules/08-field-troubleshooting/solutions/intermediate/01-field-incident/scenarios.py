"""Các sự cố của bài 08/intermediate/01 (chỉ nằm trong solutions/): nguyên nhân thật, cách test dựng lại, tập nguyên nhân
chấp nhận và mẫu "bằng chứng trực tiếp". Cả hai do hồ sơ `hospital` gây ra: đĩa 8 GB và proxy công ty.

`direct` là các cặp (mẫu nguồn, mẫu nội dung): một bằng chứng chỉ là dấu vết trực tiếp khi nguồn của nó khớp mẫu nguồn
và đoạn trích khớp mẫu nội dung tương ứng. Nguồn có ở mọi bundle của bệnh viện bất kể sự cố (vd. biến proxy của hệ thống)
không bao giờ được tính."""

import re
from dataclasses import dataclass
from typing import Callable

QUILLO = "/home/fde/quillo-1.0.0"
HEADROOM = 32 * 1024


@dataclass(frozen=True)
class Scenario:
    name: str
    ticket: str
    accepted: frozenset[str]
    direct: tuple[tuple[re.Pattern, re.Pattern], ...]
    build: Callable


def disk_full(scene) -> None:
    """Job export đêm của HIS bệnh viện ghi bản dump vào /var/backups/his trên cùng ổ / 8 GB với Docker. Ổ đầy: Postgres
    không mở rộng được tệp dữ liệu, worker để nguyên tài liệu mới và thử lại mãi; đọc vẫn chạy nên /healthz vẫn 200."""
    scene.wait_health()
    scene.ask("Kết quả xét nghiệm máu gần nhất là bao nhiêu?")
    scene.drop([f"ket-qua-{scene.rng.randint(100, 999)}-{n}.txt" for n in range(4)], words=60)
    scene.must("sudo -n install -d -m 0750 /var/backups/his && a=$(df -B1 --output=avail / | tail -n 1) && "
               f"sudo -n fallocate -l $((a - {HEADROOM})) /var/backups/his/his-export-$(date +%Y%m%d).dump",
               "d1")
    scene.wait_log("db", "No space left on device", 150, "d2")
    scene.ask("Kết quả xét nghiệm sinh hoá của bệnh nhân mới nhất?")


def proxy_into_containers(scene) -> None:
    """IT bệnh viện "sửa" việc docker pull bằng cách khai proxy trong ~/.docker/config.json của user vận hành, rồi chạy
    lại stack trong đợt bảo trì. Docker CLI/compose bơm HTTP(S)_PROXY vào mọi container tạo mới, noProxy không có tên
    dịch vụ nội bộ: api gọi http://llm:8080, http://embed:8080 đi qua proxy và nhận 502."""
    scene.wait_health()
    scene.ask("Quy trình tiếp nhận bệnh nhân cấp cứu?")
    config = ('{"proxies": {"default": {"httpProxy": "http://10.0.2.100:3128", "httpsProxy": "http://10.0.2.100:3128", '
              '"noProxy": "localhost,127.0.0.1"}}}')
    scene.must(f"mkdir -p ~/.docker && printf '%s\\n' '{config}' > ~/.docker/config.json && cd {QUILLO} && "
               "(nohup docker compose up -d --force-recreate >/dev/null 2>&1 &)", "p1")
    deadline_cmd = ("for i in $(seq 90); do docker inspect --format '{{json .Config.Env}}' quillo-api-1 2>/dev/null "
                    "| grep -q HTTP_PROXY && break; sleep 1; done; docker inspect --format '{{json .Config.Env}}' "
                    "quillo-api-1 | grep -q HTTP_PROXY")
    scene.must(deadline_cmd, "p2", timeout=150)
    scene.wait_api()
    for question in ("Quy trình tiếp nhận bệnh nhân cấp cứu?", "Lịch trực khoa nội tuần này?"):
        scene.ask(question)
    scene.wait_log("api", "502 Bad Gateway", 60, "p3")


SCENARIOS = {
    "disk-night-export": Scenario(
        "disk-night-export",
        "Từ sáng nay, kết quả xét nghiệm mới khoa thả vào thư mục chung không lên quillo: hỏi về ca mới thì không có "
        "trích dẫn nào, hỏi tài liệu cũ vẫn được. Trang trạng thái của quillo vẫn báo ok. Hôm qua mọi thứ bình thường.",
        frozenset({"disk-full"}),
        ((re.compile(r"^bundle:system/df\.txt$"), re.compile(r"100% /")),
         (re.compile(r"^bundle:quillo/logs/(db|worker|api)\.log$"),
          re.compile(r"No space left on device|DiskFull|could not extend file")),
         (re.compile(r"^customer:"),
          re.compile(r"No space left on device|DiskFull|could not extend file|100% /|/var/backups/his"))),
        disk_full,
    ),
    "proxy-docker-config": Scenario(
        "proxy-docker-config",
        "Sau đợt bảo trì cuối tuần của phòng IT, hỏi gì quillo cũng báo lỗi 'Model server không phản hồi'. Trang "
        "trạng thái báo degraded. IT đã kiểm: docker ps thấy hai container model vẫn Up (healthy), không ai đụng vào "
        "quillo cả.",
        frozenset({"proxy-misrouting", "config-error"}),
        ((re.compile(r"^customer:"), re.compile(r"HTTPS?_PROXY=http|\"https?Proxy\"")),),
        proxy_into_containers,
    ),
}
