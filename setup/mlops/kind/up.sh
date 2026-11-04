#!/usr/bin/env bash
# Dựng cluster kind `mlops` (1 node) với cert-manager, KServe (RawDeployment) và Argo Workflows. Chạy lại an toàn.
# `--senior` cài thêm add-on cho module 14–18: metrics-server, KEDA, Kueue.
set -euo pipefail

SENIOR=0
for arg in "$@"; do
  case "$arg" in
    --senior) SENIOR=1 ;;
    -h | --help) printf 'Dùng: bash setup/mlops/kind/up.sh [--senior]\n  --senior  cài thêm metrics-server, KEDA, Kueue (module 14–18)\n'; exit 0 ;;
    *) printf 'LỖI: tham số không hợp lệ %q (chỉ có --senior)\n' "$arg" >&2; exit 1 ;;
  esac
done

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
for port in "$HTTP_PORT" "$HTTPS_PORT"; do
  if [[ ! "$port" =~ ^[0-9]{1,5}$ ]] || (( 10#$port < 1024 || 10#$port > 65535 )); then
    printf 'LỖI: cổng không hợp lệ %q (MLOPS_KIND_HTTP_PORT / MLOPS_KIND_HTTPS_PORT phải là số 1024-65535)\n' "$port" >&2
    exit 1
  fi
done
case "$(uname -m)" in
  x86_64 | amd64) ARCH=amd64 ;;
  aarch64 | arm64) ARCH=arm64 ;;
  *) printf 'LỖI: kiến trúc %s chưa hỗ trợ (chỉ amd64, arm64)\n' "$(uname -m)" >&2; exit 1 ;;
esac
ARCH_UPPER="${ARCH^^}"
KIND_SHA="KIND_SHA256_${ARCH_UPPER}"
KUBECTL_SHA="KUBECTL_SHA256_${ARCH_UPPER}"
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

install_bin kind "$KIND_VERSION-$ARCH" "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-linux-${ARCH}" "${!KIND_SHA}"
install_bin kubectl "$KUBECTL_VERSION-$ARCH" "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl" "${!KUBECTL_SHA}"
KIND="$BIN_DIR/kind"
KUBECTL="$BIN_DIR/kubectl"
k() { "$KUBECTL" --context "$CTX" "$@"; }

PREVIOUS_CONTEXT="$("$KUBECTL" config current-context 2>/dev/null || true)"
restore_context() {
  if [[ -n "$PREVIOUS_CONTEXT" ]]; then
    "$KUBECTL" config use-context "$PREVIOUS_CONTEXT" >/dev/null 2>&1 || true
  else
    "$KUBECTL" config unset current-context >/dev/null 2>&1 || true
  fi
}
trap restore_context EXIT

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
artifacts_sha="$(sha256sum "$HERE/argo-artifacts.yaml" | cut -d' ' -f1)"
sed "s/__CONFIG_SHA256__/${artifacts_sha}/" "$HERE/argo-artifacts.yaml" \
  | k apply --server-side --field-manager=mlops-kind -f - >/dev/null
k -n argo wait --for=condition=Available deployment --all --timeout=300s
k -n argo rollout status deployment/argo-artifacts --timeout=300s >/dev/null

if (( SENIOR )); then
  log "metrics-server ${METRICS_SERVER_VERSION} (thêm --kubelet-insecure-tls: kubelet của kind dùng chứng chỉ tự ký)"
  fetch "https://github.com/kubernetes-sigs/metrics-server/releases/download/${METRICS_SERVER_VERSION}/components.yaml" \
    "$METRICS_SERVER_SHA256" "$CACHE/metrics-server-${METRICS_SERVER_VERSION}.yaml"
  KEDA_FILE="keda-${KEDA_VERSION#v}.yaml"
  fetch "https://github.com/kedacore/keda/releases/download/${KEDA_VERSION}/${KEDA_FILE}" \
    "$KEDA_SHA256" "$CACHE/keda-${KEDA_VERSION}.yaml"
  fetch "https://github.com/kubernetes-sigs/kueue/releases/download/${KUEUE_VERSION}/manifests.yaml" \
    "$KUEUE_SHA256" "$CACHE/kueue-${KUEUE_VERSION}.yaml"
  python3 - "$CACHE" "$METRICS_SERVER_VERSION" "$KUEUE_VERSION" <<'PY'
import re
import sys

cache, ms, kueue = sys.argv[1:4]


def rewrite(src, dst, edit):
    text = open(f"{cache}/{src}", encoding="utf-8").read()
    open(f"{cache}/{dst}", "w", encoding="utf-8").write(edit(text))


def metrics_server(text):
    anchor = "        - --metric-resolution=15s\n"
    if text.count(anchor) != 1:
        sys.exit("metrics-server: không thấy đúng một dòng --metric-resolution để thêm --kubelet-insecure-tls")
    return text.replace(anchor, anchor + "        - --kubelet-insecure-tls\n")


DROP = {f"{p}{r}.kb.io" for p in "mv" for r in ("pod", "deployment", "statefulset", "leaderworkerset")}


def kueue_manifest(text):
    docs = re.split(r"^---\s*$", text, flags=re.M)
    dropped = set()
    for i, doc in enumerate(docs):
        if not re.search(r"^kind: (Mutating|Validating)WebhookConfiguration\s*$", doc, flags=re.M):
            continue
        head, sep, body = doc.partition("\nwebhooks:\n")
        entries = re.split(r"(?m)^(?=- admissionReviewVersions:)", body)
        keep = []
        for entry in entries:
            name = re.search(r"(?m)^  name: (\S+)$", entry)
            if name and name.group(1) in DROP:
                dropped.add(name.group(1))
                continue
            keep.append(entry)
        docs[i] = head + sep + "".join(keep)
    if dropped != DROP:
        sys.exit(f"kueue: thiếu webhook cần bỏ: {sorted(DROP - dropped)}")
    out = "---".join(docs)
    frameworks = re.compile(r"(    integrations:\n      frameworks:\n)(?:      .*\n)+?(?=    #  externalFrameworks:)")
    if len(frameworks.findall(out)) != 1:
        sys.exit("kueue: không thấy đúng một khối integrations.frameworks")
    return frameworks.sub(lambda m: m.group(1) + '      - "batch/job"\n', out)


rewrite(f"metrics-server-{ms}.yaml", f"metrics-server-{ms}-kind.yaml", metrics_server)
rewrite(f"kueue-{kueue}.yaml", f"kueue-{kueue}-batchjob.yaml", kueue_manifest)
PY
  retry k apply --server-side --force-conflicts -f "$CACHE/metrics-server-${METRICS_SERVER_VERSION}-kind.yaml" >/dev/null
  k -n kube-system rollout status deployment/metrics-server --timeout=300s >/dev/null

  log "KEDA ${KEDA_VERSION} (namespace keda)"
  retry k apply --server-side --force-conflicts -f "$CACHE/keda-${KEDA_VERSION}.yaml" >/dev/null
  k -n keda wait --for=condition=Available deployment --all --timeout=300s >/dev/null

  log "Kueue ${KUEUE_VERSION} (namespace kueue-system; chỉ tích hợp batch/job, bỏ webhook pod/deployment/statefulset)"
  retry k apply --server-side --force-conflicts -f "$CACHE/kueue-${KUEUE_VERSION}-batchjob.yaml" >/dev/null
  k -n kueue-system wait --for=condition=Available deployment/kueue-controller-manager --timeout=300s >/dev/null

  log "Chờ APIService metrics, external metrics và webhook Kueue sẵn sàng"
  k wait --for=condition=Available apiservice/v1beta1.metrics.k8s.io apiservice/v1beta1.external.metrics.k8s.io \
    --timeout=300s >/dev/null
  probe='{"apiVersion":"kueue.x-k8s.io/v1beta2","kind":"ResourceFlavor","metadata":{"name":"mlops-up-probe"}}'
  ready=0
  for _ in $(seq 1 90); do
    if echo "$probe" | k create --dry-run=server -f - >/dev/null 2>&1 && k top node >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 2
  done
  (( ready )) || die "webhook Kueue hoặc metrics-server chưa sẵn sàng sau 180 giây (xem: kubectl --context $CTX -n kueue-system logs deploy/kueue-controller-manager)"
  log "Add-on senior sẵn sàng: metrics-server ${METRICS_SERVER_VERSION}, KEDA ${KEDA_VERSION}, Kueue ${KUEUE_VERSION}"
fi

log "PriorityClass mlops-system (1000000) cho controller add-on: pod của bài (serving, training) luôn thấp hơn, không đẩy được controller"
k apply --server-side --field-manager=mlops-kind -f - >/dev/null <<'YAML'
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: mlops-system
value: 1000000
globalDefault: false
preemptionPolicy: PreemptLowerPriority
description: "Controller add-on của cluster mlops (KServe, Argo, cert-manager, KEDA, Kueue): cao hơn mọi PriorityClass của bài"
YAML
addon_namespaces=(cert-manager kserve argo local-path-storage)
(( SENIOR )) && addon_namespaces+=(keda kueue-system)
for ns in "${addon_namespaces[@]}"; do
  k get namespace "$ns" >/dev/null 2>&1 || continue
  while read -r name class; do
    [[ -n "$name" && "$class" == "<none>" ]] || continue
    k -n "$ns" patch deployment "$name" --type merge \
      -p '{"spec":{"template":{"spec":{"priorityClassName":"mlops-system"}}}}' >/dev/null
    k -n "$ns" rollout status "deployment/$name" --timeout=300s >/dev/null
  done < <(k -n "$ns" get deployment -o custom-columns=N:.metadata.name,P:.spec.template.spec.priorityClassName --no-headers)
done

log "Xong. Context: $CTX (current-context của kubectl giữ nguyên: ${PREVIOUS_CONTEXT:-<trống>}). Kiểm: kubectl --context $CTX get pods -A"
