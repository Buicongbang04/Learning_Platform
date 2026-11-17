import json
import os
import ssl
import time
import urllib.error
import urllib.request

ROOT = "/var/run/secrets/kubernetes.io/serviceaccount"
GROUP = os.environ["STOREFRONT_GROUP"]
NAMESPACE = open(f"{ROOT}/namespace").read().strip()
SERVER = f"https://{os.environ['KUBERNETES_SERVICE_HOST']}:{os.environ['KUBERNETES_SERVICE_PORT']}"
CONTEXT = ssl.create_default_context(cafile=f"{ROOT}/ca.crt")
MANAGER = "storefront-operator"


def call(method, path, body=None, content_type="application/json"):
    token = open(f"{ROOT}/token").read().strip()
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{SERVER}{path}", data=data, method=method,
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": content_type})
    with urllib.request.urlopen(request, context=CONTEXT, timeout=10) as answer:
        return json.load(answer)


def apply(path, body):
    return call("PATCH", f"{path}?fieldManager={MANAGER}&force=true", body, "application/apply-patch+yaml")


def owned(storefront, kind, api_version, name, extra):
    owner = {"apiVersion": storefront["apiVersion"], "kind": "Storefront", "name": storefront["metadata"]["name"],
             "uid": storefront["metadata"]["uid"], "controller": True}
    labels = {"app.kubernetes.io/name": "storefront", "app.kubernetes.io/instance": storefront["metadata"]["name"],
              "app.kubernetes.io/managed-by": MANAGER}
    return {"apiVersion": api_version, "kind": kind,
            "metadata": {"name": name, "namespace": NAMESPACE, "labels": labels, "ownerReferences": [owner]}, **extra}


def reconcile(storefront):
    name = storefront["metadata"]["name"]
    spec = storefront["spec"]
    web = f"{name}-web"
    page = f"<h1>{spec['message']}</h1>\n"
    apply(f"/api/v1/namespaces/{NAMESPACE}/configmaps/{web}",
          owned(storefront, "ConfigMap", "v1", web, {"data": {"index.html": page}}))
    selector = {"app.kubernetes.io/name": "storefront", "app.kubernetes.io/instance": name}
    pod = {"metadata": {"labels": selector},
           "spec": {"automountServiceAccountToken": False,
                    "containers": [{"name": "web", "image": "nginx:1.30.6-alpine", "ports": [{"containerPort": 80}],
                                    "readinessProbe": {"httpGet": {"path": "/", "port": 80}, "periodSeconds": 3},
                                    "resources": {"requests": {"cpu": "10m", "memory": "16Mi"}, "limits": {"memory": "64Mi"}},
                                    "volumeMounts": [{"name": "content", "mountPath": "/usr/share/nginx/html"}]}],
                    "volumes": [{"name": "content", "configMap": {"name": web}}]}}
    deployment = apply(f"/apis/apps/v1/namespaces/{NAMESPACE}/deployments/{web}",
                       owned(storefront, "Deployment", "apps/v1", web,
                             {"spec": {"replicas": spec["replicas"], "selector": {"matchLabels": selector}, "template": pod}}))
    ready = (deployment.get("status") or {}).get("readyReplicas") or 0
    status = {"readyReplicas": ready, "phase": "Ready" if ready == spec["replicas"] else "Progressing",
              "observedGeneration": storefront["metadata"]["generation"]}
    if storefront.get("status") != status:
        call("PATCH", f"/apis/{GROUP}/v1/namespaces/{NAMESPACE}/storefronts/{name}/status", {"status": status},
             "application/merge-patch+json")


def main():
    while True:
        try:
            for storefront in call("GET", f"/apis/{GROUP}/v1/namespaces/{NAMESPACE}/storefronts")["items"]:
                if storefront["metadata"].get("deletionTimestamp"):
                    continue
                try:
                    reconcile(storefront)
                except urllib.error.HTTPError as error:
                    print(json.dumps({"storefront": storefront["metadata"]["name"], "error": error.code,
                                      "detail": error.read().decode()[:300]}), flush=True)
        except Exception as error:
            print(json.dumps({"error": type(error).__name__, "detail": str(error)[:300]}), flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
