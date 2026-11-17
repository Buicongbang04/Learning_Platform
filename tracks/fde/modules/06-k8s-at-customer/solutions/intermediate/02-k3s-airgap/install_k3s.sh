#!/bin/sh
set -eu
version="v1.37.1+k3s1"
registry=10.0.2.101:5000
gateway=${K3S_GATEWAY:-10.0.2.2}
src=$HOME/k3s-airgap
images=/var/lib/rancher/k3s/agent/images
airgap=k3s-airgap-images-amd64.tar.zst

log() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*"; }

cd "$src"
sha256sum -c - <<SUMS
92b94582eb7b34a8cf532e6006842b9ed215a6783cf56a3dd6271fd35243b2c0  k3s
865b2a63ad7a63fc0db17b7fc2985bf4ae11d5ae93ca1472be6218d20aeb6b23  $airgap
ed01f89fd977bf20ac1516bbebf8370bf3ddbaa55dac8aba610956a4c78cc00b  install.sh
SUMS

if ! ip -4 route show default | grep -q .; then
    dev=$(ip -o -4 route get "$gateway" | sed -n 's/.* dev \([^ ]*\).*/\1/p')
    log "chưa có route mặc định IPv4: thêm default via $gateway dev $dev (metric 1024)"
    sudo ip route add default via "$gateway" dev "$dev" metric 1024
    sudo tee /etc/netplan/60-k3s-default-route.yaml >/dev/null <<NETPLAN
network:
  version: 2
  ethernets:
    $dev:
      routes:
        - to: default
          via: $gateway
          metric: 1024
NETPLAN
    sudo chmod 0600 /etc/netplan/60-k3s-default-route.yaml
    sudo netplan generate
fi

log "binary k3s $version và image air-gap"
sudo install -m 0755 k3s /usr/local/bin/k3s
sudo install -d -m 0755 "$images" /etc/rancher/k3s
if ! sudo cmp -s "$airgap" "$images/$airgap"; then
    sudo install -m 0644 "$airgap" "$images/$airgap"
fi

log "registry nội bộ $registry (HTTP)"
sudo tee /etc/rancher/k3s/registries.yaml >/dev/null <<REG
mirrors:
  "$registry":
    endpoint:
      - "http://$registry"
REG
sudo tee /etc/rancher/k3s/config.yaml >/dev/null <<CFG
write-kubeconfig-mode: "0600"
CFG

log "cài service k3s (không tải gì từ internet)"
sudo env INSTALL_K3S_SKIP_DOWNLOAD=true INSTALL_K3S_VERSION="$version" sh ./install.sh

i=0
until sudo k3s kubectl get node "$(hostname)" >/dev/null 2>&1; do
    i=$((i + 1))
    [ "$i" -lt 60 ] || { sudo journalctl -u k3s --no-pager | tail -20 >&2; exit 1; }
    sleep 2
done
sudo k3s kubectl wait --for=condition=Ready "node/$(hostname)" --timeout=120s
log "k3s sẵn sàng: $(sudo k3s kubectl get node -o wide --no-headers)"
