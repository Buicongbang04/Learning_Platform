import k8sprodkit as kit
import mlopskit

from testkit import Exercise

ex = Exercise(__file__)


def manifest(name: str, gpu: str) -> list[dict]:
    return kit.substitute(kit.load_docs(ex.path(name)), **{kit.GPU: gpu})


def pod(name: str, requests: dict | None = None, limits: dict | None = None) -> str:
    resources = {k: v for k, v in (("requests", requests), ("limits", limits)) if v}
    container = {"name": "main", "image": kit.JOB_IMAGE, "imagePullPolicy": "IfNotPresent",
                 "command": ["sh", "-c", "sleep 300"], "securityContext": dict(kit.CONTAINER_SECURITY)}
    if resources:
        container["resources"] = resources
    return kit.dump([{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": name},
                      "spec": {"terminationGracePeriodSeconds": 1, "automountServiceAccountToken": False,
                               "securityContext": dict(kit.POD_SECURITY),
                               "containers": [container]}}])


def accepted(ns: str, name: str, **resources) -> bool:
    return mlopskit.apply_manifest(pod(name, **resources), ns, check=False).returncode == 0


def rejected(ns: str, name: str, **resources) -> bool:
    result = mlopskit.apply_manifest(pod(name, **resources), ns, check=False)
    return result.returncode != 0 and "forbidden" in result.stderr.lower()


def container_resources(ns: str, name: str) -> dict:
    return kit.get_json("pod", name, namespace=ns)["spec"]["containers"][0].get("resources") or {}


def test_manifest_shape():
    for name, quota, limits in (("serving.yaml", "serving-quota", "serving-defaults"),
                                ("training.yaml", "training-quota", "training-defaults")):
        docs = kit.load_docs(ex.path(name))
        kit.find(docs, "ResourceQuota", quota)
        kit.find(docs, "LimitRange", limits)
        assert all("namespace" not in (d.get("metadata") or {}) for d in docs), f"{name}: không ghi namespace"


def test_serving_namespace_rules():
    mlopskit.require_kind()
    with mlopskit.fake_extended_resource("gpu", 2) as gpu, mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(kit.dump(manifest("serving.yaml", gpu)), ns)
        assert accepted(ns, "plain"), "Pod không khai resources bị từ chối trong namespace serving"
        resources = container_resources(ns, "plain")
        expected = {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "500m", "memory": "256Mi"}}
        for part, values in expected.items():
            for key, value in values.items():
                got = (resources.get(part) or {}).get(key)
                assert got is not None and kit.quantity(got) == kit.quantity(value), \
                    f"Pod không khai resources nhận {part}.{key}={got}, cần {value}"
        assert rejected(ns, "wants-gpu", requests={gpu: "1"}, limits={gpu: "1"}), "Namespace serving vẫn cho xin GPU"
        assert rejected(ns, "too-big", limits={"memory": "2Gi"}), "Container 2Gi bộ nhớ vẫn được nhận"
        assert rejected(ns, "too-much-cpu", requests={"cpu": "3"}, limits={"cpu": "3"}), \
            "Pod xin 3 CPU vẫn được nhận trong namespace serving"


def test_training_namespace_rules():
    mlopskit.require_kind()
    with mlopskit.fake_extended_resource("gpu", 4) as gpu, mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(kit.dump(manifest("training.yaml", gpu)), ns)
        one = {"requests": {gpu: "1"}, "limits": {gpu: "1"}}
        assert accepted(ns, "gpu-1", **one) and accepted(ns, "gpu-2", **one), "Hai pod 1 GPU bị từ chối"
        assert rejected(ns, "gpu-3", **one), "Pod GPU thứ ba vẫn được nhận"
        assert accepted(ns, "plain"), "Pod không khai resources bị từ chối trong namespace training"
        resources = container_resources(ns, "plain")
        assert kit.quantity((resources.get("requests") or {}).get("memory", 0)) == kit.quantity("512Mi"), \
            "Pod không khai resources chưa nhận request bộ nhớ mặc định 512Mi"
        assert rejected(ns, "too-big", limits={"memory": "6Gi"}), "Container 6Gi bộ nhớ vẫn được nhận"
        assert accepted(ns, "big-ok", requests={"memory": "3Gi"}, limits={"memory": "4Gi"}), \
            "Container 4Gi bộ nhớ bị từ chối trong namespace training"
