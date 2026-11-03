import json

import k8skit
import mlopskit
import pytest

from testkit import Exercise

ex = Exercise(__file__)
SEED, ROWS = 7, 4000


def workflow() -> dict:
    return k8skit.find(k8skit.load_docs(ex.path("workflow.yaml")), "Workflow", "eta-train")


def templates(spec: dict) -> dict[str, dict]:
    return {t["name"]: t for t in spec["spec"].get("templates") or []}


def test_dag_shape():
    spec = workflow()
    params = {p["name"] for p in spec["spec"].get("arguments", {}).get("parameters") or []}
    assert {"seed", "rows"} <= params, "Workflow cần parameter seed và rows"
    entry = templates(spec)[spec["spec"]["entrypoint"]]
    tasks = {t["name"]: set(t.get("dependencies") or []) for t in entry.get("dag", {}).get("tasks") or []}
    assert set(tasks) == {"prepare", "train", "evaluate"}, f"DAG cần đúng 3 task prepare, train, evaluate: {set(tasks)}"
    assert "prepare" in tasks["train"] and {"prepare", "train"} <= tasks["evaluate"], (
        "train phụ thuộc prepare; evaluate phụ thuộc prepare và train"
    )
    retry = templates(spec).get("train", {}).get("retryStrategy") or {}
    assert int(retry.get("limit", 0)) >= 1, "Template train cần retryStrategy.limit >= 1"


def node_by_task(status: dict, task: str) -> dict:
    for node in status.get("nodes", {}).values():
        if node.get("displayName") == task and node.get("type") in ("Pod", "Retry"):
            return node
    pytest.fail(f"Không thấy bước {task} trong status Workflow", pytrace=False)


def test_workflow_succeeds_and_evaluate_reads_the_trained_model():
    spec = workflow()
    spec["spec"]["arguments"]["parameters"] = [{"name": "seed", "value": str(SEED)}, {"name": "rows", "value": str(ROWS)}]
    docs = k8skit.with_image([spec], k8skit.eta_image())
    with mlopskit.k8s_namespace() as ns:
        mlopskit.apply_manifest(k8skit.dump(docs), ns)
        mlopskit.wait_for("workflow", "eta-train", "jsonpath={.status.phase}=Succeeded", ns, 300,
                          fail_on=("Failed", "Error"))
        status = k8skit.get_json("workflow", "eta-train", ns)["status"]
    prepare = node_by_task(status, "prepare")
    produced = {a["name"] for a in prepare.get("outputs", {}).get("artifacts") or []}
    assert {"train", "test"} <= produced, f"prepare phải xuất artifact train và test, đang có {produced}"
    evaluate = node_by_task(status, "evaluate")
    consumed = {a["name"] for a in evaluate.get("inputs", {}).get("artifacts") or []}
    assert {"model", "test"} <= consumed, f"evaluate phải nhận artifact model và test, đang nhận {consumed}"
    outputs = {p["name"]: p.get("value") for p in evaluate.get("outputs", {}).get("parameters") or []}
    assert "metrics" in outputs, "evaluate phải xuất output parameter metrics"
    metrics = json.loads(outputs["metrics"])
    lab = k8skit.etaml()
    x, y = lab.make_trips(SEED, ROWS)
    cut = int(ROWS * 0.8)
    expected = lab.mae(lab.train(x[:cut], y[:cut]), x[cut:], y[cut:])
    assert metrics["n_test"] == ROWS - cut
    assert metrics["mae"] == pytest.approx(expected, abs=1e-6), "MAE không khớp model train trên đúng seed/rows của Workflow"
