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


def reconcile(storefront):
    # TODO: ConfigMap <tên>-web (index.html chứa spec.message) và Deployment <tên>-web (nginx:1.30.6-alpine, spec.replicas,
    # mount ConfigMap vào /usr/share/nginx/html), cả hai có ownerReference controller trỏ về Storefront; rồi cập nhật status
    # qua subresource status (readyReplicas, phase Ready/Progressing, observedGeneration). Gợi ý: server-side apply.
    print(json.dumps({"storefront": storefront["metadata"]["name"], "todo": "reconcile"}), flush=True)


def main():
    while True:
        try:
            for storefront in call("GET", f"/apis/{GROUP}/v1/namespaces/{NAMESPACE}/storefronts")["items"]:
                reconcile(storefront)
        except Exception as error:
            print(json.dumps({"error": type(error).__name__, "detail": str(error)[:300]}), flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
