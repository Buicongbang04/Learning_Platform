#!/usr/bin/env bash
set -euo pipefail
kubeconfig="${DEVOPS_LAB_KUBECONFIG:-$HOME/.kube/devops-lab.yaml}"
k() { kubectl --kubeconfig "$kubeconfig" -n linkerd "$@"; }
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
cd "$workdir"
umask 077
key() { openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve -out "$1"; }
ca() {
  key "$1.key"
  openssl req -x509 -new -sha256 -key "$1.key" -out "$1.crt" -days "$2" -subj "/CN=$3" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:$4" -addext "keyUsage=critical,keyCertSign,cRLSign"
}
sign() {
  key "$1.key"
  openssl req -new -sha256 -key "$1.key" -out "$1.csr" -subj "/CN=$2"
  printf '%s\n' "$4" > "$1.ext"
  openssl x509 -req -sha256 -in "$1.csr" -CA "$3.crt" -CAkey "$3.key" -set_serial "0x$(openssl rand -hex 16)" \
    -days "$5" -out "$1.crt" -extfile "$1.ext"
}
apply() { "$@" --dry-run=client -o yaml | kubectl --kubeconfig "$kubeconfig" apply --server-side --force-conflicts --field-manager=devops-linkerd-certs -f -; }

ca root 3650 root.linkerd.cluster.local 1
sign issuer identity.linkerd.cluster.local root \
  "basicConstraints=critical,CA:TRUE,pathlen:0
keyUsage=critical,keyCertSign,cRLSign" 365
rm -f root.key
apply k create configmap linkerd-identity-trust-roots --from-file=ca-bundle.crt=root.crt
apply k create secret generic linkerd-identity-issuer --type=kubernetes.io/tls \
  --from-file=tls.crt=issuer.crt --from-file=tls.key=issuer.key --from-file=ca.crt=root.crt
rm -f issuer.key

ca webhook 3650 webhook.linkerd.cluster.local 0
for service in linkerd-proxy-injector linkerd-sp-validator linkerd-policy-validator; do
  sign "$service" "$service.linkerd.svc" webhook \
    "basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=serverAuth
subjectAltName=DNS:$service.linkerd.svc" 3650
  apply k create secret tls "$service-k8s-tls" --cert="$service.crt" --key="$service.key"
  rm -f "$service.key"
done
rm -f webhook.key
bundle="$(base64 -w0 webhook.crt)"
patch() {
  kubectl --kubeconfig "$kubeconfig" patch "$1" "$2" --type=json \
    -p "[{\"op\":\"replace\",\"path\":\"/webhooks/0/clientConfig/caBundle\",\"value\":\"$bundle\"}]"
}
patch mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config
patch validatingwebhookconfiguration linkerd-sp-validator-webhook-config
patch validatingwebhookconfiguration linkerd-policy-validator-webhook-config
k rollout restart deployment/linkerd-identity deployment/linkerd-destination deployment/linkerd-proxy-injector
