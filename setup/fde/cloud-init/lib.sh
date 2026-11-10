#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive LC_ALL=C

LAB_USER=fde

ubuntu_base() {
    systemctl disable --now apt-daily.timer apt-daily-upgrade.timer unattended-upgrades.service 2>/dev/null || true
    while fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock >/dev/null 2>&1; do sleep 2; done
    snap list 2>/dev/null || true
    apt-get purge -y snapd
    rm -rf /snap /var/snap /var/lib/snapd /var/cache/snapd /root/snap "/home/$LAB_USER/snap"
    apt-get update
    apt-get purge -y unattended-upgrades
}

ubuntu_docker() {
    apt-get install -y --no-install-recommends docker.io
    systemctl enable docker.service containerd.service
    usermod -aG docker "$LAB_USER"
    echo "docker.io $(dpkg-query -W -f='${Version}' docker.io)"
    echo "containerd $(dpkg-query -W -f='${Version}' containerd)"
    echo "runc $(dpkg-query -W -f='${Version}' runc)"
}

rocky_podman() {
    systemctl disable --now dnf-makecache.timer || true
    dnf -y install podman
    if ! grep -q "^$LAB_USER:" /etc/subuid; then usermod --add-subuids 100000-165535 "$LAB_USER"; fi
    if ! grep -q "^$LAB_USER:" /etc/subgid; then usermod --add-subgids 100000-165535 "$LAB_USER"; fi
    dnf clean all
    echo "podman $(rpm -q --qf '%{VERSION}-%{RELEASE}' podman)"
    echo "selinux $(getenforce)"
}

finalize() {
    if command -v apt-get >/dev/null; then apt-get autoremove -y; apt-get clean; fi
    echo "os $(. /etc/os-release && echo "$ID $VERSION_ID") kernel $(uname -r) glibc $(getconf GNU_LIBC_VERSION)"
    rm -f /etc/sudoers.d/90-cloud-init-users
    : > "/home/$LAB_USER/.ssh/authorized_keys"
    rm -f /home/$LAB_USER/.bash_history /root/.bash_history
    rm -rf /tmp/fde-prepare
    cloud-init clean --logs
    truncate -s 0 /etc/machine-id
    rm -f /var/lib/dbus/machine-id
    journalctl --vacuum-time=1s >/dev/null 2>&1 || true
    sync
    fstrim -av || true
}
