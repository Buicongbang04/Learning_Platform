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

fetch_verified() {
    local url=$1 dest=$2 sha=$3
    curl -fsSL --retry 5 --retry-delay 3 -o "$dest" "$url"
    if ! echo "$sha  $dest" | sha256sum -c --status; then
        echo "sha256 của $url không khớp: cần $sha, nhận $(sha256sum "$dest" | cut -d' ' -f1)" >&2
        exit 1
    fi
}

debian_base() {
    systemctl disable --now apt-daily.timer apt-daily-upgrade.timer unattended-upgrades.service 2>/dev/null || true
    while pgrep -x 'apt-get|apt|dpkg|unattended-upgr' >/dev/null; do sleep 2; done
    apt-get update
    apt-get purge -y unattended-upgrades
    apt-get install -y --no-install-recommends curl ca-certificates iproute2
}

DOCKER_POOL=https://download.docker.com/linux/debian/dists/bookworm/pool/stable/amd64
DOCKER_DEBS=(
    "containerd.io_2.4.2-3~debian.12~bookworm_amd64.deb e8ba23b41c06ba56f10fb09612873024cc5527d4ba06045e650b2007f38da0ee"
    "docker-ce-cli_29.9.2-1~debian.12~bookworm_amd64.deb 06ebf3de771f5673de48d01837d55309e0732958f071ac8c93f4e35d85979bf1"
    "docker-ce_29.9.2-1~debian.12~bookworm_amd64.deb 8a85f26b3c980b9f2b3b909d7d20cc4d710c8774cce5e8bb02369301ae31240a"
    "docker-buildx-plugin_0.38.1-1~debian.12~bookworm_amd64.deb 4c8cea81b803b004e95ab646743a6c5f1d5dae19ff69f7fdced5a32299ce8383"
    "docker-compose-plugin_5.6.1-1~debian.12~bookworm_amd64.deb de9e644353b09379bd589cf040b5fe482c8316f93307a271e210321ab0ef2c48"
)

debian_docker_ce() {
    local dir=/root/fde-debs entry name sha
    mkdir -p "$dir"
    for entry in "${DOCKER_DEBS[@]}"; do
        read -r name sha <<<"$entry"
        fetch_verified "$DOCKER_POOL/$name" "$dir/$name" "$sha"
    done
    apt-get install -y --no-install-recommends "$dir"/*.deb
    rm -rf "$dir"
    systemctl enable docker.service containerd.service
    usermod -aG docker "$LAB_USER"
    for pkg in docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; do
        echo "$pkg $(dpkg-query -W -f='${Version}' "$pkg")"
    done
}

rocky_linger() {
    loginctl enable-linger "$LAB_USER"
    echo "linger $(loginctl show-user "$LAB_USER" -p Linger)"
}

profile_quirks() {
    if [ "${FDE_TMP_NOEXEC:-0}" = 1 ]; then
        echo "tmpfs /tmp tmpfs rw,nosuid,nodev,noexec,size=512m,mode=1777 0 0" >> /etc/fstab
        echo "quirk /tmp tmpfs noexec"
    fi
    if [ -n "${FDE_NOFILE:-}" ]; then
        printf '* soft nofile %s\n* hard nofile %s\n' "$FDE_NOFILE" "$FDE_NOFILE" > /etc/security/limits.d/90-fde-nofile.conf
        mkdir -p /etc/systemd/system.conf.d /etc/systemd/user.conf.d
        printf '[Manager]\nDefaultLimitNOFILE=%s:%s\n' "$FDE_NOFILE" "$FDE_NOFILE" > /etc/systemd/system.conf.d/90-fde-nofile.conf
        cp /etc/systemd/system.conf.d/90-fde-nofile.conf /etc/systemd/user.conf.d/90-fde-nofile.conf
        echo "quirk nofile $FDE_NOFILE"
    fi
    if [ -n "${FDE_NETEM:-}" ]; then
        cat > /usr/local/sbin/fde-netem <<SH
#!/bin/sh
for i in \$(seq 60); do
    dev=\$(ip -o route get 10.0.2.2 2>/dev/null | sed -n 's/.* dev \([^ ]*\).*/\1/p')
    [ -n "\$dev" ] && exec tc qdisc replace dev "\$dev" root netem $FDE_NETEM
    sleep 1
done
echo "không thấy giao diện tới 10.0.2.2" >&2
exit 1
SH
        chmod 0755 /usr/local/sbin/fde-netem
        cat > /etc/systemd/system/fde-netem.service <<'UNIT'
[Unit]
Description=Mạng nhà máy: trễ và mất gói trên giao diện ra (tc netem)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/fde-netem

[Install]
WantedBy=multi-user.target
UNIT
        systemctl enable fde-netem.service
        modprobe sch_netem
        echo "quirk netem $FDE_NETEM"
    fi
}

K3S_VERSION="v1.37.1+k3s1"
K3S_RELEASE="https://github.com/k3s-io/k3s/releases/download/$K3S_VERSION"
K3S_SHA256=92b94582eb7b34a8cf532e6006842b9ed215a6783cf56a3dd6271fd35243b2c0
K3S_IMAGES_SHA256=865b2a63ad7a63fc0db17b7fc2985bf4ae11d5ae93ca1472be6218d20aeb6b23
K3S_INSTALL_URL="https://raw.githubusercontent.com/k3s-io/k3s/$K3S_VERSION/install.sh"
K3S_INSTALL_SHA256=ed01f89fd977bf20ac1516bbebf8370bf3ddbaa55dac8aba610956a4c78cc00b
KUBECTL_VERSION=v1.37.1
KUBECTL_SHA256=65691ff77eb6fa44c908b77a1082c9f092c3b9733b5cefabec0d1104890e21a8
HELM_VERSION=v3.22.1
HELM_SHA256=896cf63684a42a723d61c980369d6e588330927deb13676ca0d85006dd6da0ea
K3S_NODE=lawfirm-prod

netplan_default_route() {
    local dev
    dev=$(ip -o route get 10.0.2.2 | sed -n 's/.* dev \([^ ]*\).*/\1/p')
    cat > /etc/netplan/60-fde-default-route.yaml <<NETPLAN
network:
  version: 2
  ethernets:
    $dev:
      routes:
        - to: default
          via: 10.0.2.2
          metric: 1024
NETPLAN
    chmod 0600 /etc/netplan/60-fde-default-route.yaml
    netplan generate
    echo "default route via 10.0.2.2 dev $dev (metric 1024)"
}

k3s_airgap() {
    local work=/root/fde-k3s images=/var/lib/rancher/k3s/agent/images
    mkdir -p "$work" "$images" /etc/rancher/k3s
    fetch_verified "$K3S_RELEASE/k3s" "$work/k3s" "$K3S_SHA256"
    fetch_verified "$K3S_RELEASE/k3s-airgap-images-amd64.tar.zst" "$images/k3s-airgap-images-amd64.tar.zst" "$K3S_IMAGES_SHA256"
    fetch_verified "$K3S_INSTALL_URL" "$work/install.sh" "$K3S_INSTALL_SHA256"
    fetch_verified "https://get.helm.sh/helm-$HELM_VERSION-linux-amd64.tar.gz" "$work/helm.tar.gz" "$HELM_SHA256"
    fetch_verified "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl" "$work/kubectl" "$KUBECTL_SHA256"
    install -m 0755 "$work/k3s" /usr/local/bin/k3s
    install -m 0755 "$work/kubectl" /usr/local/bin/kubectl
    tar -xzf "$work/helm.tar.gz" -C "$work" linux-amd64/helm
    install -m 0755 "$work/linux-amd64/helm" /usr/local/bin/helm
    cat > /etc/rancher/k3s/config.yaml <<CFG
node-name: $K3S_NODE
write-kubeconfig-mode: "0600"
disable:
  - traefik
  - servicelb
CFG
    cat > /etc/rancher/k3s/registries.yaml <<'REG'
mirrors:
  "10.0.2.101:5000":
    endpoint:
      - "http://10.0.2.101:5000"
  docker.io:
    endpoint:
      - "http://10.0.2.101:5000"
REG
    INSTALL_K3S_SKIP_DOWNLOAD=true INSTALL_K3S_VERSION="$K3S_VERSION" sh "$work/install.sh"
    rm -rf "$work"
    local i
    for i in $(seq 90); do
        k3s kubectl get node "$K3S_NODE" >/dev/null 2>&1 && break
        sleep 2
    done
    k3s kubectl wait --for=condition=Ready "node/$K3S_NODE" --timeout=300s
    local deployment
    for deployment in coredns local-path-provisioner metrics-server; do
        for i in $(seq 150); do
            k3s kubectl -n kube-system get "deployment/$deployment" >/dev/null 2>&1 && break
            sleep 2
        done
        k3s kubectl -n kube-system rollout status "deployment/$deployment" --timeout=300s
    done
    rm -f "$images/k3s-airgap-images-amd64.tar.zst"
    echo "k3s $(k3s --version | head -1)"
    echo "helm $(helm version --short)"
    echo "kubectl $(kubectl version --client | head -1)"
    k3s crictl images
}

k3s_tenant() {
    local ns=${FDE_K8S_NAMESPACE:?} kubeconfig=${FDE_KUBECONFIG:?}
    k3s kubectl apply -f - <<YAML
apiVersion: v1
kind: Namespace
metadata:
  name: $ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: $ns-quota
  namespace: $ns
spec:
  hard:
    requests.cpu: "3"
    requests.memory: 4Gi
    limits.memory: 5Gi
    pods: "12"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: $ns-limits
  namespace: $ns
spec:
  limits:
    - type: Pod
      max:
        cpu: "2"
        memory: 3Gi
    - type: PersistentVolumeClaim
      max:
        storage: 10Gi
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: $ns
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: $LAB_USER
  namespace: $ns
---
apiVersion: v1
kind: Secret
metadata:
  name: $LAB_USER-token
  namespace: $ns
  annotations:
    kubernetes.io/service-account.name: $LAB_USER
type: kubernetes.io/service-account-token
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: $LAB_USER-deployer
  namespace: $ns
rules:
  - apiGroups: [""]
    resources: [pods, pods/log, pods/exec, pods/portforward, pods/attach, services, configmaps, secrets,
                persistentvolumeclaims, serviceaccounts]
    verbs: [get, list, watch, create, update, patch, delete, deletecollection]
  - apiGroups: [apps]
    resources: [deployments, deployments/scale, statefulsets, statefulsets/scale, replicasets, daemonsets]
    verbs: [get, list, watch, create, update, patch, delete, deletecollection]
  - apiGroups: [batch]
    resources: [jobs, cronjobs]
    verbs: [get, list, watch, create, update, patch, delete, deletecollection]
  - apiGroups: [networking.k8s.io]
    resources: [networkpolicies, ingresses]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [policy]
    resources: [poddisruptionbudgets]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [autoscaling]
    resources: [horizontalpodautoscalers]
    verbs: [get, list, watch, create, update, patch, delete]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: $LAB_USER-deployer
  namespace: $ns
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: $LAB_USER-deployer
subjects:
  - kind: ServiceAccount
    name: $LAB_USER
    namespace: $ns
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: $LAB_USER-view
  namespace: $ns
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: view
subjects:
  - kind: ServiceAccount
    name: $LAB_USER
    namespace: $ns
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: $ns-protect-default-deny
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [networking.k8s.io]
        apiVersions: ["*"]
        operations: [UPDATE, DELETE]
        resources: [networkpolicies]
  matchConditions:
    - name: tenant-service-account
      expression: request.userInfo.username == "system:serviceaccount:$ns:$LAB_USER"
  validations:
    - expression: request.name != "default-deny"
      message: NetworkPolicy default-deny do IT khách quản; thêm NetworkPolicy riêng để mở luồng cần thiết
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: $ns-protect-default-deny
spec:
  policyName: $ns-protect-default-deny
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: $ns
YAML
    local token="" i
    for i in $(seq 60); do
        token=$(k3s kubectl -n "$ns" get secret "$LAB_USER-token" -o jsonpath='{.data.token}' | base64 -d)
        [ -n "$token" ] && break
        sleep 1
    done
    [ -n "$token" ] || { echo "token của ServiceAccount $LAB_USER chưa được cấp" >&2; exit 1; }
    install -d -m 0700 -o "$LAB_USER" -g "$LAB_USER" "$(dirname "$kubeconfig")"
    local tmp
    tmp=$(mktemp)
    k3s kubectl config --kubeconfig="$tmp" set-cluster "$K3S_NODE" --server=https://127.0.0.1:6443 \
        --certificate-authority=/var/lib/rancher/k3s/server/tls/server-ca.crt --embed-certs=true >/dev/null
    k3s kubectl config --kubeconfig="$tmp" set-credentials "$LAB_USER" --token="$token" >/dev/null
    k3s kubectl config --kubeconfig="$tmp" set-context "$ns" --cluster="$K3S_NODE" --user="$LAB_USER" --namespace="$ns" >/dev/null
    k3s kubectl config --kubeconfig="$tmp" use-context "$ns" >/dev/null
    install -m 0600 -o "$LAB_USER" -g "$LAB_USER" "$tmp" "$kubeconfig"
    rm -f "$tmp"
    sudo -u "$LAB_USER" -H kubectl --kubeconfig="$kubeconfig" auth can-i create deployments -n "$ns"
    echo "tenant $ns kubeconfig $kubeconfig"
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
