#!/usr/bin/env bash
# Dựng cluster kind `mlops` (1 node) với cert-manager, KServe (RawDeployment) và Argo Workflows. Chạy lại an toàn.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
source "$HERE/versions.env"

if [[ -f "$ROOT/setup/.env" ]]; then
  while IFS='=' read -r key value; do
    [[ -z "${!key:-}" ]] && export "$key=$value"
  done < <(grep -E '^MLOPS_KIND_(HTTP|HTTPS)_PORT=[0-9]+$' "$ROOT/setup/.env" || true)
fi
HTTP_PORT="${MLOPS_KIND_HTTP_PORT:-28081}"
HTTPS_PORT="${MLOPS_KIND_HTTPS_PORT:-28444}"
BIN_DIR="$HOME/.local/bin"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/mlops-kind"
CLUSTER=mlops
CTX=kind-mlops
NODE="${CLUSTER}-control-plane"
START=$(date +%s)

log() { printf '\033[1m[up.sh %3ss]\033[0m %s\n' "$(( $(date +%s) - START ))" "$*"; }
die() { printf 'LỖI: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || die "cần Docker"
docker info >/dev/null 2>&1 || die "Docker chưa chạy"
command -v sha256sum >/dev/null || die "cần sha256sum (coreutils)"
command -v python3 >/dev/null || die "cần python3"
mkdir -p "$BIN_DIR" "$CACHE"

fetch() {
  local url="$1" sha="$2" out="$3"
  if [[ -f "$out" ]] && echo "$sha  $out" | sha256sum --check --status; then
    return 0
  fi
  local tmp="$out.part"
  curl -fsSL --retry 3 -o "$tmp" "$url"
  echo "$sha  $tmp" | sha256sum --check --quiet || { rm -f "$tmp"; die "checksum sai: $url"; }
  mv "$tmp" "$out"
}

install_bin() {
  local name="$1" version="$2" url="$3" sha="$4"
  local target="$BIN_DIR/$name"
  if [[ -x "$target" ]] && echo "$sha  $target" | sha256sum --check --status; then
    log "$name $version đã có (checksum khớp): $target"
    return 0
  fi
  log "Tải $name $version -> $target (kiểm sha256 trước khi cài)"
  fetch "$url" "$sha" "$CACHE/$name-$version"
  install -m 0755 "$CACHE/$name-$version" "$target"
}

install_bin kind "$KIND_VERSION" "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-linux-amd64" "$KIND_SHA256"
install_bin kubectl "$KUBECTL_VERSION" "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" "$KUBECTL_SHA256"
KIND="$BIN_DIR/kind"
KUBECTL="$BIN_DIR/kubectl"
k() { "$KUBECTL" --context "$CTX" "$@"; }

port_busy() { ss -ltnH "sport = :$1" 2>/dev/null | grep -q .; }

if "$KIND" get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  if [[ "$(docker inspect -f '{{.State.Running}}' "$NODE" 2>/dev/null)" != "true" ]]; then
    log "Node $NODE đang dừng, khởi động lại"
    docker start "$NODE" >/dev/null
  fi
  log "Cluster $CLUSTER đã có"
  "$KIND" export kubeconfig --name "$CLUSTER" >/dev/null 2>&1
else
  for port in "$HTTP_PORT" "$HTTPS_PORT"; do
    port_busy "$port" && die "cổng $port đã bị dùng; đặt MLOPS_KIND_HTTP_PORT / MLOPS_KIND_HTTPS_PORT trong setup/.env"
  done
  config="$CACHE/cluster.yaml"
  sed -e "s/hostPort: 28081/hostPort: ${HTTP_PORT}/" -e "s/hostPort: 28444/hostPort: ${HTTPS_PORT}/" \
    "$HERE/cluster.yaml" > "$config"
  log "Tạo cluster $CLUSTER ($KIND_NODE_IMAGE), cổng 127.0.0.1:${HTTP_PORT}->30080, 127.0.0.1:${HTTPS_PORT}->30443"
  "$KIND" create cluster --config "$config" --wait 180s
fi

log "Chờ API server"
for _ in $(seq 1 60); do
  [[ "$(k get --raw /readyz 2>/dev/null)" == "ok" ]] && break
  sleep 2
done
k wait --for=condition=Ready node --all --timeout=180s >/dev/null

retry() {
  local n
  for n in 1 2 3 4 5 6 7 8 9 10; do
    "$@" && return 0
    log "thử lại ($n/10) sau 10s: $*"
    sleep 10
  done
  return 1
}

log "cert-manager ${CERT_MANAGER_VERSION}"
fetch "https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.yaml" \
  "$CERT_MANAGER_SHA256" "$CACHE/cert-manager-${CERT_MANAGER_VERSION}.yaml"
k apply --server-side -f "$CACHE/cert-manager-${CERT_MANAGER_VERSION}.yaml" >/dev/null
k -n cert-manager wait --for=condition=Available deployment --all --timeout=300s

log "KServe ${KSERVE_VERSION} (RawDeployment, không Knative/Istio)"
fetch "https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve.yaml" \
  "$KSERVE_SHA256" "$CACHE/kserve-${KSERVE_VERSION}.yaml"
fetch "https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve-cluster-resources.yaml" \
  "$KSERVE_RUNTIMES_SHA256" "$CACHE/kserve-cluster-resources-${KSERVE_VERSION}.yaml"
kserve_image="$(k -n kserve get deployment kserve-controller-manager -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true)"
kserve_mode="$(k -n kserve get configmap inferenceservice-config -o jsonpath='{.data.deploy}' 2>/dev/null || true)"
if [[ "$kserve_image" == "kserve/kserve-controller:${KSERVE_VERSION}" && "$kserve_mode" == *RawDeployment* ]]; then
  log "KServe ${KSERVE_VERSION} đã cài ở RawDeployment, không apply lại (apply lại sẽ trả inferenceservice-config về mặc định trong chốc lát)"
else
  k create namespace kserve --dry-run=client -o yaml | k apply -f - >/dev/null
  retry k apply --server-side --force-conflicts -f "$CACHE/kserve-${KSERVE_VERSION}.yaml" >/dev/null
  ingress="$(k -n kserve get configmap inferenceservice-config -o jsonpath='{.data.ingress}')"
  ingress="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d["disableIngressCreation"]=True; print(json.dumps(d))' "$ingress")"
  patch="$(python3 -c 'import json,sys; print(json.dumps({"data": {"deploy": json.dumps({"defaultDeploymentMode": "RawDeployment"}), "ingress": sys.argv[1]}}))' "$ingress")"
  k -n kserve patch configmap inferenceservice-config --type merge -p "$patch" >/dev/null
fi
k -n kserve wait --for=condition=Available deployment/kserve-controller-manager --timeout=300s
runtimes="$CACHE/kserve-runtimes-${KSERVE_VERSION}.yaml"
python3 - "$CACHE/kserve-cluster-resources-${KSERVE_VERSION}.yaml" "$runtimes" <<'PY'
import re
import sys

docs = re.split(r"^---\s*$", open(sys.argv[1], encoding="utf-8").read(), flags=re.M)
keep = [d for d in docs if re.search(r"^kind: ClusterServingRuntime\s*$", d, flags=re.M)]
open(sys.argv[2], "w", encoding="utf-8").write("\n---\n".join(keep))
PY
retry k apply --server-side --force-conflicts -f "$runtimes" >/dev/null

log "Argo Workflows ${ARGO_VERSION} (namespace argo) + kho artifact MinIO trong cluster"
fetch "https://github.com/argoproj/argo-workflows/releases/download/${ARGO_VERSION}/install.yaml" \
  "$ARGO_SHA256" "$CACHE/argo-${ARGO_VERSION}.yaml"
k create namespace argo --dry-run=client -o yaml | k apply -f - >/dev/null
k apply --server-side -n argo -f "$CACHE/argo-${ARGO_VERSION}.yaml" >/dev/null
k apply --server-side --field-manager=mlops-kind -f "$HERE/argo-artifacts.yaml" >/dev/null
k -n argo wait --for=condition=Available deployment --all --timeout=300s

log "Xong. Context: $CTX. Kiểm: kubectl --context $CTX get pods -A"
